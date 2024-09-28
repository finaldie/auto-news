import os
import json
import time

import numpy as np

from embedding import Embedding
from langchain_community.embeddings import OllamaEmbeddings
import utils


class EmbeddingOllama(Embedding):
    """
    Embedding via Ollama
    """
    def __init__(self, model_name="nomic-embed-text", base_url=""):
        super().__init__(model_name)

        self.base_url = base_url or os.getenv("OLLAMA_URL")
        self.dimensions = -1

        self.client = OllamaEmbeddings(
            base_url=self.base_url,
            model=self.model_name,
        )

        print(f"Initialized EmbeddingOllama: model_name: {self.model_name}, base_url: {self.base_url}")

    def dim(self):
        if self.dimensions > 0:
            return self.dimensions

        text = "This is a test query"
        query_result = self.client.embed_query(text)
        self.dimensions = len(query_result)
        return self.dimensions

    def create(
        self,
        text: str,
        num_retries=3,
        retry_wait_time=0.5,
        error_wait_time=0.5,

        # ollama embedding query result is not normalized, for most
        # of the vector database would suggest us do the normalization
        # first before inserting into the vector database
        # here, we can apply a post-step for the normalization
        normalize=True,
    ):
        emb = None

        for i in range(1, num_retries + 1):
            try:
                emb = self.client.embed_query(text)

                if normalize:
                    emb = (np.array(emb) / np.linalg.norm(emb)).tolist()

                break

            except Exception as e:
                print(f"[ERROR] APIError during embedding ({i}/{num_retries}): {e}")

                if i == num_retries:
                    raise

                time.sleep(error_wait_time)

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
        client = db_client
        embedding = None

        if client:
            # Tips: the quickest way to get rid of all previous
            # cache, change the provider (1st arg)
            embedding = client.get_milvus_embedding_item_id(
                "ollama-norm",
                self.model_name,
                source,
                page_id)

        if embedding:
            print("[EmbeddingOllama] Embedding got from cache")
            return utils.fix_and_parse_json(embedding)

        # Not found in cache, generate one
        print("[EmbeddingOllama] Embedding not found, create a new one and cache it")

        # Most of the emb models have 8k tokens, exceed it will
        # throw exceptions. Here we simply limited it <= 5000 chars
        # for the input

        EMBEDDING_MAX_LENGTH = int(os.getenv("EMBEDDING_MAX_LENGTH", 5000))
        embedding = self.create(text[:EMBEDDING_MAX_LENGTH])

        # store embedding into redis (ttl = 1 month)
        if client:
            client.set_milvus_embedding_item_id(
                "ollama-norm",
                self.model_name,
                source,
                page_id,
                json.dumps(embedding),
                expired_time=key_ttl)

        return embedding
