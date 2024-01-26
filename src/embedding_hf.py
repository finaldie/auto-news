import json

from langchain.embeddings import HuggingFaceEmbeddings
from embedding import Embedding
from db_cli import DBClient
import utils


class EmbeddingHuggingFace(Embedding):
    """
    Embedding with Sentence Transformers Embeddings (model downloaded
    from HuggingFace)
    """
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        super.__init__(model_name)

        self.api = HuggingFaceEmbeddings(model_name=self.model_name)
        print("Initialized EmbeddingHuggingFace")

    def dim(self):
        return 384

    def getname(self, start_date, prefix="news"):
        return f"{prefix}_embedding_hf_{start_date}".replace("-", "_")

    def create(self, text: str):
        """
        It creates the embedding with 1536 dimentions by default
        """

        return self.api.embed_query(text)

    def get_or_create(
        self,
        text: str,
        source="",
        page_id="",
        db_client=None,
        key_ttl=86400 * 30
    ):
        """
        Get embedding from cache (or create if not exist)
        """
        client = db_client or DBClient()

        embedding = client.get_embedding_item_id(
            "hf",
            self.model_name,
            source,
            page_id)

        if not embedding:
            embedding = self.create(text)

            # store embedding into redis (ttl = 1 month)
            client.set_embedding_item_id(
                "hf",
                self.model_name,
                source,
                page_id,
                json.dumps(embedding),
                expired_time=key_ttl)

        else:
            embedding = utils.fix_and_parse_json(embedding)

        return embedding
