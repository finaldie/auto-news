import os
import time
import copy
from datetime import timedelta, datetime

from notion import NotionAgent
from llm_agent import LLMAgentCategoryAndRanking, LLMAgentSummary
import utils
import data_model


class OperatorArticle:
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

    def pull(self, database_id):
        notion_api_key = os.getenv("NOTION_TOKEN")
        notion_agent = NotionAgent(notion_api_key)

        redis_url = os.getenv("BOT_REDIS_URL")
        redis_conn = utils.redis_conn(redis_url)

        created_time_tpl = data_model.NOTION_INBOX_CREATED_TIME_KEY
        redis_key = created_time_tpl.format("article", "default")

        last_created_time = utils.redis_get(redis_conn, redis_key)
        if not last_created_time:
            last_created_time = (datetime.now() - timedelta(days=1)).isoformat()

        # The api will return the pages and sort by "created time" asc
        extracted_pages = notion_agent.queryDatabaseInbox_Article(
            database_id,
            filter_created_time=last_created_time)

        return extracted_pages

    def save2json(self, data_folder, run_id, data):
        workdir = os.getenv("WORKDIR")

        filename = "article.json"
        data_path = f"{workdir}/{data_folder}/{run_id}"
        full_path = utils.gen_filename(data_path, filename)

        print(f"Save data to {full_path}, data: {data}")
        utils.save_data_json(full_path, data)

    def readFromJson(self, data_folder, run_id):
        workdir = os.getenv("WORKDIR")

        filename = "article.json"
        data_path = f"{workdir}/{data_folder}/{run_id}"
        full_path = utils.gen_filename(data_path, filename)

        data = utils.read_data_json(full_path)

        print(f"Retrieve article data from {full_path}, data: {data}")
        return data

    def dedup(self, extractedPages, target="inbox"):
        redis_url = os.getenv("BOT_REDIS_URL")
        redis_conn = utils.redis_conn(redis_url)

        redis_page_tpl = data_model.NOTION_INBOX_ITEM_ID
        if target == "toread":
            redis_page_tpl = data_model.NOTION_TOREAD_ITEM_ID

        deduped_pages = []

        for page_id, page in extractedPages.items():
            redis_page_key = redis_page_tpl.format("article", "default", page_id)

            if utils.redis_get(redis_conn, redis_page_key):
                print(f"Duplicated article found, skip. key: {redis_page_key}")
            else:
                deduped_pages.append(page)

        return deduped_pages

    def summarize(self, pages):
        llm_agent = LLMAgentSummary()
        llm_agent.init_prompt()
        llm_agent.init_llm()

        redis_url = os.getenv("BOT_REDIS_URL")
        redis_conn = utils.redis_conn(redis_url)
        redis_key_expire_time = os.getenv("BOT_REDIS_KEY_EXPIRE_TIME", 604800)

        summarized_pages = []

        for page in pages:
            page_id = page["id"]
            content = page["content"]

            st = time.time()

            summary_key = data_model.NOTION_SUMMARY_ITEM_ID.format(
                "article", "default", page_id)

            llm_summary_resp = utils.redis_get(redis_conn, summary_key)

            if not llm_summary_resp:
                summary = llm_agent.run(content)

                print(f"Cache llm response for {redis_key_expire_time}s, key: {summary_key}")
                utils.redis_set(
                    redis_conn,
                    summary_key,
                    llm_summary_resp,
                    expire_time=int(redis_key_expire_time))

            else:
                print("Found llm summary from cache")
                summary = llm_summary_resp

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
        llm_agent = LLMAgentCategoryAndRanking()
        llm_agent.init_prompt()
        llm_agent.init_llm()

        redis_url = os.getenv("BOT_REDIS_URL")
        redis_conn = utils.redis_conn(redis_url)
        redis_key_expire_time = os.getenv("BOT_REDIS_KEY_EXPIRE_TIME", 604800)

        # page_id -> ranked_page
        ranked = {}

        for page in pages:
            page_id = page["id"]
            text = page["__summary"]

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
                category_and_rank_str = llm_ranking_resp

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

    def push(self, ranked_data, targets):
        print(f"input data: {ranked_data}")

        for target in targets:
            print(f"Pushing data to target: {target} ...")

            if target == "notion":
                notion_api_key = os.getenv("NOTION_TOKEN")
                notion_agent = NotionAgent(notion_api_key)

                database_id = os.getenv("NOTION_DATABASE_ID_TOREAD")

                for ranked_page in ranked_data:
                    try:
                        topics = ranked_page["__topics"]
                        categories = ranked_page["__categories"]
                        rating = ranked_page["__rate"]

                        notion_agent.createDatabaseItem_ToRead_Article(
                            database_id,
                            ranked_page,
                            topics,
                            categories,
                            rating)

                        created_time = ranked_page["created_time"]
                        self.markVisited(created_time)

                    except Exception as e:
                        print(f"[ERROR]: Push to notion failed, skip: {e}")
            else:
                print(f"[ERROR]: Unknown target {target}, skip")

    def markVisited(self, last_created_time):
        redis_url = os.getenv("BOT_REDIS_URL")
        redis_conn = utils.redis_conn(redis_url)

        created_time_tpl = data_model.NOTION_INBOX_CREATED_TIME_KEY
        redis_key = created_time_tpl.format("article", "default")

        utils.redis_set(redis_conn, redis_key, last_created_time)
