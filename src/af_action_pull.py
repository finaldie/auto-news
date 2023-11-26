import argparse
import os
from datetime import datetime

from dotenv import load_dotenv

from ops_todo import OperatorTODO
from ops_deepdive import OperatorDeepDive
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


def pull_todo(args, op):
    print("######################################################")
    print("# TODO: Pulling")
    print("######################################################")
    print(f"environment: {os.environ}")

    # Pull from non-TODO sources (past N days)
    # - Takeaways
    # - Journal notes
    sources = ["Youtube", "Article", "Twitter", "RSS", "Reddit"]
    data = op.pull(sources=sources, category="todo")
    return data


def save_todo(args, op, data):
    """
    Save the middle result (json) to data folder
    """
    print("######################################################")
    print("# TODO: Save data to json")
    print("######################################################")
    op.save2json(args.data_folder, args.run_id, "action_todo.json", data)


def pull_deepdive(args, op):
    print("######################################################")
    print("# DeepDive: Pulling")
    print("######################################################")
    print(f"environment: {os.environ}")

    # Pull from non-TODO sources (past N days)
    # - Takeaways
    sources = ["Youtube", "Article", "Twitter", "RSS", "Reddit", "Journal", "TODO", "DeepDive"]
    data = op.pull(sources=sources, category="deepdive")
    return data


def save_deepdive(args, op, data):
    """
    Save the middle result (json) to data folder
    """
    print("######################################################")
    print("# DeepDive: Save data to json")
    print("######################################################")
    op.save2json(args.data_folder, args.run_id, "action_deepdive.json", data)


def run(args):
    def run_todo():
        op = OperatorTODO()
        data = pull_todo(args, op)
        save_todo(args, op, data)

    def run_deepdive():
        op = OperatorDeepDive()
        data = pull_deepdive(args, op)
        save_deepdive(args, op, data)

    utils.prun(run_todo)
    utils.prun(run_deepdive)


if __name__ == "__main__":
    args = parser.parse_args()
    load_dotenv()

    run(args)
