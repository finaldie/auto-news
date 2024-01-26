import openai

from embedding import Embedding
from embedding_openai_0x import EmbeddingOpenAI_0x
from embedding_openai_1x import EmbeddingOpenAI_1x


class EmbeddingOpenAI(Embedding):
    def __init__(self, model_name=""):
        super().__init__(model_name)

        self.instance = None

        if openai.__version__ < "1.0.0":
            self.instance = EmbeddingOpenAI_0x(model_name=model_name)
        else:  # >= 1.0.0
            self.instance = EmbeddingOpenAI_1x(model_name=model_name)

        print(f"Initialized EmbeddingOpenAI Interface: openai version {openai.__version__}")

    def dim(self):
        return self.instance.dim()

    def getname(self, start_date, prefix="news"):
        return self.instance.getname(
            start_date=start_date,
            prefix=prefix)

    def create(
        self,
        text: str,
        num_retries=3
    ):
        return self.instance.create(
            text=text,
            num_retries=num_retries)

    def get_or_create(
        self,
        text: str,
        source="",
        page_id="",
        db_client=None,
        key_ttl=86400 * 30
    ):
        return self.instance.get_or_create(
            text=text,
            source=source,
            page_id=page_id,
            db_client=db_client,
            key_ttl=key_ttl)
