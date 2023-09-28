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
    LLMWebLoader,
    LLMArxivLoader
)
import utils
from ops_base import OperatorBase
from db_cli import DBClient
from ops_notion import OperatorNotion


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
        # 1. prepare notion agent and db connection
        notion_api_key = os.getenv("NOTION_TOKEN")
        notion_agent = NotionAgent(notion_api_key)

        client = DBClient()
        last_created_time = client.get_notion_inbox_created_time(
            "article", "default")

        last_created_time = utils.bytes2str(last_created_time)
        print(f"Get last_created_time from redis: {last_created_time}")

        if not last_created_time:
            last_created_time = (datetime.now() - timedelta(days=1)).isoformat()

        # 2. get inbox database indexes
        op_notion = OperatorNotion()

        # db_index_id = os.getenv("NOTION_DATABASE_ID_INDEX_INBOX")
        db_index_id = op_notion.get_index_inbox_dbid()

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

        client = DBClient()
        deduped_pages = []

        for page_id, page in extractedPages.items():
            title = page["title"]
            print(f"Dedupping page, title: {title}")

            if client.get_notion_toread_item_id(
                    "article", "default", page_id):
                print(f"Duplicated article found, skip. page_id: {page_id}")
            else:
                deduped_pages.append(page)

        return deduped_pages

    def summarize(self, pages):
        print("#####################################################")
        print("# Summarize Articles")
        print("#####################################################")
        SUMMARY_MAX_LENGTH = int(os.getenv("SUMMARY_MAX_LENGTH", 20000))
        print(f"Number of pages: {len(pages)}")
        print(f"Summary max length: {SUMMARY_MAX_LENGTH}")

        llm_agent = LLMAgentSummary()
        llm_agent.init_prompt()
        llm_agent.init_llm()

        client = DBClient()
        redis_key_expire_time = os.getenv(
            "BOT_REDIS_KEY_EXPIRE_TIME", 604800)

        summarized_pages = []

        for page in pages:
            title = page["title"]
            page_id = page["id"]
            content = page["content"]
            source_url = page["source_url"]
            print(f"====== Summarying page, title: {title} ======")
            print(f"source url: {source_url}")
            print(f"Page content ({len(content)} chars): {content[:200]}...")

            st = time.time()

            llm_summary_resp = client.get_notion_summary_item_id(
                "article", "default", page_id)

            if not llm_summary_resp:
                # Double check the content, if empty, load it from
                # the source url
                if not content:
                    print("page content is empty, fallback to load web page via WebBaseLoader")

                    try:
                        content = utils.load_web(source_url)
                        print(f"Page content ({len(content)} chars): {content}")

                    except Exception as e:
                        print(f"[ERROR] Exception occurred during utils.load_web(), source_url: {source_url}, {e}")

                    if not content:
                        print("[ERROR] Empty Web page loaded via WebBaseLoader, skip it")
                        continue

                content = content[:SUMMARY_MAX_LENGTH]
                summary = llm_agent.run(content)

                print(f"Cache llm response for {redis_key_expire_time}s, page_id: {page_id}, summary: {summary}")

                client.set_notion_summary_item_id(
                    "article", "default", page_id, summary,
                    expired_time=int(redis_key_expire_time))

            else:
                print("Found llm summary from cache, decoding (utf-8) ...")
                summary = utils.bytes2str(llm_summary_resp)

            # assemble summary into page
            summarized_page = copy.deepcopy(page)
            summarized_page["__summary"] = summary

            # Try to load Arxiv metadata if the page is from it
            arxiv_loader = LLMArxivLoader()
            loaded, arxiv_res = arxiv_loader.load_from_url(source_url)

            if loaded:
                summarized_page["__arxiv_result"] = arxiv_res
                print(f"Arxiv result: {arxiv_res}")

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

        client = DBClient()
        redis_key_expire_time = os.getenv(
            "BOT_REDIS_KEY_EXPIRE_TIME", 604800)

        # array of ranged pages
        ranked = []

        for page in pages:
            title = page["title"]
            page_id = page["id"]
            text = page["__summary"]
            print(f"Ranking page, title: {title}")

            # Let LLM to category and rank
            st = time.time()

            llm_ranking_resp = client.get_notion_ranking_item_id(
                "article", "default", page_id)

            category_and_rank_str = None

            if not llm_ranking_resp:
                print("Not found category_and_rank_str in cache, fallback to llm_agent to rank")
                category_and_rank_str = llm_agent.run(text)

                print(f"Cache llm response for {redis_key_expire_time}s, page_id: {page_id}")
                client.set_notion_ranking_item_id(
                    "article", "default", page_id,
                    category_and_rank_str,
                    expired_time=int(redis_key_expire_time))

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

        stat = {
            "total": 0,
            "error": 0,
        }

        for target in targets:
            print(f"Pushing data to target: {target} ...")

            if target == "notion":
                notion_api_key = os.getenv("NOTION_TOKEN")
                notion_agent = NotionAgent(notion_api_key)
                op_notion = OperatorNotion()

                # Get the latest toread database id from index db
                # db_index_id = os.getenv("NOTION_DATABASE_ID_INDEX_TOREAD")
                db_index_id = op_notion.get_index_toread_dbid()
                database_id = utils.get_notion_database_id_toread(
                    notion_agent, db_index_id)
                print(f"Latest ToRead database id: {database_id}")

                if not database_id:
                    print("[ERROR] no index db pages found... skip")
                    break

                for ranked_page in ranked_data:
                    stat["total"] += 1

                    try:
                        page_id = ranked_page["id"]
                        title = ranked_page["title"]
                        print(f"Pushing page, title: {title}")

                        topics = ranked_page["__topics"]
                        topics_topk = self._get_top_items(topics, topk)
                        topics_topk = [x[0].replace(",", " ")[:20] for x in topics_topk]

                        categories = ranked_page["__categories"]
                        categories_topk = self._get_top_items(categories, topk)
                        categories_topk = [x[0].replace(",", " ")[:20] for x in categories_topk]

                        rating = ranked_page["__rate"]

                        new_page = notion_agent.createDatabaseItem_ToRead_Article(
                            database_id,
                            ranked_page,
                            topics_topk,
                            categories_topk,
                            rating)

                        # Add Arxiv metadata as a comment
                        if ranked_page.get("__arxiv_result"):
                            try:
                                new_page_id = new_page["id"]
                                metadata_text = ranked_page["__arxiv_result"]["metadata_text"]

                                notion_agent.createPageComment(
                                    new_page_id, metadata_text)

                            except Exception as e:
                                print(f"[WARN] Failed to add Arxiv metadata, skip: {e}")

                        self.markVisited(page_id, source="article", list_name="default")

                        created_time = ranked_page["created_time"]
                        self.updateCreatedTime(
                            created_time,
                            source="article",
                            list_name="default")

                    except Exception as e:
                        print(f"[ERROR]: Push to notion failed, skip: {e}")
                        traceback.print_exc()
                        stat["error"] += 1

            else:
                print(f"[ERROR]: Unknown target {target}, skip")

        return stat
