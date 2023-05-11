import os
import time
import copy
import traceback
from operator import itemgetter
from datetime import timedelta, datetime

from notion import NotionAgent
from llm_agent import (
    LLMAgentCategoryAndRanking,
    LLMAgentSummary,
    LLMWebLoader
)
import utils
import data_model
from ops_base import OperatorBase


class OperatorArticle(OperatorBase):
    """
    An Operator to handle:
    - pulling data from source
    - save to local json
    - restore from local json
    - dedup
    - summarization
    - ranking
    - publish
    """

    def pull(self):
        print("#####################################################")
        print("# Pulling Articles")
        print("#####################################################")
        # 1. prepare notion agent and redis connection
        notion_api_key = os.getenv("NOTION_TOKEN")
        notion_agent = NotionAgent(notion_api_key)

        redis_url = os.getenv("BOT_REDIS_URL")
        redis_conn = utils.redis_conn(redis_url)

        created_time_tpl = data_model.NOTION_INBOX_CREATED_TIME_KEY
        redis_key = created_time_tpl.format("article", "default")

        last_created_time = utils.redis_get(redis_conn, redis_key)
        last_created_time = utils.bytes2str(last_created_time)
        print(f"Get last_created_time from redis: {last_created_time}")

        if not last_created_time:
            last_created_time = (datetime.now() - timedelta(days=1)).isoformat()

        # 2. get inbox database indexes
        db_index_id = os.getenv("NOTION_DATABASE_ID_INDEX_INBOX")
        db_pages = utils.get_notion_database_pages_inbox(
            notion_agent, db_index_id, "Article")
        print(f"The database pages founded: {db_pages}")

        # 2. get latest two databases and collect items by created_time
        db_pages = db_pages[:2]
        print(f"The latest 2 databases: {db_pages}")

        pages = {}

        for db_page in db_pages:
            database_id = db_page["database_id"]
            print(f"Pulling from database_id: {database_id}...")

            # The api will return the pages and sort by "created time" asc
            # format dict(<page_id, page>)
            extracted_pages = notion_agent.queryDatabaseInbox_Article(
                database_id,
                filter_created_time=last_created_time)

            pages.update(extracted_pages)

        return pages

    def dedup(self, extractedPages, target="inbox"):
        print("#####################################################")
        print("# Dedup Articles")
        print("#####################################################")
        print(f"Number of pages: {len(extractedPages)}")

        redis_url = os.getenv("BOT_REDIS_URL")
        redis_conn = utils.redis_conn(redis_url)

        redis_page_tpl = data_model.NOTION_INBOX_ITEM_ID
        if target == "toread":
            redis_page_tpl = data_model.NOTION_TOREAD_ITEM_ID

        deduped_pages = []

        for page_id, page in extractedPages.items():
            title = page["title"]
            print(f"Dedupping page, title: {title}")

            redis_page_key = redis_page_tpl.format("article", "default", page_id)

            if utils.redis_get(redis_conn, redis_page_key):
                print(f"Duplicated article found, skip. key: {redis_page_key}")
            else:
                deduped_pages.append(page)

        return deduped_pages

    def _load_web(self, url):
        loader = LLMWebLoader()
        docs = loader.load(url)

        content = ""
        for doc in docs:
            content += doc.page_content
            content += "\n"

        return content

    def summarize(self, pages):
        print("#####################################################")
        print("# Summarize Articles")
        print("#####################################################")
        print(f"Number of pages: {len(pages)}")
        llm_agent = LLMAgentSummary()
        llm_agent.init_prompt()
        llm_agent.init_llm()

        redis_url = os.getenv("BOT_REDIS_URL")
        redis_conn = utils.redis_conn(redis_url)
        redis_key_expire_time = os.getenv("BOT_REDIS_KEY_EXPIRE_TIME", 604800)

        summarized_pages = []

        for page in pages:
            title = page["title"]
            page_id = page["id"]
            content = page["content"]
            source_url = page["source_url"]
            print(f"Summarying page, title: {title}")
            print(f"Page content ({len(content)} chars): {content}")

            st = time.time()

            summary_key = data_model.NOTION_SUMMARY_ITEM_ID.format(
                "article", "default", page_id)

            llm_summary_resp = utils.redis_get(redis_conn, summary_key)

            if not llm_summary_resp:
                # Double check the content, if empty, load it from
                # the source url
                if not content:
                    print("page content is empty, fallback to load web page via WebBaseLoader")
                    content = self._load_web(source_url)
                    print(f"Page content ({len(content)} chars): {content}")

                    if not content:
                        print("[ERROR] Empty Web page loaded via WebBaseLoader, skip it")
                        continue

                summary = llm_agent.run(content)

                print(f"Cache llm response for {redis_key_expire_time}s, key: {summary_key}, summary: {summary}")
                utils.redis_set(
                    redis_conn,
                    summary_key,
                    summary,
                    expire_time=int(redis_key_expire_time))

            else:
                print("Found llm summary from cache, decoding (utf-8) ...")
                summary = utils.bytes2str(llm_summary_resp)

            # assemble summary into page
            summarized_page = copy.deepcopy(page)
            summarized_page["__summary"] = summary

            print(f"Used {time.time() - st:.3f}s, Summarized page_id: {page_id}, summary: {summary}")
            summarized_pages.append(summarized_page)

        return summarized_pages

    def rank(self, pages):
        """
        Rank page summary (not the entire content)
        """
        print("#####################################################")
        print("# Rank Articles")
        print("#####################################################")
        print(f"Number of pages: {len(pages)}")

        llm_agent = LLMAgentCategoryAndRanking()
        llm_agent.init_prompt()
        llm_agent.init_llm()

        redis_url = os.getenv("BOT_REDIS_URL")
        redis_conn = utils.redis_conn(redis_url)
        redis_key_expire_time = os.getenv("BOT_REDIS_KEY_EXPIRE_TIME", 604800)

        # array of ranged pages
        ranked = []

        for page in pages:
            title = page["title"]
            page_id = page["id"]
            text = page["__summary"]
            print(f"Ranking page, title: {title}")

            # Let LLM to category and rank
            st = time.time()

            ranking_key = data_model.NOTION_RANKING_ITEM_ID.format(
                "article", "default", page_id)

            llm_ranking_resp = utils.redis_get(redis_conn, ranking_key)

            category_and_rank_str = None

            if not llm_ranking_resp:
                print("Not found category_and_rank_str in cache, fallback to llm_agent to rank")
                category_and_rank_str = llm_agent.run(text)

                print(f"Cache llm response for {redis_key_expire_time}s, key: {ranking_key}")
                utils.redis_set(
                    redis_conn,
                    ranking_key,
                    category_and_rank_str,
                    expire_time=int(redis_key_expire_time))

            else:
                print("Found category_and_rank_str from cache")
                category_and_rank_str = utils.bytes2str(llm_ranking_resp)

            print(f"Used {time.time() - st:.3f}s, Category and Rank: text: {text}, rank_resp: {category_and_rank_str}")

            category_and_rank = utils.fix_and_parse_json(category_and_rank_str)
            print(f"LLM ranked result (json parsed): {category_and_rank}")

            # Parse LLM response and assemble category and rank
            ranked_page = copy.deepcopy(page)

            if not category_and_rank:
                print("[ERROR] Cannot parse json string, assign default rating -0.01")
                ranked_page["__topics"] = []
                ranked_page["__categories"] = []
                ranked_page["__rate"] = -0.01
            else:
                ranked_page["__topics"] = [(x["topic"], x.get("score") or 1) for x in category_and_rank["topics"]]
                ranked_page["__categories"] = [(x["category"], x.get("score") or 1) for x in category_and_rank["topics"]]
                ranked_page["__rate"] = category_and_rank["overall_score"]
                ranked_page["__feedback"] = category_and_rank.get("feedback") or ""

            ranked.append(ranked_page)

        print(f"Ranked pages: {ranked}")
        return ranked

    def _get_top_items(self, items: list, k):
        """
        items: [(name, score), ...]
        """
        tops = sorted(items, key=itemgetter(1), reverse=True)
        return tops[:k]

    def push(self, ranked_data, targets, topk=3):
        print("#####################################################")
        print("# Push Articles")
        print("#####################################################")
        print(f"Number of pages: {len(ranked_data)}")
        print(f"Targets: {targets}")
        print(f"Top-K: {topk}")
        print(f"input data: {ranked_data}")

        for target in targets:
            print(f"Pushing data to target: {target} ...")

            if target == "notion":
                notion_api_key = os.getenv("NOTION_TOKEN")
                notion_agent = NotionAgent(notion_api_key)

                # Get the latest toread database id from index db
                db_index_id = os.getenv("NOTION_DATABASE_ID_INDEX_TOREAD")
                database_id = utils.get_notion_database_id_toread(
                    notion_agent, db_index_id)
                print(f"Latest ToRead database id: {database_id}")

                if not database_id:
                    print("[ERROR] no index db pages found... skip")
                    break

                for ranked_page in ranked_data:
                    try:
                        page_id = ranked_page["id"]
                        title = ranked_page["title"]
                        print(f"Pushing page, title: {title}")

                        topics = ranked_page["__topics"]
                        topics_topk = self._get_top_items(topics, topk)
                        topics_topk = [x[0].replace(",", " ") for x in topics_topk]

                        categories = ranked_page["__categories"]
                        categories_topk = self._get_top_items(categories, topk)
                        categories_topk = [x[0].replace(",", " ") for x in categories_topk]

                        rating = ranked_page["__rate"]

                        notion_agent.createDatabaseItem_ToRead_Article(
                            database_id,
                            ranked_page,
                            topics_topk,
                            categories_topk,
                            rating)

                        self.markVisited(page_id)

                        created_time = ranked_page["created_time"]
                        self.updateCreatedTime(created_time)

                    except Exception as e:
                        print(f"[ERROR]: Push to notion failed, skip: {e}")
                        traceback.print_exc()

            else:
                print(f"[ERROR]: Unknown target {target}, skip")

    def markVisited(self, page_id: str):
        redis_url = os.getenv("BOT_REDIS_URL")
        redis_conn = utils.redis_conn(redis_url)

        # Mark toread item as visited
        toread_key_tpl = data_model.NOTION_TOREAD_ITEM_ID
        toread_key = toread_key_tpl.format("article", "default", page_id)
        utils.redis_set(redis_conn, toread_key, "true")

    def updateCreatedTime(self, last_created_time: str):
        print(f"[updateCreatedTime] last_created_time: {last_created_time}")
        redis_url = os.getenv("BOT_REDIS_URL")
        redis_conn = utils.redis_conn(redis_url)

        # Update the latest created time
        created_time_tpl = data_model.NOTION_INBOX_CREATED_TIME_KEY
        redis_key = created_time_tpl.format("article", "default")

        curr_created_time = utils.redis_get(redis_conn, redis_key)
        curr_created_time = utils.bytes2str(curr_created_time)
        print("Updating created time: curr_created_time: {curr_created_time}")

        if not curr_created_time:
            utils.redis_set(
                redis_conn,
                redis_key,
                last_created_time,
                overwrite=True)

            print(f"Last created time has not been set yet, set to {last_created_time}")
        else:
            curr = utils.parseDataFromIsoFormat(curr_created_time)
            last = utils.parseDataFromIsoFormat(last_created_time)

            if last > curr:
                utils.redis_set(
                    redis_conn,
                    redis_key,
                    last_created_time,
                    overwrite=True)

            print(f"Update Last created time curr: {curr_created_time}, set to {last_created_time}")
