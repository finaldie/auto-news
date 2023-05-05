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


def redis_set(conn, key: str, val: str):
    try:
        conn.set(key, val)
        return True
    except Exception as e:
        print(f"[ERROR]: Failed to get key {key} and val {val}: {e}")
        return False


def fix_json_str(data):
    res = data.replace("\\n", "\n")
    res = data.replace("\t", "")
    return res


def fix_and_parse_json(data):
    fixed = fix_json_str(data)
    res = None

    try:
        res = json.loads(fixed)
        return res
    except Exception as e:
        print(f"[ERROR]: cannot parse json string: {data}, error: {e}")
        return res
