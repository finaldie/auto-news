import os
import openai

from pymilvus import (
    connections,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
    utility
)


class MilvusClient:
    def __init__(
        self,
        alias="default",
        host="milvus-standalone",
        port='19530',
        dim=1536,
        embedding_model="text-embedding-ada-002"  # OpenAI
    ):
        self.alias = alias  # The server alias we connect to

        self.conn = connections.connect(
            alias=alias,
            host=host,
            port=port
        )

        self.embedding_model = embedding_model

        # <name, collection>
        self.collections = {}

    def createEmbedding(self, text: str):
        """
        It creates the embedding with 1536 dimentions by default
        """
        api_key = os.getenv("OPENAI_API_KEY")
        print(f"[createEmbedding] openai api key: {api_key}")

        emb = openai.Embedding.create(
            input=[text],
            api_key=api_key,
            model=self.embedding_model)

        return emb["data"][0]["embedding"]

    def getConnAlias(self):
        return self.alias

    def disconnect(self):
        connections.disconnect(self.alias)

    def createCollection(self, name="embedding_table", desc="embeddings"):
        # Create table schema
        self.fields = [
            FieldSchema(name="pk",
                        dtype=DataType.INT64,
                        is_primary=True,
                        auto_id=True),

            FieldSchema(name="embeddings",
                        dtype=DataType.FLOAT_VECTOR,
                        dim=1536),

            FieldSchema(name="item_id",
                        dtype=DataType.VARCHAR,
                        max_length=128),
        ]

        self.schema = CollectionSchema(
            fields=self.fields,
            description=desc
        )

        collection = Collection(
            name=name,
            schema=self.schema,
            # create collection (table) on the 'alias' server
            using=self.alias
            # shards_num=2
        )

        # Create index
        self._create_index(collection)

        # Let server load the collection data into memory before actual search
        collection.load()

        # insert into collections
        self.collections[name] = collection
        return collection

    def loadCollection(self, name):
        if self.collections.get(name):
            return self.collections[name]

        collection = Collection(name)
        collection.load()
        self.collections[name] = collection
        return collection

    def getCollection(self, name):
        """
        Get collection from local cache
        """
        collection = self.collections.get(name) or Collection(name)
        self.collections[name] = collection
        return collection

    def _create_index(self, collection):
        if collection.has_index():
            print("[INFO] The collection has index already, skip")
            return

        # create index if not exist.
        collection.release()
        collection.create_index("embeddings", {
            "metric_type": "IP",
            "index_type": "HNSW",
            "params": {"M": 8, "efConstruction": 64},
        }, index_name="embeddings")

        print("[INFO] Created index for the collection")

    def create_index(self, name):
        collection = self.getCollection(name)

        self._create_index(collection)

    def add(
        self,
        name: str,    # collection name
        item_id: str,
        text: str,
        embed: list = None,
    ):
        """ Insert embedding and data into collection (table)
        """
        emb = embed or self.createEmbedding(text)
        collection = self.getCollection(name)

        result = collection.insert([[emb], [item_id]])
        print(f"Inserted data into memory at primary key: {result.primary_keys[0]}:\n data: {text}, item_id: {item_id}")

    def get(
        self,
        name: str,  # collection name
        text: str,
        topk=1
    ):
        emb = self.createEmbedding(text)
        collection = self.getCollection(name)

        search_params = {
            "metrics_type": "IP",
            "params": {"nprobe": 8},
        }

        result = collection.search(
            [emb], "embeddings", search_params, topk,
            output_fields=["item_id"])

        return [{"item_id": item.entity.value_of_field("item_id")} for item in result[0]]

    def exist(self, name):
        return utility.has_collection(name)

    def clear(self, name):
        """ Clear the index in memory
        """
        collection = self.getCollection(name)
        collection.drop()

        collection = Collection(name, self.schema)
        self.create_index()

        collection.load()
        self.collections[name] = collection

        return "Obliviated"

    def drop(self, name):
        """
        Drop all the data for a collection
        """
        collection = self.getCollection(name)
        collection.drop()

        self.collections.pop(name, None)

    def release(self, name):
        """
        Release a Collection from memory
        """
        collection = self.getCollection(name)
        collection.release()

    def flush(self, name):
        collection = self.getCollection(name)
        collection.flush()

    def get_stats(self, name):
        """
        Returns: The stats of the Collection
        """
        collection = self.getCollection(name)

        return {
            "name": collection.name,
            "description": collection.description,
            "schema": collection.schema,
            "is_empty": collection.is_empty,
            "num_entities": collection.num_entities,
            "primary_field": collection.primary_field,
            "partitions": collection.partitions,
            "indexes": collection.indexes,
            "properties": collection.properties,
        }

    def list_collections(self) -> list:
        return utility.list_collections()
