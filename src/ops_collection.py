import os
import copy
import traceback
from datetime import datetime, timedelta

import utils
from notion import NotionAgent
from ops_base import OperatorBase
from db_cli import DBClient
from ops_milvus import OperatorMilvus


class OperatorCollection(OperatorBase):
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
        """
        Pull Collection

        @return pages <id, page>
        """
        print("#####################################################")
        print("# Pulling ToRead Items")
        print("#####################################################")
        collection_type = kwargs.setdefault("collection_type", "weekly")
        sources = kwargs.setdefault("sources", ["Youtube", "Article", "Twitter", "RSS"])

        print(f"collection_type: {collection_type}, sources: {sources}")

        now = datetime.now()
        start_time = now

        if collection_type == "weekly":
            start_time = now - timedelta(weeks=1)

        print(f"start_time: {start_time}")

        # 1. prepare notion agent and db connection
        notion_api_key = os.getenv("NOTION_TOKEN")
        notion_agent = NotionAgent(notion_api_key)

        # 2. get toread database indexes
        db_index_id = os.getenv("NOTION_DATABASE_ID_INDEX_TOREAD")
        db_pages = utils.get_notion_database_pages_toread(
            notion_agent, db_index_id)
        print(f"The database pages founded: {db_pages}")

        # 2. get latest two databases and collect recent items
        db_pages = db_pages[:2]
        print(f"The latest 2 databases: {db_pages}")

        page_list = {}

        for db_page in db_pages:
            database_id = db_page["database_id"]
            print(f"Pulling from database_id: {database_id}...")

            for source in sources:
                # The api will return the pages and sort by "created time" asc
                # format dict(<page_id, page>)
                pages = notion_agent.queryDatabaseToRead(
                    database_id, source, last_edited_time=start_time.isoformat())

                page_list.update(pages)

        print(f"Pulled total {len(page_list)} items")
        return page_list

    def pre_filter(self, pages, **kwargs):
        """
        Pre filter all pages with user rating >= min_score
        """
        print("#####################################################")
        print("# Pre-Filter Collection")
        print("#####################################################")
        min_score = kwargs.setdefault("min_score", 4)
        print(f"input size: {len(pages)}, min_score: {min_score}")

        notion_api_key = os.getenv("NOTION_TOKEN")
        notion_agent = NotionAgent(notion_api_key)

        # 1. filter all score >= min_score or contains take aways msg
        filtered1 = []
        for page_id, page in pages.items():
            print(f"page: {page}")
            user_rating = page["user_rating"]

            take_aways = notion_agent.extractRichText(
                page["properties"]["properties"]["Take Aways"]["rich_text"])

            if user_rating >= min_score or take_aways:
                filtered1.append(page)

        print(f"Filter output size: {len(filtered1)}")
        return filtered1

    def post_filter(self, pages, **kwargs):
        """
        Post filter all pages with relevant score >= min_score
        """
        print("#####################################################")
        print("# Post-Filter Collection")
        print("#####################################################")
        k = kwargs.setdefault("k", 3)
        min_score = float(kwargs.setdefault("min_score", 4.5))
        print(f"k: {k}, input size: {len(pages)}, min_score: {min_score}")

        # 1. filter all score >= min_score
        filtered1 = []
        for page in pages:
            relevant_score = float(page["__relevant_score"])
            print(f"- Relevant score: {relevant_score}, min_score: {min_score}")

            if relevant_score >= min_score:
                filtered1.append(page)

        # 2. get top k
        tops = sorted(filtered1, key=lambda page: page["__relevant_score"], reverse=True)
        print(f"After sorting: {tops}")

        filtered2 = []
        for i in range(min(k, len(tops))):
            filtered2.append(tops[i])

        print(f"Filter output size: {len(filtered2)}")
        return filtered2

    def score(self, data, **kwargs):
        print("#####################################################")
        print("# Scoring Collection pages")
        print("#####################################################")
        start_date = kwargs.setdefault("start_date", "")
        max_distance = kwargs.setdefault("max_distance", 0.45)
        top_k_similar = kwargs.setdefault("top_k_similar", 3)
        print(f"start_date: {start_date}, top_k_similar: {top_k_similar}, max_distance: {max_distance}")

        op_milvus = OperatorMilvus()
        client = DBClient()

        notion_api_key = os.getenv("NOTION_TOKEN")
        notion_agent = NotionAgent(notion_api_key)

        scored_list = []

        for page in data:
            try:
                page_id = page["id"]

                score_text = notion_agent.concatBlocksText(
                    page["blocks"], separator="\n")
                # score_text = score_text[:2048]

                take_aways = notion_agent.extractRichText(
                    page["properties"]["properties"]["Take Aways"]["rich_text"])
                if take_aways:
                    score_text += f"\nTake aways: {take_aways}"

                title = page.get("name") or ""
                print(f"Scoring page: {title}, score_text: {score_text}")

                relevant_metas = op_milvus.get_relevant(
                    start_date, score_text, topk=top_k_similar,
                    max_distance=max_distance, db_client=client)

                # Exclude the page itself
                scoring_metadata = [x for x in relevant_metas if x['page_id'] != page_id]

                page_score = op_milvus.score(scoring_metadata)

                scored_page = copy.deepcopy(page)
                scored_page["__relevant_score"] = page_score

                scored_list.append(scored_page)
                print(f"Collection page scored: {page_score}")

            except Exception as e:
                print(f"[ERROR]: Score page failed, skip: {e}")
                traceback.print_exc()

        print(f"Scored_pages ({len(scored_list)}): {scored_list}")
        return scored_list

    def push(self, pages, targets, **kwargs):
        print("#####################################################")
        print("# Push Collection Pages")
        print("#####################################################")
        print(f"Number of pages: {len(pages)}")
        print(f"Targets: {targets}")
        print(f"Input data: {pages}")

        collection_type = kwargs.setdefault("collection_type", "weekly")
        collection_source_type = f"collection_{collection_type}"
        print(f"Collection type: {collection_type}")

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

                for page in pages:
                    try:
                        title = page["name"]

                        # Modify page source and list_name
                        page["list_name"] = [page["source"]]
                        page["source"] = collection_source_type

                        print(f"Pushing page, title: {title}, source: {page['source']}, list_name: {page['list_name']}")

                        topics_topk = page.get("topic") or ""
                        categories_topk = page.get("categories") or ""
                        rating = page.get("user_rating") or -3

                        page_take_aways = notion_agent.extractRichText(page["properties"]["properties"]["Take Aways"]["rich_text"])
                        page["__take_aways"] = page_take_aways

                        notion_agent.createDatabaseItem_ToRead_Collection(
                            database_id,
                            page,
                            topics_topk,
                            categories_topk,
                            rating,
                            prop_add_take_away=True)

                        # For collection, we don't need mark as visited
                        # self.markVisited(
                        #     page_id,
                        #     source=collection_source_type)

                    except Exception as e:
                        print(f"[ERROR]: Push to notion failed, skip: {e}")
                        traceback.print_exc()

            else:
                print(f"[ERROR]: Unknown target {target}, skip")
