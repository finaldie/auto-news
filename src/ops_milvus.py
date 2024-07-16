import os
import json
import copy
import traceback
from datetime import date, timedelta

from db_cli import DBClient
from notion import NotionAgent
from milvus_cli import MilvusClient
from embedding_agent import EmbeddingAgent
import embedding_utils as emb_utils
import utils


class OperatorMilvus:
    def dedup(self, pages, **kwargs):
        """
        data: {
            "page_id1": page1,
            "page_id2": page2,
            ...
        }
        """
        print("#####################################################")
        print("# Dedup Milvus pages")
        print("#####################################################")
        client = DBClient()
        deduped_pages = []
        updated_pages = []  # user rating changed
        source = kwargs.setdefault("source", date.today().isoformat())
        start_date = kwargs.setdefault(
            "start_date", date.today().isoformat())

        for page_id, page in pages.items():
            name = page["name"]
            new_user_rating = int(page["user_rating"])
            print(f"Dedupping page, title: {name}, source: {source}, user_rating: {new_user_rating}")

            if client.get_milvus_perf_data_item_id(
                    source, start_date, page_id):
                print(f"Duplicated page found, skip. page_id: {page_id}")
                page_metadatas = self.get_pages([page_id], db_client=client)

                if len(page_metadatas) == 0:
                    print("Not page metadata found, push to updating queue")
                    updated_pages.append(page)
                    continue

                # Check user_rating changed or not
                page_metadata = page_metadatas[0]
                cur_user_rating = page_metadata.get("user_rating")

                if cur_user_rating != new_user_rating:
                    updated_pages.append(page)

                    print(f"Append page to updated_pages due to user rating changed, cur_user_rating: {cur_user_rating}, new_user_rating: {new_user_rating}")

            else:
                deduped_pages.append(page)
                updated_pages.append(page)

        print(f"Pages after dedup: {len(deduped_pages)}")
        return deduped_pages, updated_pages

    def update(self, source, pages: list, **kwargs):
        print("#####################################################")
        print("# Update Milvus pages")
        print("#####################################################")
        client = DBClient()
        tot = 0
        err = 0
        key_ttl = 86400 * 30

        for page in pages:
            page_id = page["id"]
            user_rating = int(page["user_rating"])
            last_edited_time = page["last_edited_time"]
            tot += 1

            data = {
                "page_id": page_id,
                "last_edited_time": last_edited_time,
                "user_rating": user_rating,
            }

            try:
                print(f"Updating page_id: {page_id}, with ttl: {key_ttl}, data: {data}")
                client.set_page_item_id(
                    page_id, json.dumps(data), expired_time=key_ttl)

            except Exception as e:
                print(f"[ERROR] Failed to update page metadata: {e}")
                err += 1

        print(f"Pages updating finished, total {tot}, errors: {err}")

    def get_pages(self, page_ids: list, db_client=None):
        client = db_client or DBClient()
        pages = []

        for page_id in page_ids:
            # format: {user_rating: xx, ...}
            page_metadata = client.get_page_item_id(page_id)

            if not page_metadata:
                print(f"[WARN] cannot find any metadata for page_id: {page_id}, skip it")
                continue

            page_metadata = utils.fix_and_parse_json(page_metadata)

            pages.append(page_metadata)

        return pages

    def get_relevant(
        self,
        start_date,
        text: str,
        topk: int = 2,
        max_distance: float = 0.45,
        db_client=None,
        fallback=None
    ):
        """
        @param max_distance - filter out if distance > max_distance

        Notes: distance is in [0.0, 1.0], tune the max_distance for best
        needs

        Ref: https://milvus.io/blog/optimizing-billion-scale-image-search-milvus-part-2.md
        """
        # print("#####################################################")
        # print("# Get relevant Milvus pages")
        # print("#####################################################")

        emb_agent = EmbeddingAgent()

        collection_name = emb_agent.getname(start_date)
        print(f"[get_relevant] collection_name: {collection_name}")

        client = db_client or DBClient()
        milvus_client = MilvusClient(emb_agent=emb_agent)

        # get a fallback collection name
        if not fallback:
            yesterday = (date.fromisoformat(start_date) - timedelta(days=1)).isoformat()
            fallback = emb_agent.getname(yesterday)

        print(f"[get_relevant] Fallback collection name: {fallback}")

        key_ttl = 86400 * 30  # 30 days
        embedding = emb_agent.get_or_create(
            text,
            source="default",
            page_id=utils.hashcode_md5(text.encode('utf-8')),
            db_client=client,
            key_ttl=key_ttl)

        # response_arr: [{item_id, distance}, ...]
        response_arr = milvus_client.get(
            collection_name, text, topk=topk,
            fallback=fallback, emb=embedding)

        # filter by distance (similiarity value) according to the
        # metrics type
        metric_type = os.getenv("MILVUS_SIMILARITY_METRICS", "L2")
        valid_embs = emb_utils.similarity_topk(response_arr, metric_type, max_distance, topk)
        print(f"[get_relevant] metric_type: {metric_type}, max_distance: {max_distance}, raw emb response_arr size: {len(response_arr)}, post emb_utils.topk: {len(valid_embs)}")

        res = []

        for response in valid_embs:
            print(f"[get_relevant] Processing response: {response}")

            page_id = response["item_id"]
            distance = response["distance"]

            page_metadata = client.get_page_item_id(page_id)

            if not page_metadata:
                print(f"[WARN] cannot find any metadata for page_id: {page_id}, skip it")
                continue

            page_metadata = utils.fix_and_parse_json(page_metadata)
            copied_page_metadata = copy.deepcopy(page_metadata)
            copied_page_metadata["distance"] = distance

            res.append(copied_page_metadata)
            print(f"[get_relevant] found page_metadata: {copied_page_metadata}")

        return res

    def score(self, relevant_page_metas: list):
        """
        K-Mean score

        TODO: calculate score consider distance, the shorter distance
        the higher weight of the user rating

        @param relevant_page_metas: From get_relevant

        @return the average rating of all the user ratings
        """
        # print("#####################################################")
        # print("# Score Milvus pages")
        # print("#####################################################")
        print(f"relevant_page_metas({len(relevant_page_metas)}): {relevant_page_metas}")

        tot = 0
        n = len(relevant_page_metas)

        if n == 0:
            return -1  # unknown score

        for page_metadata in relevant_page_metas:
            tot += page_metadata["user_rating"]

        return tot / n

    def push(self, pages, **kwargs):
        """
        Create and push embeddings to Milvus vector database

        Notes: We only do embedding on the summary, not the original
               long content
        """
        print("#####################################################")
        print("# Push Milvus pages")
        print("#####################################################")
        source = kwargs.setdefault("source", "")
        start_date = kwargs.setdefault(
            "start_date", date.today().isoformat())

        client = DBClient()
        notion_agent = NotionAgent()
        emb_agent = EmbeddingAgent()
        milvus_client = MilvusClient(emb_agent=emb_agent)

        collection_name = emb_agent.getname(start_date)
        print(f"source: {source}, start_date: {start_date}, collection name: {collection_name}")

        if not milvus_client.exist(collection_name):
            milvus_client.createCollection(
                collection_name,
                desc=f"Collection end by {start_date}, dim: {emb_agent.dim()}",
                dim=emb_agent.dim())

            print(f"[INFO] No collection {collection_name} found, created a new one")

        # The collection exists, add new embeddings
        milvus_client.getCollection(collection_name)

        tot = 0
        err = 0
        skipped = 0
        key_ttl = 86400 * 30  # 30 days

        for page in pages:
            page_id = page["id"]
            tot += 1
            skipped = 0

            try:
                content = notion_agent.concatBlocksText(
                    page["blocks"], separator="\n")

                # Notes: the page does not exist, but the embedding
                #        maybe exist
                embedding = emb_agent.get_or_create(
                    content,
                    source=source,
                    page_id=page_id,
                    db_client=client,
                    key_ttl=key_ttl)

                # push to milvus
                milvus_client.add(
                    collection_name,
                    page_id,
                    content,
                    embed=embedding)

                self.markVisisted(
                    source, page_id, start_date,
                    db_client=client, key_ttl=key_ttl)

            except Exception as e:
                print(f"[ERROR] Failed to push to Milvus: {e}")
                traceback.print_exc()
                err += 1

        print(f"[INFO] Finished, total {tot}, skipped: {skipped}, errors: {err}")

    def markVisisted(self, source, page_id, dt, db_client=None, key_ttl=86400 * 15):
        client = db_client or DBClient()
        client.set_milvus_perf_data_item_id(
            source, dt, page_id, expired_time=key_ttl)

    def clear(self, cleanup_date):
        """
        Clean up all collections on or before the clean date
        """
        milvus_client = MilvusClient()

        collections = milvus_client.list_collections()
        print(f"Collections: {collections}")

        for name in collections:
            suffix = name.split("__")[-1]
            dt = date.fromisoformat(suffix.replace("_", "-"))
            stats = milvus_client.get_stats(name)

            print(f"Checking collection: {name}, stats: {stats}")

            if dt <= cleanup_date:
                print(f"- Cleanup collection {name}")
                milvus_client.release(name)
                milvus_client.drop(name)
