import argparse
import os
from datetime import date, datetime, timedelta

from dotenv import load_dotenv

from ops_twitter import OperatorTwitter
from ops_article import OperatorArticle
from ops_youtube import OperatorYoutube
from ops_obsidian import OperatorObsidian


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
parser.add_argument("--sources",
                    help="sources to pull, comma separated",
                    default="Twitter,Article,Youtube")
parser.add_argument("--targets",
                    help="targets to push, comma separated",
                    default="Obsidian")
parser.add_argument("--min-rating",
                    help="Minimum user rating to distribute",
                    default=4)
parser.add_argument("--dedup", help="whether dedup item",
                    default=True)
parser.add_argument("--past-days",
                    help="How many days in the past to process",
                    default=2)


def process_twitter(args, folders):
    print("#####################################################")
    print("# Process Twitter")
    print("#####################################################")
    op = OperatorTwitter()
    data = op.load_folders(folders, "twitter.json")
    data_deduped = op.unique(data)
    print(f"data_deduped ({len(data_deduped.keys())}): {data_deduped}")

    return data_deduped


def process_article(args, folders):
    print("#####################################################")
    print("# Process Article")
    print("#####################################################")
    op = OperatorArticle()

    data = op.load_folders(folders, "article.json")
    data_deduped = op.unique(data)
    print(f"data_deduped ({len(data_deduped.keys())}): {data_deduped}")

    return data_deduped


def process_youtube(args, folders):
    print("#####################################################")
    print(f"# Process Youtube, dedup: {args.dedup}")
    print("#####################################################")
    op = OperatorYoutube()

    data = op.load_folders(folders, "youtube.json")
    data_deduped = op.unique(data)
    print(f"data_deduped ({len(data_deduped.keys())}): {data_deduped}")

    return data_deduped


def dist(args, data, target):
    if target == "Obsidian":
        op = OperatorObsidian()
        dedup = op.dedup(data)
        op.push(dedup, args.min_rating)


def run(args):
    print(f"environment: {os.environ}")
    sources = args.sources.split(",")
    targets = args.targets.split(",")
    exec_date = date.fromisoformat(args.start)
    workdir = os.getenv("WORKDIR")

    print(f"sources: {sources}, targets: {targets}, exec_date: {exec_date}, workdir: {workdir}")

    # folder names to load
    folders = []

    for i in range(args.past_days):
        dt = exec_date - timedelta(days=i)
        name = dt.isoformat()
        folders.append(f"{workdir}/{args.data_folder}/{name}")

    data_deduped = {}

    for source in sources:
        if source == "Twitter":
            data_deduped = process_twitter(args, folders)

        elif source == "Article":
            data_deduped = process_article(args, folders)

        elif source == "Youtube":
            data_deduped = process_youtube(args, folders)

        for target in targets:
            dist(args, data_deduped, target)


if __name__ == "__main__":
    args = parser.parse_args()
    load_dotenv()

    run(args)
