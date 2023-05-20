from abc import ABC, abstractmethod


class Embedding(ABC):
    def __init__(self, model_name="openai"):
        self.model_name = model_name

    @abstractmethod
    def dim(self):
        pass

    @abstractmethod
    def getname(self, start_date, prefix="news"):
        pass

    @abstractmethod
    def create(self, text: str):
        pass

    @abstractmethod
    def get_or_create(self, text: str, source="", page_id="", db_client=None):
        pass
