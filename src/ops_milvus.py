import traceback
from datetime import date

from db_cli import DBClient
from notion import NotionAgent
from milvus_cli import MilvusClient
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
            new_user_rating = page["user_rating"]
            print(f"Dedupping page, title: {name}, source: {source}, user_rating: {new_user_rating}")

            if client.get_milvus_perf_data_item_id(
                    source, start_date, page_id):
                print(f"Duplicated obsidian found, skip. page_id: {page_id}")
                page_metadatas = self.get_pages([page_id], db_client=client)

                if len(page_metadatas) == 0:
                    print("Not page metadata found, skip")
                    continue

                # Check user_rating changed or not
                page_metadata = page_metadatas[0]
                cur_user_rating = page_metadata.get("user_rating")

                if cur_user_rating != new_user_rating:
                    updated_pages.append(page)

                    print(f"Append page to updated_pages due to user rating changed, cur_user_rating: {cur_user_rating}, new_user_rating: {new_user_rating}")

            else:
                deduped_pages.append(page)

        print(f"Pages after dedup: {len(deduped_pages)}")
        return deduped_pages, updated_pages

    def update(self, source, pages: list, **kwargs):
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
                "last_edited_time": last_edited_time,
                "user_rating": user_rating,
            }

            try:
                client.set_page_item_id(
                    source, page_id, data, expired_time=key_ttl)

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
            page_metadata = utils.fix_and_parse_json(page_metadata)

            pages.append(page_metadata)

        return pages

    def get_relevant(self, start_date, text: str, topk: int = 5):
        print("#####################################################")
        print("# Get relevant Milvus pages")
        print("#####################################################")

        collection_name = f"news_embedding__{start_date}"
        print(f"[get_relevant] collection_name: {collection_name}")

        client = DBClient()
        milvus_client = MilvusClient()

        response_arr = milvus_client.get(collection_name, text, topk=5)
        res = []

        for response in response_arr:
            print(f"Processing response: {response}")

            page_id = response["item_id"]
            page_metadata = client.get_page_item_id(page_id)
            page_metadata = utils.fix_and_parse_json(page_metadata)

            res.append(page_metadata)

        return res

    def score(self, relevant_page_metas: list):
        """
        @param relevant_page_metas: From get_relevant

        @return the average rating of all the user ratings
        """

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
        """
        print("#####################################################")
        print("# Push Milvus pages")
        print("#####################################################")
        source = kwargs.setdefault("source", "")
        start_date = kwargs.setdefault(
            "start_date", date.today().isoformat())

        collection_name = f"news_embedding__{start_date}"
        print(f"source: {source}, start_date: {start_date}")

        client = DBClient()
        notion_agent = NotionAgent()
        milvus_client = MilvusClient()

        if not milvus_client.exist(collection_name):
            self._create_collection(collection_name, pages, source, start_date)
            return

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
                embedding = client.get_milvus_embedding_item_id(
                    source, page_id)

                if not embedding:
                    embedding = milvus_client.createEmbedding(content)
                else:
                    embedding = utils.bytes2str(embedding)

                # store embedding into redis (ttl = 1 month)
                client.set_milvus_embedding_item_id(
                    source, page_id, embedding, expired_time=key_ttl)

                # push to milvus
                milvus_client.add(
                    collection_name,
                    page_id,
                    content,
                    embed=embedding)

                self.markVisisted(
                    source, page_id, start_date, db_client=client)

            except Exception as e:
                print(f"[ERROR] Failed to push to Milvus: {e}")
                traceback.print_exc()
                err += 1

            # TODO: Remove it after testing
            break

        print(f"[INFO] Finished, total {tot}, skipped: {skipped}, errors: {err}")

    def markVisisted(self, source, page_id, dt, db_client=None):
        client = db_client or DBClient()
        client.set_milvus_perf_data_item_id(
            source, dt, page_id)
