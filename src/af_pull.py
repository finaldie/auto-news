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


def pull_twitter(args):
    print(f"environment: {os.environ}")

    screen_names_famous = os.getenv("TWITTER_LIST_FAMOUS", "")
    screen_names_ai = os.getenv("TWITTER_LIST_AI", "")

    print(f"screen name famous: {screen_names_famous}")
    print(f"screen name ai: {screen_names_ai}")

    api_key = os.getenv("TWITTER_API_KEY")
    api_key_secret = os.getenv("TWITTER_API_KEY_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

    agent = TwitterAgent(api_key, api_key_secret, access_token, access_token_secret)

    agent.subscribe("Famous", screen_names_famous.split(","))
    agent.subscribe("AI", screen_names_ai.split(","))

    data = agent.pull()
    print(f"Pulled from twitter: {data}")

    return data


def save_twitter(args, data):
    """
    Save the middle result (json) to data folder
    """
    filename = "twitter.json"
    real_path = os.path.realpath(args.data_folder)
    data_path = f"{real_path}/{args.run_id}"

    full_path = utils.gen_filename(data_path, filename)

    print(f"Save data to {full_path}, data: {data}")
    utils.save_data_json(full_path, data)


def run(args):
    sources = args.sources.split(",")

    for source in sources:
        print(f"Pulling from source: {source} ...")

        if source == "twitter":
            data = pull_twitter(args)
            save_twitter(args, data)

    
if __name__ == "__main__":
    args = parser.parse_args()
    load_dotenv()

    run(args)
