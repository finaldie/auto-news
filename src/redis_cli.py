import os
import redis


class RedisClient:
    def __init__(self, url=None):
        self.url = url or os.getenv("BOT_REDIS_URL")
        self.api = self._init()

    def _init(self):
        conn = None

        try:
            conn = redis.from_url(self.url)
        except Exception as e:
            print(f"[ERROR]: Connect to redis @{self.url} failed: {e}")

        return conn

    def get(self, key: str):
        data = None

        try:
            data = self.api.get(key)
        except Exception as e:
            print(f"[ERROR]: Redis client failed to get key {key}: {e}")

        return data

    def set(self, key: str, val: str, **kwargs):
        """
        expired_time: the key will be expired after expired_time seconds
        """
        expired_time = kwargs.setdefault("expired_time", 0)
        overwrite = kwargs.setdefault("overwrite", False)
        print(f"[Redis Client] Set key: {key}, val: {val}, expired_time: {expired_time}, overwrite: {overwrite}")

        try:
            if expired_time <= 0:
                if overwrite:
                    self.api.set(key, val)
                else:
                    self.api.setnx(key, val)
            else:
                self.api.setex(key, int(expired_time), val)

            return True
        except Exception as e:
            print(f"[ERROR]: Redis client failed to set key {key} and val {val}: {e}")
            return False
