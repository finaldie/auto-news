import os
import json
import time
import hashlib
import traceback
import subprocess
from datetime import datetime
from operator import itemgetter

import pytz
import requests

from db_cli import DBClient
from llm_agent import (
    LLMWebLoader,
    LLMYoutubeLoader
)

from ops_audio2text import OperatorAudioToText


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


def read_file(full_path="."):
    if not os.path.exists(full_path):
        return ""

    if not os.path.isfile(full_path):
        return ""

    output = ""

    f = open(full_path, "r")
    output = f.read()
    f.close()

    return output


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
    if not data:
        return None

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
    if not dt:
        return dt

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


def urlGet(url, timeout=3):
    if not url:
        return False, {}

    try:
        resp = requests.get(url, timeout=timeout)
        return True, resp
    except Exception as e:
        print(f"[ERROR] urlGet failed: {e}")
        return False, {}


def urlHead(url, timeout=3, allow_redirects=True):
    if not url:
        return False, {}

    try:
        resp = requests.head(url, timeout=timeout, allow_redirects=allow_redirects)
        return True, resp
    except Exception as e:
        print(f"[ERROR] urlHead failed: {e}")
        return False, {}


def urlUnshorten(url):
    if not url:
        return url

    # Fetch the metadata only (without body)
    ok, resp = urlHead(url, allow_redirects=True)
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

    res = text.split("===")

    summary = res[0].strip()
    translation = ""

    # Notes: LLM may not be reliable for separating chunks, sometimes
    # the translation content may be separated by \n\n instead of ===
    chunks = summary.split("\n\n")
    if len(chunks) > 1:
        summary = chunks[0].strip()

        for i in range(1, len(chunks)):
            translation += chunks[i].strip() + "\n"

    if not translation:
        for i in range(1, len(res)):
            translation += res[i].strip() + "\n"

    return summary, translation


def get_notion_database_pages_inbox(
    notion_agent,
    db_index_id,
    source
):
    db_pages = notion_agent.queryDatabaseIndex_Inbox(
        db_index_id, source)

    print(f"Query index db (inbox): {db_index_id}, the database pages founded: {db_pages}")
    return db_pages


def get_notion_database_pages_toread(notion_agent, db_index_id):
    db_pages = notion_agent.queryDatabaseIndex_ToRead(db_index_id)

    print(f"Query index db (toread): {db_index_id}, the database pages founded: {db_pages}")

    return db_pages


def get_notion_database_id_toread(notion_agent, db_index_id):
    """
    Get latest notion ToRead database id
    """
    db_pages = get_notion_database_pages_toread(
        notion_agent, db_index_id)

    if len(db_pages) == 0:
        print("[ERROR] no index db pages found...")
        return ""

    latest_db_page = db_pages[0]
    database_id = latest_db_page["database_id"]
    return database_id


def run_shell_command(cmd):
    try:
        output = subprocess.check_output(cmd, shell=True)
        return True, output
    except Exception as err:
        print(f"Run shell command: Error occurred: {err}")
        return False, str(err)


def hashcode_md5(data: bytes):
    """
    Notes: the update() should only be applied to the
           current hash_key, repeat/sequatial call
           means update(a + b + c + ...), which lead
           incorrect/inconsistent hash result

    Ref: https://docs.python.org/3/library/hashlib.html
    """
    hash_obj = hashlib.md5()
    hash_obj.update(data)
    return hash_obj.hexdigest()


def prun(func, **kwargs):
    try:
        return func(**kwargs)

    except Exception as e:
        print(f"[ERROR] Exception from prun: {e}")
        traceback.print_exc()


def retry(func, retries=3, **kwargs):
    retries = retries if retries > 0 else 3

    while retries > 0:
        retries -= 1

        try:
            st = time.time()
            ret = func(**kwargs)
            print(f"Function executed successfully, time used: {time.time() - st:.2f}s")
            return ret

        except Exception as e:
            print(f"[ERROR] Failed to executed function: {e}")
            traceback.print_exc()

            if retries == 0:
                raise
            else:
                print("Wait for 5s to retry ...")
                time.sleep(5)


def load_web(url):
    landing_page = urlUnshorten(url)
    print(f"[load_web] origin url: {url}, landing page: {landing_page}")

    loader = LLMWebLoader()
    docs = loader.load(landing_page)

    content = ""
    for doc in docs:
        content += doc.page_content
        content += "\n"

    content = refine_content(content)
    print(f"[load_web] finished, content (post refinement): {content[:200]}...")
    return content


def load_video_transcript(
    url,
    audio_url,
    page_id="",
    data_folder="",
    run_id="",
    audio2text=True,
    enable_cache=True
):
    loader = LLMYoutubeLoader()
    transcript_langs = os.getenv("YOUTUBE_TRANSCRIPT_LANGS", "en")
    langs = transcript_langs.split(",")
    print(f"Loading Youtube transcript, supported language list: {langs}, video_url: {url}, audio_url: {audio_url}, page_id: {page_id}, audio2text: {audio2text}, enable_cache: {enable_cache}")

    # For the below sites, skip load from them as it may lead infinite loop and never ends
    excluded_list = ["twitch.tv"]

    for excluded_site in excluded_list:
        if excluded_site in url:
            print(f"[WARN] Doesn't support load video transcript from {excluded_site}, SKIP and RETURN")
            return "", {}

    client = DBClient()
    redis_key_expire_time = os.getenv(
        "BOT_REDIS_KEY_EXPIRE_TIME", 604800)

    if enable_cache:
        transcript = client.get_notion_summary_item_id(
            "reddit_transcript", "default", page_id)

        if transcript:
            transcript = bytes2str(transcript)
            print(f"[[utils.load_video_transcript]] Found cached video transcript: {transcript[:200]}...")

            return transcript, {}

        else:
            print(f"[utils.load_video_transcript] cannot find cached transcript, will load it from original video, url: {url}, page_id: {page_id}")

    docs = []
    transcript = ""
    metadata = {}

    for lang in langs:
        print(f"Loading Youtube transcript with language {lang} ...")
        docs = loader.load(url, language=lang)

        if len(docs) > 0:
            print(f"Found transcript for language {lang}, number of docs returned: {len(docs)}")
            break

    if not docs:
        print(f"[WARN] Transcipt not found for language list: {langs}")

        if audio2text:
            st = time.time()
            print(f"Audio2Text enabled, transcribe it, page_id: {page_id}, url: {url}, audio_url: {audio_url} ...")
            op_a2t = OperatorAudioToText(model_name="base")

            audio_file = op_a2t.extract_audio(
                page_id, audio_url, data_folder, run_id)
            print(f"Extracted audio file: {audio_file}")

            audio_text = op_a2t.transcribe(audio_file)
            print(f"Transcribed audio text (total {time.time() - st:.2f}s): {audio_text}")

            transcript = audio_text.get("text") or ""

    else:
        for doc in docs:
            transcript += doc.page_content
            transcript += "\n"

            # Notes: metadata is the same for all the docs
            metadata = doc.metadata

    # cache it
    if enable_cache:
        client.set_notion_summary_item_id(
            "reddit_transcript", "default", page_id, transcript,
            expired_time=int(redis_key_expire_time))

    return transcript, metadata


def refine_content(text: str):
    """
    A simple 'refine' method to merge all sequence \n to one
    """
    if not text:
        return ""

    while "\n\n" in text:
        text = text.replace("\n\n", "\n")

    return text.strip()
