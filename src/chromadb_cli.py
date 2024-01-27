import os
import chromadb

from langchain.text_splitter import (
    RecursiveCharacterTextSplitter
)

from chromadb.utils import embedding_functions

import utils


class ChromaDB:
    """
    A chromadb instance manages one collection
    """
    def __init__(
        self,
        db_path: str = "./test.vdb",
        collection_name: str = "default",
        emb_fn=None
    ):
        self.client = chromadb.PersistentClient(path=db_path)
        self.emb_fn = emb_fn
        self.collection_name = collection_name
        self.collection = None

        if not self.emb_fn:
            openai_api_key = os.getenv("OPENAI_API_KEY", "")
            model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")

            self.emb_fn = embedding_functions.OpenAIEmbeddingFunction(
                api_key=openai_api_key,
                model_name=model_name,
            )

        print(f"ChromaDB initialization done, db_path: {db_path}, collection_name: {collection_name}, emb_fn: {emb_fn}")

    def create_collection(self):
        if not self.emb_fn:
            self.collection = self.client.get_or_create_collection(name=self.collection_name)
        else:
            self.collection = self.client.get_or_create_collection(name=self.collection_name, embedding_function=self.emb_fn)

        return self.collection

    def get_collection(self):
        return self.collection

    def delete_collection(self):
        if not self.collection:
            return

        self.client.delete_collection(name=self.collection_name)
        self.collection = None

    def add(
        self,
        text: str,
        metadata: dict,  # uuid, url, title, etc
        chunk_size: int = 1024,
        chunk_overlap: int = 128,
    ):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        docs = text_splitter.create_documents([text])
        # print(f"docs: {docs}")
        # for doc in docs:
        #    print(f"doc: {doc.page_content}")

        docs_arr = [doc.page_content for doc in docs]
        ids = [utils.hashcode_md5(doc.page_content.encode('utf-8')) for doc in docs]
        metadatas = [metadata for doc in docs]

        self.collection.add(
            documents=docs_arr,
            metadatas=metadatas,
            ids=ids,
        )

    def query(
        self,
        text: str,
        n_results=3,
        **kwargs
    ):
        return self.collection.query(
            query_texts=[text],
            n_results=n_results
        )

    def query_result(
        self,
        text: str,
        n_results=3,
        max_distance=0.5,
        **kwargs
    ):
        res = self.collection.query(
            query_texts=[text],
            n_results=n_results
        )

        # print(f"[chromadb.query_result] res: {res}")

        if len(res["ids"]) == 0:
            return []

        ret = []

        for id, distance, metadata, doc in zip(res["ids"][0], res["distances"][0], res["metadatas"][0], res["documents"][0]):
            # print(f"id: {id}, distance: {distance}, meta: {metadata}, doc: {doc}")

            if distance <= max_distance:
                ret.append({"id": id, "distance": distance, "metadata": metadata, "doc": doc})
            else:
                print(f"[vdb.query_result] skip due to distance is low: {distance}")

        return ret

    def peek(self):
        return self.collection.peek()

    def count(self):
        return self.collection.count()

    def reset(self):
        self.client.reset()
        return self

    def heartbeat(self):
        return self.client.heartbeat()
