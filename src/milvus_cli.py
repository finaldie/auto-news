import os

from pymilvus import (
    connections,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
    utility,
    exceptions
)


class MilvusClient:
    def __init__(
        self,
        alias="default",
        host="",
        port="",
        emb_agent=None,
    ):
        self.alias = alias  # The server alias we connect to
        self.host = host or os.getenv("MILVUS_HOST", "milvus-standalone")

        # In k8s, the port format tcp://IP:19530, extract it again
        self.port = port or os.getenv("MILVUS_PORT", "19530").split(":")[-1]

        print(f"[MilvusClient] server.alias: {self.alias}, host: {self.host}, port: {self.port}")

        self.conn = connections.connect(
            alias=self.alias,
            host=self.host,
            port=self.port
        )

        self.emb_agent = emb_agent

        # <name, collection>
        self.collections = {}

    def getConnAlias(self):
        return self.alias

    def disconnect(self):
        connections.disconnect(self.alias)

    def createCollection(
        self,
        name="embedding_table",
        desc="embeddings",
        dim=1536,
        distance_metric="",
    ):
        distance_metric = distance_metric or os.getenv("MILVUS_SIMILARITY_METRICS", "L2")

        # Create table schema
        self.fields = [
            FieldSchema(name="pk",
                        dtype=DataType.INT64,
                        is_primary=True,
                        auto_id=True),

            FieldSchema(name="embeddings",
                        dtype=DataType.FLOAT_VECTOR,
                        dim=dim),

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
        self._create_index(collection, distance_metric)

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

    def _create_index(self, collection, distance_metric):
        if collection.has_index():
            print("[INFO] The collection has index already, skip")
            return

        # create index if not exist.
        collection.release()
        collection.create_index("embeddings", {
            "metric_type": distance_metric,
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
        emb = embed or self.emb_agent.create(text)
        collection = self.getCollection(name)

        result = collection.insert([[emb], [item_id]])
        print(f"[Milvus Client] Inserted data into memory at primary key: {result.primary_keys[0]}:\n data: {text}, item_id: {item_id}")

    def get(
        self,
        name: str,  # collection name
        text: str,
        topk=1,
        fallback=None,
        emb=None,
        distance_metric="",
        timeout=60,  # timeout (unit second)
    ):
        distance_metric = distance_metric or os.getenv("MILVUS_SIMILARITY_METRICS", "L2")
        collection = None

        try:
            collection = self.getCollection(name)

        except exceptions.SchemaNotReadyException as e:
            print(f"[ERROR] Schema {name} is not ready yet: {e}")

            if fallback:
                print(f"Using fallback collection: {fallback}")
                return self.get(fallback, text, topk=topk, emb=emb)
            else:
                return []

        except Exception as e:
            print(f"[ERROR] Failed to get collection: {e}")
            return []

        search_params = {
            "metric_type": distance_metric,
            "params": {"nprobe": 8},
        }

        emb = emb or self.emb_agent.create(text)

        result = collection.search(
            [emb],
            "embeddings",
            search_params,
            topk,
            output_fields=["item_id"],
            timeout=timeout,
        )

        print(f"[Milvus Client] get relevant results: {result}")

        return [{
            "item_id": hit.entity.get("item_id"),
            "distance": hit.distance
        } for hit in result[0]]

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
        # print(f"collection: {collection}")

        return {
            "name": collection.name,
            "description": collection.description,
            "schema": collection.schema,
            "is_empty": collection.is_empty,
            "num_entities": collection.num_entities,
            "primary_field": collection.primary_field,
            "partitions": collection.partitions,
            "indexes": collection.indexes,
            # "properties": collection.properties,
        }

    def list_collections(self) -> list:
        return utility.list_collections()
