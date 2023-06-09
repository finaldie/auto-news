import argparse
from datetime import date, datetime, timedelta

from dotenv import load_dotenv

from ops_milvus import OperatorMilvus


parser = argparse.ArgumentParser()
parser.add_argument("--prefix", help="runtime prefix path",
                    default="./run")
parser.add_argument("--start", help="start time",
                    default=datetime.now().isoformat())
parser.add_argument("--run-id", help="run-id",
                    default="")
parser.add_argument("--job-id", help="job-id",
                    default="")
parser.add_argument("--milvus-retention-days", help="Milvus data retention days",
                    type=int,
                    default=3)


def milvus_cleanup(args):
    print("##########################################################")
    print("Milvus cleanup")
    print("##########################################################")
    start_date = date.fromisoformat(args.start)
    cleanup_date = start_date - timedelta(days=args.milvus_retention_days)

    print(f"start date: {start_date}, retention days: {args.milvus_retention_days}, cleanup_date: {cleanup_date}")

    op = OperatorMilvus()
    op.clear(cleanup_date)


def run(args):
    milvus_cleanup(args)


if __name__ == "__main__":
    args = parser.parse_args()
    load_dotenv()

    run(args)
