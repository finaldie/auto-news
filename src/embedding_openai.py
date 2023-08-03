import os
import json
import openai

from embedding import Embedding
from db_cli import DBClient
import utils


class EmbeddingOpenAI(Embedding):
    def __init__(self, model_name="openai"):
        super().__init__(model_name)
        print("Initialized EmbeddingOpenAI")

    def dim(self):
        return 1536

    def getname(self, start_date, prefix="news"):
        return f"{prefix}_embedding__{start_date}".replace("-", "_")

    def create(
        self,
        text: str,
        model_name="text-embedding-ada-002",
        num_retries=3
    ):
        """
        It creates the embedding with 1536 dimentions by default
        """
        api_key = os.getenv("OPENAI_API_KEY")
        emb = None

        for i in range(1, num_retries + 1):
            try:
                emb = openai.Embedding.create(
                    input=[text],
                    api_key=api_key,
                    model=model_name)

            except openai.error.RateLimitError as e:
                print(f"[ERROR] RateLimit error during embedding ({i}/{num_retries}): {e}")

                if i == num_retries:
                    raise

            except openai.error.APIError as e:
                print(f"[ERROR] Failed during embedding ({i}/{num_retries}): {e}")

                if i == num_retries:
                    raise

        return emb["data"][0]["embedding"]

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
            source, page_id)

        if not embedding:
            # OpenAI embedding model accept 8k tokens, exceed it will
            # throw exceptions. Here we simply limited it <= 5000 chars
            # for the input

            EMBEDDING_MAX_LENGTH = int(os.getenv("EMBEDDING_MAX_LENGTH", 5000))
            embedding = self.create(text[:EMBEDDING_MAX_LENGTH])

            # store embedding into redis (ttl = 1 month)
            client.set_milvus_embedding_item_id(
                source, page_id, json.dumps(embedding),
                expired_time=key_ttl)

        else:
            embedding = utils.fix_and_parse_json(embedding)

        return embedding
