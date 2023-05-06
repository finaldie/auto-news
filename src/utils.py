import os
import json

import redis


def gen_filename(data_folder, filename):
    return f"{data_folder}/{filename}"


def save_data_json(full_path, data):
    with open(full_path, "w") as out_file:
        json.dump(data, out_file)


def read_data_json(full_path):
    if not os.path.exists(full_path):
        return {}

    f = open(full_path, "r")
    data = json.load(f)
    f.close()

    return data


def redis_conn(url):
    conn = None

    try:
        conn = redis.from_url(url)
    except Exception as e:
        print(f"[ERROR]: Connect to redis @{url} failed: {e}")

    return conn


def redis_get(conn, key: str):
    data = None

    try:
        data = conn.get(key)
    except Exception as e:
        print(f"[ERROR]: Failed to get key {key}: {e}")

    return data


def redis_set(conn, key: str, val: str, expire_time=0):
    """
    expire_time: the key will be expired after expire_time seconds
    """
    try:
        if expire_time <= 0:
            conn.setnx(key, val)
        else:
            conn.setex(key, int(expire_time), val)

        return True
    except Exception as e:
        print(f"[ERROR]: Failed to set key {key} and val {val}: {e}")
        return False


def fix_json_str(data):
    res = data.replace("\\n", "\n")
    res = data.replace("\t", "")
    return res


def fix_and_parse_json(data):
    res = None

    try:
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        fixed = fix_json_str(data)
        res = json.loads(fixed)
        return res
    except Exception as e:
        print(f"[ERROR]: cannot parse json string: {data}, error: {e}")
        return res
