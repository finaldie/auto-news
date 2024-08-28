import os
from embedding_openai import EmbeddingOpenAI
from embedding_hf import EmbeddingHuggingFace
from embedding_hf_inst import EmbeddingHuggingFaceInstruct
from embedding_ollama import EmbeddingOllama


class EmbeddingAgent:
    def __init__(
        self,
        provider="",
        model_name="",
    ):
        self.provider = provider
        if not self.provider:
            self.provider = os.getenv("EMBEDDING_PROVIDER", "openai")

        self.model_name = model_name
        if not self.model_name:
            self.model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")

        print(f"[EmbeddingAgent] provider: {self.provider}, model_name: {self.model_name}")

        self.model = None

        if self.provider == "openai":
            self.model = EmbeddingOpenAI(model_name=self.model_name)

        elif self.provider == "hf":
            self.model = EmbeddingHuggingFace(model_name=self.model_name)

        elif self.provider == "hf_inst":
            self.model = EmbeddingHuggingFaceInstruct(model_name=self.model_name)

        elif self.provider == "ollama":
            self.model = EmbeddingOllama(model_name=self.model_name)

        else:
            print(f"[ERROR] Unknown embedding provider: {self.provider}")
            return None

    def dim(self):
        return self.model.dim()

    def getname(self, start_date, prefix="news"):
        return self.model.getname(start_date, prefix)

    def create(self, text: str):
        return self.model.create(text)

    def get_or_create(self, text: str, source="", page_id="", db_client=None, key_ttl=86400 * 30):
        return self.model.get_or_create(text, source, page_id, db_client, key_ttl)
