import os
import json
from datetime import datetime
from operator import itemgetter

import redis
import pytz
import requests


def str2bool(v):
    if isinstance(v, bool):
        return v

    if not isinstance(v, str):
        raise TypeError('Boolean type expected')
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise ValueError('Boolean value expected')


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


def redis_set(conn, key: str, val: str, expire_time=0, overwrite=False):
    """
    expire_time: the key will be expired after expire_time seconds
    """
    try:
        if expire_time <= 0:
            if overwrite:
                conn.set(key, val)
            else:
                conn.setnx(key, val)
        else:
            conn.setex(key, int(expire_time), val)

        return True
    except Exception as e:
        print(f"[ERROR]: Failed to set key {key} and val {val}: {e}")
        return False


def bytes2str(data):
    """
    If input data is bytes type, then convert it to str
    """
    if isinstance(data, bytes):
        data = data.decode("utf-8")

    return data


def fix_json_str(data):
    res = data.replace("\\n", "\n")
    res = data.replace("\t", "")
    return res


def fix_and_parse_json(data):
    res = None

    try:
        data = bytes2str(data)
        fixed = fix_json_str(data)
        res = json.loads(fixed)
        return res
    except Exception as e:
        print(f"[ERROR]: cannot parse json string: {data}, error: {e}")
        return res


def parseDataFromIsoFormat(dt: str):
    """
    Input date string: 2023-05-07T08:32:00+00:00, 2023-05-07T08:32:00.000Z

    Start from Python 3.11, the datetime.fromisoformat() will handle
    it correctly, before 3.11, if date string contains 'Z', need to
    replace it before handling

    Here, we simply replace Z with +00:00

    @return datetime object
    """
    return datetime.fromisoformat(dt.replace('Z', '+00:00'))


def convertUTC2PDT_str(utc_time: str):
    dt_utc = parseDataFromIsoFormat(utc_time)
    dt_pdt = dt_utc.astimezone(pytz.timezone('America/Los_Angeles'))
    return dt_pdt


def get_top_items(items: list, k=3):
    """
    items: [(name, score), ...]
    """
    tops = sorted(items, key=itemgetter(1), reverse=True)
    return tops[:k]


def urlGet(url):
    if not url:
        return False, {}

    try:
        resp = requests.get(url)
        return True, resp
    except Exception as e:
        print(f"[ERROR] urlGet failed: {e}")
        return False, {}


def urlUnshorten(url):
    if not url:
        return url

    ok, resp = urlGet(url)
    if ok:
        url = resp.url

    return url


def splitSummaryTranslation(text):
    """
    Split summary and its translation into two parts
    Format:
    ```
    summary english

    summary other language
    ```
    """
    if not text:
        return text, ""

    res = text.split("\n\n")

    summary = res[0]
    translation = res[1] if len(res) >= 2 else ""

    return summary, translation
