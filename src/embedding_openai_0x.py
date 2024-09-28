import os
import json
import time

import httpx
import openai

from embedding import Embedding
from db_cli import DBClient
import utils


class EmbeddingOpenAI_0x(Embedding):
    """
    For The implementation for openai < 1.*
    """
    def __init__(self, model_name="text-embedding-ada-002"):
        super().__init__(model_name)
        print(f"Initialized EmbeddingOpenAI 0x: {openai.__version__}, model_name: {model_name}")

    def dim(self):
        return 1536

    def create(
        self,
        text: str,
        num_retries=3
    ):
        """
        It creates the embedding with 1536 dimentions by default
        """
        api_key = os.getenv("OPENAI_API_KEY")
        emb = None

        for i in range(1, num_retries + 1):
            try:
                if os.getenv("OPENAI_PROXY") is not None:
                    client = httpx.Client(proxies={"http://": os.getenv("OPENAI_PROXY"),
                                                   "https://": os.getenv("OPENAI_PROXY")})

                    emb = openai.Embedding.create(
                        http_client=client,
                        input=[text],
                        api_key=api_key,
                        model=self.model_name)
                else:
                    emb = openai.Embedding.create(
                        input=[text],
                        api_key=api_key,
                        model=self.model_name)

            except openai.error.RateLimitError as e:
                print(f"[ERROR] RateLimit error during embedding ({i}/{num_retries}): {e}")

                if i == num_retries:
                    raise
                else:
                    time.sleep(1)

            except openai.error.APIError as e:
                print(f"[ERROR] Failed during embedding ({i}/{num_retries}): {e}")

                if i == num_retries:
                    raise
                else:
                    time.sleep(1)

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
            "openai",
            self.model_name,
            source,
            page_id)

        if not embedding:
            # OpenAI embedding model accept 8k tokens, exceed it will
            # throw exceptions. Here we simply limited it <= 5000 chars
            # for the input

            EMBEDDING_MAX_LENGTH = int(os.getenv("EMBEDDING_MAX_LENGTH", 5000))
            embedding = self.create(text[:EMBEDDING_MAX_LENGTH])

            # store embedding into redis (ttl = 1 month)
            client.set_milvus_embedding_item_id(
                "openai",
                self.model_name,
                source,
                page_id,
                json.dumps(embedding),
                expired_time=key_ttl)

        else:
            embedding = utils.fix_and_parse_json(embedding)

        return embedding
