import os
from datetime import datetime, timedelta

import utils
from db_cli import DBClient
from notion import NotionAgent


class OperatorBase:
    """
    Operator Base class
    """

    def pull(self):
        return None

    def sync(self, source):
        """
        Sync content items from notion ToRead database, conditions:
        - All items >= last_edited_time
        - Items with user rating
        """
        notion_api_key = os.getenv("NOTION_TOKEN")
        notion_agent = NotionAgent(notion_api_key)

        db_index_id = os.getenv("NOTION_DATABASE_ID_INDEX_TOREAD")
        db_pages = utils.get_notion_database_pages_toread(
            notion_agent, db_index_id)

        if len(db_pages) == 0:
            print("[ERROR] No valid ToRead databases found")
            return {}

        client = DBClient()
        last_edited_time = client.get_notion_last_edited_time(
            source, "default")
        last_edited_time = utils.bytes2str(last_edited_time)

        if not last_edited_time:
            last_edited_time = (datetime.now() - timedelta(days=365)).isoformat()

        print(f"Start syncing content, last_edited_time: {last_edited_time}")

        data = {}

        for db_page in db_pages:
            database_id = db_page["database_id"]

            pages = notion_agent.queryDatabaseToRead(
                database_id, source, last_edited_time=last_edited_time)

            for page_id, page in pages.items():
                name = page["name"]
                user_rating = page["user_rating"]
                cur_edited_time = page["last_edited_time"]
                cur = utils.parseDataFromIsoFormat(cur_edited_time)

                if not user_rating:
                    print("[INFO] Skip sync the content, user rating is empty")
                    continue

                print(f"Syncing page: {name}")

                old_page = data.get(page_id)
                if not old_page:
                    print(f"[INFO] Sync the content, user rating: {user_rating}")
                    data[page_id] = page
                else:
                    old_user_rating = old_page["user_rating"]

                    # Use most recent page to overwrite
                    old_edited_time = old_page["last_edited_time"]
                    old = utils.parseDataFromIsoFormat(old_edited_time)

                    if cur > old:
                        print(f"Current page is newer, overwrite old one, old: {old}, cur: {cur}, old rating: {old_user_rating}, new rating: {user_rating}")
                        data[page_id] = page
                    else:
                        print(f"Current page is older, do nothing, old: {old}, cur: {cur}")

        print(f"Synced pages: {len(data.keys())}")
        return data

    def updateLastEditedTimeForData(
        self,
        data,
        source="Article",
        list_name="default",
        db_client=None
    ):
        client = db_client or DBClient()

        for page_id, page in data.items():
            last_edited_time = page["last_edited_time"]

            self.updateLastEditedTime(last_edited_time, source, list_name, db_client=client)

        print("Finished for updating last_edited_time")

    def save2json(
        self,
        data_folder,
        run_id,
        filename,
        data
    ):
        workdir = os.getenv("WORKDIR")

        data_path = f"{workdir}/{data_folder}/{run_id}"
        full_path = utils.gen_filename(data_path, filename)

        print(f"Save data to {full_path}, data: {data}")
        utils.save_data_json(full_path, data)

    def readFromJson(self, data_folder, run_id, filename):
        workdir = os.getenv("WORKDIR")

        data_path = f"{workdir}/{data_folder}/{run_id}"
        full_path = utils.gen_filename(data_path, filename)

        data = utils.read_data_json(full_path)

        print(f"Retrieve data from {full_path}, data: {data}")
        return data

    def dedup(self, data, target):
        return

    def summarize(self, data):
        return

    def rank(self, data):
        return

    def push(self, ranked_data, targets, topk=3):
        return

    def markVisited(
        self,
        item_id: str,
        source="Article",
        list_name="default",
        db_client=None
    ):
        """
        Mark a notion toRead item as visited
        """
        client = db_client or DBClient()
        client.set_notion_toread_item_id(source, list_name, item_id)

    def updateCreatedTime(
        self,
        last_created_time: str,
        source="Article",
        list_name="default",
        db_client=None
    ):
        print(f"[updateCreatedTime] last_created_time: {last_created_time}")
        client = db_client or DBClient()

        curr_created_time = client.get_notion_inbox_created_time(source, list_name)
        curr_created_time = utils.bytes2str(curr_created_time)
        print(f"Updating created time: curr_created_time: {curr_created_time}")

        curr = utils.parseDataFromIsoFormat(curr_created_time)
        last = utils.parseDataFromIsoFormat(last_created_time)

        if not curr_created_time or last > curr:
            client.set_notion_inbox_created_time(
                source, list_name, last_created_time, overwrite=True)

            print(f"Update Last created time curr: {curr_created_time}, set to {last_created_time}")

    def updateLastEditedTime(
        self,
        last_edited_time: str,
        source="Article",
        list_name="default",
        db_client=None
    ):
        print(f"[updateLastEditedTime] last_edited_time: {last_edited_time}")
        client = db_client or DBClient()

        curr_edited_time = client.get_notion_last_edited_time(source, list_name)
        curr_edited_time = utils.bytes2str(curr_edited_time)
        print(f"Updating last edited time: curr_edited_time: {curr_edited_time}")

        curr = utils.parseDataFromIsoFormat(curr_edited_time)
        last = utils.parseDataFromIsoFormat(last_edited_time)

        if not curr_edited_time or last > curr:
            client.set_notion_last_edited_time(
                source, list_name, last_edited_time, overwrite=True)

            print(f"Update Last edited time curr: {curr_edited_time}, set to {last_edited_time}")
