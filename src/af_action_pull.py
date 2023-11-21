import argparse
import os
from datetime import datetime

from dotenv import load_dotenv

from ops_todo import OperatorTODO


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


def pull(args, op):
    print("######################################################")
    print("# TODO: Pulling")
    print("######################################################")
    print(f"environment: {os.environ}")

    # Pull from non-TODO sources (past N days)
    # - Takeaways
    # - Journal notes
    data = op.pull()
    return data


def save(args, op, data):
    """
    Save the middle result (json) to data folder
    """
    print("######################################################")
    print("# TODO: Save data to json")
    print("######################################################")
    op.save2json(args.data_folder, args.run_id, "action.json", data)


def run(args):
    op = OperatorTODO()
    data = pull(args, op)
    save(args, op, data)


if __name__ == "__main__":
    args = parser.parse_args()
    load_dotenv()

    run(args)
