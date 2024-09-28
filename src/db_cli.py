from db_cli_base import DBClientBase
from redis_cli import RedisClient

import data_model


class DBClient(DBClientBase):
    def __init__(self, driver=None):
        super().__init__(driver=driver)

        if not self.driver:
            self.driver = RedisClient()
            print("[INFO] Initialized default DB driver (Redis)")

    def get_notion_inbox_created_time(self, source, category):
        key_tpl = data_model.NOTION_INBOX_CREATED_TIME_KEY
        key = key_tpl.format(source, category)
        return self.driver.get(key)

    def set_notion_inbox_created_time(self, source, category, t, **kwargs):
        key_tpl = data_model.NOTION_INBOX_CREATED_TIME_KEY
        key = key_tpl.format(source, category)
        self.driver.set(key, t, **kwargs)

    def get_notion_toread_item_id(self, source, category, item_id):
        key_tpl = data_model.NOTION_TOREAD_ITEM_ID
        key = key_tpl.format(source, category, item_id)
        return self.driver.get(key)

    def set_notion_toread_item_id(self, source, category, item_id, **kwargs):
        key_tpl = data_model.NOTION_TOREAD_ITEM_ID
        key = key_tpl.format(source, category, item_id)
        self.driver.set(key, "true", **kwargs)

    def get_notion_last_edited_time(self, source, category):
        key_tpl = data_model.NOTION_TOREAD_LAST_EDITED_KEY
        key = key_tpl.format(source, category)
        return self.driver.get(key)

    def set_notion_last_edited_time(self, source, category, t, **kwargs):
        key_tpl = data_model.NOTION_TOREAD_LAST_EDITED_KEY
        key = key_tpl.format(source, category)
        self.driver.set(key, t, **kwargs)

    def get_notion_ranking_item_id(self, source, category, item_id):
        key_tpl = data_model.NOTION_RANKING_ITEM_ID
        key = key_tpl.format(source, category, item_id)
        return self.driver.get(key)

    def set_notion_ranking_item_id(
        self,
        source,
        category,
        item_id,
        r: str,
        **kwargs
    ):
        key_tpl = data_model.NOTION_RANKING_ITEM_ID
        key = key_tpl.format(source, category, item_id)
        self.driver.set(key, r, **kwargs)

    def get_notion_summary_item_id(self, source, category, item_id):
        key_tpl = data_model.NOTION_SUMMARY_ITEM_ID
        key = key_tpl.format(source, category, item_id)
        return self.driver.get(key)

    def set_notion_summary_item_id(
        self,
        source,
        category,
        item_id,
        s: str,
        **kwargs
    ):
        key_tpl = data_model.NOTION_SUMMARY_ITEM_ID
        key = key_tpl.format(source, category, item_id)
        self.driver.set(key, s, **kwargs)

    def get_obsidian_inbox_item_id(self, source, category, item_id):
        key_tpl = data_model.OBSIDIAN_INBOX_ITEM_ID
        key = key_tpl.format(source, category, item_id)
        return self.driver.get(key)

    def set_obsidian_inbox_item_id(self, source, category, item_id, **kwargs):
        key_tpl = data_model.OBSIDIAN_INBOX_ITEM_ID
        key = key_tpl.format(source, category, item_id)
        self.driver.set(key, "true", **kwargs)

    def get_milvus_embedding_item_id(
        self,
        provider,
        model_name,
        source,
        item_id
    ):
        key_tpl = data_model.MILVUS_EMBEDDING_ITEM_ID
        key = key_tpl.format(provider, model_name, source, item_id)
        return self.driver.get(key)

    def set_milvus_embedding_item_id(
        self,
        provider,
        model_name,
        source,
        item_id,
        embed: list,
        **kwargs
    ):
        key_tpl = data_model.MILVUS_EMBEDDING_ITEM_ID
        key = key_tpl.format(provider, model_name, source, item_id)
        self.driver.set(key, embed, **kwargs)

    def get_milvus_perf_data_item_id(self, source, dt: str, item_id):
        key_tpl = data_model.MILVUS_PERF_DATA_ITEM_ID
        key = key_tpl.format(source, dt, item_id)
        return self.driver.get(key)

    def set_milvus_perf_data_item_id(
        self,
        source,
        dt: str,
        item_id,
        **kwargs
    ):
        key_tpl = data_model.MILVUS_PERF_DATA_ITEM_ID
        key = key_tpl.format(source, dt, item_id)
        self.driver.set(key, "true", **kwargs)

    def get_page_item_id(self, item_id):
        key_tpl = data_model.PAGE_ITEM_ID
        key = key_tpl.format(item_id)
        return self.driver.get(key)

    def set_page_item_id(
        self,
        item_id,
        json_data: str,
        **kwargs
    ):
        key_tpl = data_model.PAGE_ITEM_ID
        key = key_tpl.format(item_id)
        self.driver.set(key, json_data, **kwargs)

    # TODO: Switch to MySQL driver
    def get_todo_item_id(self, item_id):
        key_tpl = data_model.TODO_ITEM_ID
        key = key_tpl.format(item_id)
        return self.driver.get(key)

    def set_todo_item_id(
        self,
        item_id,
        json_data: str,
        **kwargs
    ):
        key_tpl = data_model.TODO_ITEM_ID
        key = key_tpl.format(item_id)
        self.driver.set(key, json_data, **kwargs)

    # TODO: Switch to MySQL driver
    def get_action_item_id(self, item_id):
        key_tpl = data_model.ACTION_ITEM_ID
        key = key_tpl.format(item_id)
        return self.driver.get(key)

    def set_action_item_id(
        self,
        item_id,
        json_data: str,
        **kwargs
    ):
        key_tpl = data_model.ACTION_ITEM_ID
        key = key_tpl.format(item_id)
        self.driver.set(key, json_data, **kwargs)
