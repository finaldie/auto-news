from llama_index.vector_stores import ChromaVectorStore
from llama_index import StorageContext
from llama_index import VectorStoreIndex, ServiceContext
from llama_index.llms import OpenAI

from chromadb_cli import ChromaDB


class LlamaIndexEngine:
    """
    llama_index + openAI + chromadb vector store for RAG
    """
    def __init__(self, work_dir, collection, model_name):
        self.collection = collection
        self.model_name = model_name
        print(f"[LlamaIndexEngine] collection: {collection}, model_name: {model_name}")

        self.llm = OpenAI(temperature=0, model=model_name)
        self.service_context = ServiceContext.from_defaults(llm=self.llm)

        # create collection if none
        if not self.collection:
            self.vector_db_path = f"{work_dir}/data.vdb"
            self.vector_db = ChromaDB(db_path=self.vector_db_path)
            self.collection = self.vector_db.create_collection()
        
        self.vector_store = ChromaVectorStore(chroma_collection=self.collection)
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

        self.index = VectorStoreIndex.from_documents(
            [],
            service_context=self.service_context,
            storage_context=self.storage_context
        )

        # Create a Q/A engine
        self.query_engine = self.index.as_query_engine()
        print("[LlamaIndexEngine] Initialization finished")

    def qa(self, query: str):
        return self.query_engine.query(query)
