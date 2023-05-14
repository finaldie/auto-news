import argparse
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
import utils

from ops_twitter import OperatorTwitter
from ops_article import OperatorArticle
from ops_youtube import OperatorYoutube


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


def process_article(args, folders):
    print("#####################################################")
    print("# Process Article")
    print("#####################################################")
    op = OperatorArticle()

    data = op.load_folders(folders, "article.json")
    data_deduped = op.unique(data)
    print(f"data_deduped ({len(data_deduped.keys())}): {data_deduped}")


def process_youtube(args, folders):
    print("#####################################################")
    print(f"# Process Youtube, dedup: {args.dedup}")
    print("#####################################################")
    op = OperatorYoutube()

    data = op.load_folders(folders, "youtube.json")
    data_deduped = op.unique(data)
    print(f"data_deduped ({len(data_deduped.keys())}): {data_deduped}")


def run(args):
    print(f"environment: {os.environ}")
    sources = args.sources.split(",")
    exec_date = datetime.fromisoformat(args.start)

    # folder names to load
    folders = []

    for i in range(args.past_days):
        dt = exec_date - timedelta(days=i)
        name = dt.isoformat()
        folders.append(f"{args.data_path}/{name}")

    for source in sources:
        print(f"Pushing data for source: {source} ...")

        if source == "Twitter":
            process_twitter(args, folders)

        elif source == "Article":
            process_article(args, folders)

        elif source == "Youtube":
            process_youtube(args, folders)


if __name__ == "__main__":
    args = parser.parse_args()
    load_dotenv()

    run(args)
