import json

from langchain.embeddings import HuggingFaceInstructEmbeddings
from embedding import Embedding
from db_cli import DBClient
import utils
import embedding_utils as emb_utils


class EmbeddingHuggingFaceInstruct(Embedding):
    """
    Embedding with Instruct Embeddings (model downloaded
    from HuggingFace)
    """
    def __init__(self, model_name="hkunlp/instructor-xl"):
        super().__init__(model_name)

        self.api = HuggingFaceInstructEmbeddings(model_name=self.model_name)
        print("Initialized EmbeddingHuggingFaceInstruct")

    def dim(self):
        return 384

    def create(self, text: str, normalize=True):
        """
        Query local HF embedding model
        """

        emb = self.api.embed_query(text)

        if normalize:
            emb = emb_utils.l2_norm(emb)

        return emb

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

        embedding = client.get_milvus_embedding_item_id(
            "hf_inst",
            self.model_name,
            source,
            page_id)

        if not embedding:
            embedding = self.create(text)

            # store embedding into redis (ttl = 1 month)
            client.set_milvus_embedding_item_id(
                "hf_inst",
                self.model_name,
                source,
                page_id,
                json.dumps(embedding),
                expired_time=key_ttl)

        else:
            embedding = utils.fix_and_parse_json(embedding)

        return embedding
