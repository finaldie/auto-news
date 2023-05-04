import random
import argparse

import time
import math
from collections import defaultdict
from datetime import date, timedelta

import json


parser = argparse.ArgumentParser()
parser.add_argument("--prefix", help="runtime prefix path",
                    default="./run")
parser.add_argument("--start", help="specific the start date",
                    default=date.today().isoformat())


def run(dt, prefix):
    start = date.fromisoformat(dt)
    end = start + timedelta(days=1)

    print("Start: {}, end: {}".format(start, end))


if __name__ == "__main__":
    args = parser.parse_args()

    run(args.start, args.prefix)
