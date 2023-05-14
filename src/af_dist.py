import argparse
import os
from datetime import datetime

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
parser.add_argument("--sources", help="sources to pull, comma separated",
                    default="Twitter,Article,Youtube")
parser.add_argument("--targets", help="targets to push, comma separated",
                    default="Obsidian")
parser.add_argument("--min-rating", help="Minimum user rating to distribute",
                    default=4)
parser.add_argument("--dedup", help="whether dedup item",
                    default=True)


def process_twitter(args):
    print("#####################################################")
    print("# Process Twitter")
    print("#####################################################")
    op = OperatorTwitter()
    data = op.readFromJson(args.data_folder, args.run_id, "twitter.json")
    data_deduped = op.dedup(data, target="syncing")
    print(f"data_deduped ({len(data_deduped.keys())}): {data_deduped}")


def process_article(args):
    print("#####################################################")
    print("# Process Article")
    print("#####################################################")
    op = OperatorArticle()

    data = op.readFromJson(args.data_folder, args.run_id, "article.json")
    data_deduped = op.dedup(data, target="syncing")
    print(f"data_deduped ({len(data_deduped.keys())}): {data_deduped}")


def process_youtube(args):
    print("#####################################################")
    print(f"# Process Youtube, dedup: {args.dedup}")
    print("#####################################################")
    op = OperatorYoutube()

    data = op.readFromJson(args.data_folder, args.run_id, "youtube.json")
    data_deduped = op.dedup(data, target="syncing")
    print(f"data_deduped ({len(data_deduped.keys())}): {data_deduped}")


def run(args):
    print(f"environment: {os.environ}")
    sources = args.sources.split(",")

    for source in sources:
        print(f"Pushing data for source: {source} ...")

        if source == "Twitter":
            process_twitter(args)

        elif source == "Article":
            process_article(args)

        elif source == "Youtube":
            process_youtube(args)


if __name__ == "__main__":
    args = parser.parse_args()
    load_dotenv()

    run(args)
