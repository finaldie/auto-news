import os
import time
from datetime import datetime, timedelta

import utils
from db_cli import DBClient
from notion import NotionAgent
from ops_notion import OperatorNotion
from ops_stats import OpsStats


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

        op_notion = OperatorNotion()

        # db_index_id = os.getenv("NOTION_DATABASE_ID_INDEX_TOREAD")
        db_index_id = op_notion.get_index_toread_dbid()

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

    def load_folders(self, folders: list, target_filename: str):
        """
        Load target_filename from folder_path
        """
        file_list = []
        print(f"Loading folders: {folders}")

        for folder_path in folders:
            for root, dirs, files in os.walk(folder_path):
                for filename in files:
                    if filename != target_filename:
                        continue

                    file_path = os.path.join(root, filename)
                    file_list.append(file_path)

                    print(f"Found file to read: {file_path}")

        pages = []
        for file_path in file_list:
            page = utils.read_data_json(file_path)
            pages.append(page)

        return pages

    def unique(self, data: list):
        """
        For same page_id, keep one copy with latest edited time
        """
        deduped_pages = {}

        for pages in data:
            for page_id, page in pages.items():
                name = page["name"]
                last_edited_time = page["last_edited_time"]
                last = utils.parseDataFromIsoFormat(last_edited_time)

                print(f"Dedupping page name: {name}, last_edited_time: l{last_edited_time} ...")

                if not deduped_pages.get(page_id):
                    deduped_pages[page_id] = page

                else:
                    curr_page = deduped_pages[page_id]
                    curr_edited_time = curr_page["last_edited_time"]
                    curr = utils.parseDataFromIsoFormat(curr_edited_time)

                    if last > curr:
                        deduped_pages[page_id] = page
                        print(f"Overwrite the page due to it's latest one, last: {last}, curr: {curr}")

        return deduped_pages

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

    def score(self, data):
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
        if not last_created_time:
            print("No last_created_time, skip updating")
            return

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

    def createStats(
        self,
        source: str,
        category: str,
        data_input: dict,
        data_deduped=None,
        data_summarized=None,
        data_scored=None,
        data_filtered=None,
        data_ranked=None,
        pushed_stats=None
    ):
        data_dict = {
            "total_input": data_input,
            "post_deduping": data_deduped,
            "post_summary": data_summarized,
            "post_scoring": data_scored,
            "post_filtering": data_filtered,
            "total_pushed": data_ranked,
        }

        stat = OpsStats(source, category)

        for counter_name, data in data_dict.items():
            if not data:
                continue

            if isinstance(data, dict):
                stat.getCounter(counter_name).set(len(data.keys()))
            elif isinstance(data, list):
                stat.getCounter(counter_name).set(len(data))

        stat.getCounter("total_pushed").set(pushed_stats["total"])
        return [stat]

    def pull_takeaways(self, **kwargs):
        print("#####################################################")
        print("# Pulling Pages: Takeaways ...")
        print("#####################################################")
        sources = kwargs.setdefault("sources", ["Youtube", "Article", "Twitter", "RSS", "Reddit", "Journal", "TODO", "DeepDive"])
        category = kwargs.setdefault("category", "todo")

        now = datetime.now()
        start_time = now

        print(f"start_time: {start_time}, pulling sources: {sources}, category: {category}")

        # 1. prepare notion agent and db connection
        notion_api_key = os.getenv("NOTION_TOKEN")
        notion_agent = NotionAgent(notion_api_key)
        op_notion = OperatorNotion()

        # 2. get toread database indexes
        # db_index_id = os.getenv("NOTION_DATABASE_ID_INDEX_TOREAD")
        db_index_id = op_notion.get_index_toread_dbid()

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
                print(f"====== Pulling source: {source} ======")
                client = DBClient()

                last_edited_time = client.get_notion_last_edited_time(
                    source, category)
                last_edited_time = utils.bytes2str(last_edited_time)

                if not last_edited_time:
                    last_edited_time = (datetime.now() - timedelta(days=1)).isoformat()

                print(f"Notion last_edited_time: {last_edited_time}, source: {source}")

                # Pull the pages with user_ratings >= last_edited_time
                # format dict(<page_id, page>)
                pages = notion_agent.queryDatabaseToRead(
                    database_id,
                    source,
                    last_edited_time=last_edited_time,
                    extraction_interval=0.02,
                    require_user_rating=False)

                print(f"Pulled {len(pages)} pages for source: {source}")
                page_list.update(pages)

                # Wait a moment to mitigate rate limiting
                wait_for_secs = 5
                print(f"Wait for a moment: {wait_for_secs}s")
                time.sleep(wait_for_secs)

        print(f"Pulled total {len(page_list)} items")
        return page_list

    def pull_journal(self, **kwargs):
        print("#####################################################")
        print("# Pulling Pages: Journal Inbox ...")
        print("#####################################################")
        category = kwargs.setdefault("category", "todo")

        client = DBClient()
        last_edited_time = client.get_notion_last_edited_time(
            "Journal", category)

        last_edited_time = utils.bytes2str(last_edited_time)
        print(f"Get last_edited_time from redis: {last_edited_time}")

        if not last_edited_time:
            last_edited_time = (datetime.now() - timedelta(days=1)).isoformat()

        print(f"last_edited_time: {last_edited_time}")

        # 1. prepare notion agent and db connection
        notion_api_key = os.getenv("NOTION_TOKEN")
        notion_agent = NotionAgent(notion_api_key)
        op_notion = OperatorNotion()

        # 2. get inbox database indexes
        db_index_id = op_notion.get_index_inbox_dbid()

        db_pages = utils.get_notion_database_pages_inbox(
            notion_agent, db_index_id, "Journal")
        print(f"The database pages founded: {db_pages}")

        # 2. get latest two databases and collect recent items
        db_pages = db_pages[:2]
        print(f"The latest 2 databases: {db_pages}")

        page_list = {}
        sources = kwargs.setdefault("sources", ["Journal"])

        for db_page in db_pages:
            database_id = db_page["database_id"]
            print(f"Pulling from database_id: {database_id}...")

            for source in sources:
                print(f"Querying source: {source} ...")
                # The api will return the pages and sort by "created time" asc
                # format dict(<page_id, page>)
                pages = notion_agent.queryDatabaseInbox_Journal(
                    database_id,
                    filter_last_edited_time=last_edited_time)

                page_list.update(pages)

                # Wait a moment to mitigate rate limiting
                wait_for_secs = 5
                print(f"Wait for a moment: {wait_for_secs}s")
                time.sleep(wait_for_secs)

        print(f"Pulled total {len(page_list)} items")
        return page_list
