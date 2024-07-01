import os
import time
import copy
import traceback
from datetime import timedelta, datetime

import pytz
from notion import NotionAgent
from llm_agent import (
    LLMAgentCategoryAndRanking,
    LLMAgentSummary,
)
import utils
from ops_base import OperatorBase
from db_cli import DBClient
from ops_notion import OperatorNotion


class OperatorYoutube(OperatorBase):
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
    def pull(self, **kwargs):
        print("#####################################################")
        print("# Pulling Youtube video transcripts")
        print("#####################################################")
        data_folder = kwargs.setdefault("data_folder", "")
        run_id = kwargs.setdefault("run_id", "")
        print(f"data_folder: {data_folder}, run_id: {run_id}")

        # 1. prepare notion agent and db connection
        notion_api_key = os.getenv("NOTION_TOKEN")
        notion_agent = NotionAgent(notion_api_key)

        client = DBClient()
        last_created_time = client.get_notion_inbox_created_time(
            "youtube", "default")

        last_created_time = utils.bytes2str(last_created_time)
        print(f"Get last_created_time from redis: {last_created_time}")

        if not last_created_time:
            last_created_time = (datetime.now() - timedelta(days=1)).isoformat()

        # 2. get inbox database indexes
        # db_index_id = os.getenv("NOTION_DATABASE_ID_INDEX_INBOX")
        op_notion = OperatorNotion()
        db_index_id = op_notion.get_index_inbox_dbid()

        db_pages = utils.get_notion_database_pages_inbox(
            notion_agent, db_index_id, "Youtube")
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
            extracted_pages = notion_agent.queryDatabaseInbox_Youtube(
                database_id,
                filter_created_time=last_created_time)

            # The extracted pages contains
            # - title
            # - video url
            # Pull transcipt and merge it
            for page_id, extracted_page in extracted_pages.items():
                page = copy.deepcopy(extracted_page)
                title = page["title"]

                # Notes: some app (e.g. From iOS) will only fill the title
                # with the url link, it wont fill other fields
                source_url = page["source_url"] or title
                print(f"====== [Pulling youtube transcript]: title: {title}, page_id: {page_id}, source_url: {source_url} ======")

                try:
                    transcript, metadata = utils.load_video_transcript(
                        source_url,  # video
                        source_url,  # audio
                        page_id=page_id,
                        data_folder=data_folder,
                        run_id=run_id)

                    print(f"Pulled youtube transcipt, metadata: {metadata}")

                    page["__transcript"] = transcript

                    page["__title"] = metadata.setdefault("title", "")
                    page["__description"] = metadata.setdefault("description", "")
                    page["__thumbnail_url"] = metadata.setdefault("thumbnail_url", "")
                    page["__publish_date"] = ""
                    if metadata.get("publish_date"):
                        # Notes: pd is datetime object or str
                        pd = metadata["publish_date"]

                        if isinstance(pd, str):
                            page["__publish_date"] = pd

                        else:
                            pd_pdt = pd.astimezone(pytz.timezone('America/Los_Angeles'))
                            page["__publish_date"] = pd_pdt.isoformat()

                    page["__author"] = metadata.setdefault("author", "")
                    page["__view_count"] = metadata.setdefault("view_count", 0)

                    # unit: second
                    page["__length"] = metadata.setdefault("length", 0)

                    pages[page_id] = page
                    print(f"Page pulled succeed, title {title}, source_url: {source_url}")

                except Exception as e:
                    print(f"[ERROR] Exception occurred during pulling Youtube video: {title}, page_id: {page_id}, source_url: {source_url} : {e}")

        return pages

    def dedup(self, extractedPages, target="toread"):
        print("#####################################################")
        print("# Dedup Youtube pages")
        print("#####################################################")
        print(f"Number of pages: {len(extractedPages)}")

        client = DBClient()
        deduped_pages = []

        for page_id, page in extractedPages.items():
            title = page["title"]
            print(f"Dedupping page, title: {title}")

            if client.get_notion_toread_item_id(
                    "youtube", "default", page_id):
                print(f"Duplicated youtube found, skip. page_id: {page_id}")
            else:
                deduped_pages.append(page)

        return deduped_pages

    def summarize(self, pages):
        print("#####################################################")
        print("# Summarize Youtube transcripts")
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
            print(f"====== Summarying page, title: {title} ======")

            content = page["__transcript"]
            source_url = page["source_url"]
            print(f"Summarying page, source_url: {source_url}")
            print(f"Page content ({len(content)} chars): {content[:200]}...")

            st = time.time()
            summary = ""

            llm_summary_resp = client.get_notion_summary_item_id(
                "youtube", "default", page_id)

            if not llm_summary_resp:
                if not content:
                    print(f"[ERROR] Empty Youtube transcript loaded, title: {title}, source_url: {source_url}, skip it")
                    continue

                content = content[:SUMMARY_MAX_LENGTH]

                try:
                    summary = llm_agent.run(content)

                    print(f"Cache llm response for {redis_key_expire_time}s, page_id: {page_id}, summary: {summary}")

                    client.set_notion_summary_item_id(
                        "youtube", "default", page_id, summary,
                        expired_time=int(redis_key_expire_time))

                except Exception as e:
                    print(f"[ERROR] Exception during llm_agent.run(): {e}")

                if not summary and os.getenv("LLM_PROVIDER", "") != "openai":
                    print("Fallback to OpenAI")
                    fallback_agent = LLMAgentSummary()
                    fallback_agent.init_prompt()
                    fallback_agent.init_llm(provider="openai")

                    summary = fallback_agent.run(content)

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
        print("# Rank Youtubes")
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
                "youtube", "default", page_id)

            category_and_rank_str = None

            if not llm_ranking_resp:
                print("Not found category_and_rank_str in cache, fallback to llm_agent to rank")
                category_and_rank_str = llm_agent.run(text)

                print(f"Cache llm response for {redis_key_expire_time}s, page_id: {page_id}")

                client.set_notion_ranking_item_id(
                    "youtube", "default", page_id,
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

    def push(self, ranked_data, targets, topk=3):
        print("#####################################################")
        print("# Push Youtubes")
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
                        title = ranked_page.get("__title") or ranked_page["title"]
                        print(f"Pushing page, title: {title}")

                        topics = ranked_page["__topics"]
                        topics_topk = utils.get_top_items(topics, topk)
                        topics_topk = [x[0].replace(",", " ")[:20] for x in topics_topk]

                        categories = ranked_page["__categories"]
                        categories_topk = utils.get_top_items(categories, topk)
                        categories_topk = [x[0].replace(",", " ")[:20] for x in categories_topk]

                        rating = ranked_page["__rate"]

                        notion_agent.createDatabaseItem_ToRead_Youtube(
                            database_id,
                            ranked_page,
                            topics_topk,
                            categories_topk,
                            rating)

                        self.markVisited(page_id, source="youtube", list_name="default")

                        created_time = ranked_page["created_time"]
                        self.updateCreatedTime(created_time, source="youtube", list_name="default")

                    except Exception as e:
                        print(f"[ERROR]: Push to notion failed, skip: {e}")
                        stat["error"] += 1
                        traceback.print_exc()

            else:
                print(f"[ERROR]: Unknown target {target}, skip")

        return stat
