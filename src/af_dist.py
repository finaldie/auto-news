import argparse
import os
from datetime import date, datetime, timedelta

from dotenv import load_dotenv

from ops_twitter import OperatorTwitter
from ops_article import OperatorArticle
from ops_youtube import OperatorYoutube
from ops_obsidian import OperatorObsidian
from ops_milvus import OperatorMilvus
from ops_reddit import OperatorReddit
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
                    default="data")
parser.add_argument("--sources",
                    help="sources to pull, comma separated",
                    default=os.getenv("CONTENT_SOURCES", "Twitter,Reddit,Article,Youtube,RSS"))
parser.add_argument("--targets",
                    help="targets to push, comma separated",
                    default="Milvus")
parser.add_argument("--min-rating",
                    help="Minimum user rating to distribute",
                    default=4)
parser.add_argument("--dedup", help="whether dedup item",
                    default=True)
parser.add_argument("--past-days",
                    help="How many days in the past to process",
                    default=30)


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


def process_rss(args, folders):
    print("#####################################################")
    print(f"# Process RSS, dedup: {args.dedup}")
    print("#####################################################")
    op = OperatorYoutube()

    data = op.load_folders(folders, "rss.json")
    data_deduped = op.unique(data)
    print(f"data_deduped ({len(data_deduped.keys())}): {data_deduped}")

    return data_deduped


def process_reddit(args, folders):
    print("#####################################################")
    print(f"# Process Reddit, dedup: {args.dedup}")
    print("#####################################################")
    op = OperatorReddit()

    data = op.load_folders(folders, "reddit.json")
    data_deduped = op.unique(data)
    print(f"data_deduped ({len(data_deduped.keys())}): {data_deduped}")

    return data_deduped


def dist(args, data, source, target):
    """
    data: The past few days unique data
    """
    print("#####################################################")
    print(f"# Data distribution, dedup: {args.dedup}, source: {source}, target: {target}, start_date: {args.start}")
    print("#####################################################")
    dedup = utils.str2bool(args.dedup)

    if target == "Obsidian":
        # TODO: The distribution part is only for weekly or monthly
        #       job, to minimize the number of items
        # op = OperatorObsidian()

        # data_deduped = []
        # if dedup:
        #     data_deduped = op.dedup(data)
        # else:
        #     data_deduped = [page for page_id, page in data.items()]

        # filtered = op.filters(data_deduped, min_rating=args.min_rating)
        # op.push(filtered)
        pass

    elif target == "Milvus":
        op = OperatorMilvus()

        data_deduped = []
        data_updated = []

        if dedup:
            data_deduped, data_updated = op.dedup(data, start_date=args.start, source=source)
        else:
            data_deduped = [page for page_id, page in data.items()]

        # update page metadata cache, e.g. user_rating
        op.update(source, data_updated)

        # push to vector database
        op.push(data_deduped, start_date=args.start, source=source)


def run(args):
    sources = args.sources.split(",")
    targets = args.targets.split(",")
    exec_date = date.fromisoformat(args.start)
    workdir = os.getenv("WORKDIR")
    dedup = utils.str2bool(args.dedup)

    print(f"sources: {sources}, targets: {targets}, exec_date: {exec_date}, workdir: {workdir}, dedup: {dedup}")

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

        elif source == "RSS":
            data_deduped = process_rss(args, folders)

        elif source == "Reddit":
            data_deduped = process_reddit(args, folders)

        for target in targets:
            dist(args, data_deduped, source, target)


if __name__ == "__main__":
    args = parser.parse_args()
    load_dotenv()

    run(args)
