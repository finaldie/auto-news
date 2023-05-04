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
parser.add_argument("--targets", help="targets to push, comma separated",
                    default="notion")


def retrieve_twitter(args):
    """
    get data from local data folder
    """
    filename = "twitter.json"
    data_path = f"{args.data_folder}/{args.run_id}"
    full_path = utils.gen_filename(data_path, filename)

    data = utils.read_data_json(full_path)

    print("retrieve twitter data: {data}")



def push_to_targets(args, data):
    targets = args.targets.split(",")

    for target in targets:
        print(f"Pushing data to target: {target} ...")

        if target == "notion":
            continue


def run(args):
    sources = args.sources.split(",")

    for source in sources:
        print(f"Pushing data for source: {source} ...")

        if source == "twitter":
            data = retrieve_twitter(args)
            push_to_targets(args, data) 

    
if __name__ == "__main__":
    args = parser.parse_args()

    run(args)
