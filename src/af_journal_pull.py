import argparse
import os
from datetime import datetime

from dotenv import load_dotenv

from ops_journal import OperatorJournal


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
                    default="Journal")


def pull(args, op, sources):
    print("######################################################")
    print("# Pull Journal")
    print("######################################################")
    data = op.pull(sources=sources)
    return data


def save(args, op, data):
    """
    Save the middle result (json) to data folder
    """
    print("######################################################")
    print("# Save Journal data to json")
    print("######################################################")
    op.save2json(args.data_folder, args.run_id, "journal.json", data)


def run(args):
    sources = args.sources.split(",")
    print(f"Sources: {sources}")

    op = OperatorJournal()
    data = pull(args, op, sources)
    save(args, op, data)


if __name__ == "__main__":
    args = parser.parse_args()
    load_dotenv()

    run(args)
