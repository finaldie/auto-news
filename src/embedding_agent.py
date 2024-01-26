import os
from embedding_openai import EmbeddingOpenAI
from embedding_hf import EmbeddingHuggingFace
from embedding_hf_inst import EmbeddingHuggingFaceInstruct


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
            self.model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

        print(f"[EmbeddingFactory] provider: {self.provider}, model_name: {self.model_name}")

        self.model = None

        if self.provider == "openai":
            self.model = EmbeddingOpenAI(model_name=self.model_name)

        elif self.provider == "all-MiniLM-L6-v2":
            self.model = EmbeddingHuggingFace(model_name=self.model_name)

        elif self.provider == "hkunlp/instructor-xl":
            self.model = EmbeddingHuggingFaceInstruct(model_name=self.model_name)
        else:
            print(f"[ERROR] Unknown embedding model: {self.model_name}")
            return None

    def dim(self):
        return self.model.dim()

    def getname(self, start_date, prefix="news"):
        return self.model.getname(start_date, prefix)

    def create(self, text: str):
        return self.model.create(text)

    def get_or_create(self, text: str, source="", page_id="", db_client=None, key_ttl=86400 * 30):
        return self.model.get_or_create(text, source, page_id, db_client, key_ttl)
