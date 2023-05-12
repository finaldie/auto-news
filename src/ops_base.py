import os

import utils
from db_cli import DBClient


class OperatorBase:
    """
    Operator Base class
    """

    def pull(self):
        return None

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
        list_name="default"
    ):
        """
        Mark a notion toRead item as visited
        """
        client = DBClient()
        client.set_notion_toread_item_id(source, list_name, item_id)

    def updateCreatedTime(
        self,
        last_created_time: str,
        source="Article",
        list_name="default",
    ):
        print(f"[updateCreatedTime] last_created_time: {last_created_time}")
        client = DBClient()

        curr_created_time = client.get_notion_inbox_created_time(source, list_name)
        curr_created_time = utils.bytes2str(curr_created_time)
        print(f"Updating created time: curr_created_time: {curr_created_time}")

        curr = utils.parseDataFromIsoFormat(curr_created_time)
        last = utils.parseDataFromIsoFormat(last_created_time)

        if not curr_created_time or last > curr:
            client.set_notion_inbox_created_time(
                source, list_name, last_created_time, overwrite=True)

            print(f"Update Last created time curr: {curr_created_time}, set to {last_created_time}")
