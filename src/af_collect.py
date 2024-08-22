import argparse
import os
from datetime import datetime

from dotenv import load_dotenv

from ops_collection import OperatorCollection


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
parser.add_argument("--collection-type", help="weekly, monthly, yearly",
                    default="weekly")
parser.add_argument("--min-rating", help="Minimum rating to pull",
                    default=4)
parser.add_argument("--sources", help="sources to pull, comma separated",
                    default=os.getenv("CONTENT_SOURCES", "Twitter,Reddit,Article,Youtube,RSS"))


def pull(args, op, sources):
    print("######################################################")
    print("# Pull Collections")
    print("######################################################")
    data = op.pull(collection_type=args.collection_type, sources=sources)
    filtered_data = op.pre_filter(data, min_score=args.min_rating)
    return filtered_data


def save(args, op, data):
    """
    Save the middle result (json) to data folder
    """
    print("######################################################")
    print("# Save Collection data to json")
    print("######################################################")
    op.save2json(args.data_folder, args.run_id, "collection.json", data)


def run(args):
    sources = args.sources.split(",")
    print(f"Sources: {sources}")

    op = OperatorCollection()
    data = pull(args, op, sources)
    save(args, op, data)


if __name__ == "__main__":
    args = parser.parse_args()
    load_dotenv()

    run(args)
