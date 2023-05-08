import os

import utils
import data_model


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
        source="article",
        list_name="default"
    ):
        """
        Mark a notion toRead item as visited
        """
        redis_url = os.getenv("BOT_REDIS_URL")
        redis_conn = utils.redis_conn(redis_url)

        # Mark toread item as visited
        toread_key_tpl = data_model.NOTION_TOREAD_ITEM_ID
        toread_key = toread_key_tpl.format(source, list_name, item_id)
        utils.redis_set(redis_conn, toread_key, "true")

    def updateCreatedTime(
        self,
        last_created_time: str,
        source="article",
        list_name="default",
    ):
        print(f"[updateCreatedTime] last_created_time: {last_created_time}")
        redis_url = os.getenv("BOT_REDIS_URL")
        redis_conn = utils.redis_conn(redis_url)

        # Update the latest created time
        created_time_tpl = data_model.NOTION_INBOX_CREATED_TIME_KEY
        redis_key = created_time_tpl.format(source, list_name)

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
