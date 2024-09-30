from abc import abstractmethod
import re


class Embedding:
    def __init__(self, model_name):
        self.model_name = model_name

    def getname(self, start_date, prefix="news"):
        """
        Get the name of the milvus collection for the embedding
        We are only allowed to use alphanumeric characters and underscores in the collection name
        """
        # Replace any non-alphanumeric character in the model name with an underscore
        sanitized_model_name = re.sub(r'\W+', '_', self.model_name)
        sanitized_start_date = start_date.replace('-', '_')
        return f"{prefix}_{sanitized_model_name}__{sanitized_start_date}"

    @abstractmethod
    def dim(self):
        pass

    @abstractmethod
    def create(self, text: str):
        pass

    @abstractmethod
    def get_or_create(self, text: str, source="", page_id="", db_client=None):
        pass
