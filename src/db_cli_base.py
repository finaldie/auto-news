from abc import ABC, abstractmethod


class DBClientBase(ABC):
    """
    Define the abstract methods for getting the common metadata
    whatever the backend driver we use
    """
    def __init__(self, driver=None):
        self.driver = driver

    @abstractmethod
    def get_notion_inbox_created_time(self, source, category):
        pass

    @abstractmethod
    def set_notion_inbox_created_time(self, source, category, t, **kwargs):
        pass

    @abstractmethod
    def get_notion_toread_item_id(self, source, category, item_id):
        pass

    @abstractmethod
    def set_notion_toread_item_id(self, source, category, item_id, **kwargs):
        pass

    @abstractmethod
    def get_notion_last_edited_time(self, source, category):
        pass

    @abstractmethod
    def set_notion_last_edited_time(self, source, category, t, **kwargs):
        pass

    @abstractmethod
    def get_notion_ranking_item_id(self, source, category, item_id):
        pass

    @abstractmethod
    def set_notion_ranking_item_id(self, source, category, item_id, r: str, **kwargs):
        pass

    @abstractmethod
    def get_notion_summary_item_id(self, source, category, item_id):
        pass

    @abstractmethod
    def set_notion_summary_item_id(self, source, category, item_id, s: str, **kwargs):
        pass
