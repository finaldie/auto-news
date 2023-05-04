import random
import argparse
import sys
import os

import time
import math
from collections import defaultdict
from datetime import date, timedelta, datetime

import requests
import json

from dotenv import load_dotenv
from tweets import TwitterAgent
import utils
import data_model
from notion import NotionAgent


parser = argparse.ArgumentParser()
parser.add_argument("--prefix", help="runtime prefix path",
                    default="./run")
parser.add_argument("--start", help="start time",
                    default=datetime.now().isoformat())
parser.add_argument("--run-id", help="run-id",
                    default="")
parser.add_argument("--job-id", help="job-id",
                    default="")
parser.add_argument("--data-folder", help="data folder to save",
                    default="./data")
parser.add_argument("--sources", help="sources to pull, comma separated",
                    default="twitter")
parser.add_argument("--targets", help="targets to push, comma separated",
                    default="notion")


def retrieve_twitter(args):
    """
    get data from local data folder
    """
    workdir = os.getenv("WORKDIR")

    filename = "twitter.json"
    data_path = f"{workdir}/{args.data_folder}/{args.run_id}"
    full_path = utils.gen_filename(data_path, filename)

    data = utils.read_data_json(full_path)

    print(f"retrieve twitter data from {full_path}, data: {data}")
    return data


def tweets_dedup(args, tweets):
    print("#####################################################")
    print("# Tweets Dedup                                      #")
    print("#####################################################")

    redis_url = os.getenv("BOT_REDIS_URL")
    redis_conn = utils.redis_conn(redis_url)

    tweets_deduped = {}

    for list_name, data in tweets.items():
        tweets_list = tweets_deduped.setdefault(list_name, [])

        for tweet in data:
            tweet_id = tweet["tweet_id"]

            key = data_model.NOTION_INBOX_ITEM_ID.format("twitter", list_name, tweet_id)

            if utils.redis_get(redis_conn, key):
                print("Duplicated tweet found, key: {key}")
            else:
                # mark as visited
                utils.redis_set(redis_conn, key, "true")

                tweets_list.append(tweet)

    print(f"tweets_deduped: {tweets_deduped}")
    return tweets_deduped


def push_to_inbox(args, data):
    """
    data: {list_name1: [tweet1, tweet2, ...], list_name2: [...], ...}
    """
    print("#####################################################")
    print("# Push Tweets to Inbox                              #")
    print("#####################################################")

    targets = args.targets.split(",")

    for target in targets:
        print(f"Pushing data to target: {target} ...")

        if target == "notion":
            notion_api_key = os.getenv("NOTION_TOKEN")
            notion_agent = NotionAgent(notion_api_key)

            database_id = os.getenv("NOTION_DATABASE_ID_TWITTER_INBOX")

            for list_name, tweets in data.items():
                for tweet in tweets:
                    notion_agent.createDatabaseItem_TwitterInbox(
                        database_id, [list_name], tweet)

                    print(f"Insert one tweet into inbox")

        else:
            print("[ERROR]: Unknown target {target}, skip")


def tweets_category_and_rank(args, tweets):
    return True


def push_to_read(args, data):
    return True


def run(args):
    print(f"environment: {os.environ}")
    sources = args.sources.split(",")

    for source in sources:
        print(f"Pushing data for source: {source} ...")

        # Notes: For twitter we don't need summary step
        if source == "twitter":
            data = retrieve_twitter(args)
            data_deduped = tweets_dedup(args, data)
            push_to_inbox(args, data_deduped)

            data_ranked = tweets_category_and_rank(args, data_deduped)
            push_to_read(args, data_ranked)


if __name__ == "__main__":
    args = parser.parse_args()
    load_dotenv()

    run(args)
