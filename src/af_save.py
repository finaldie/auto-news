import argparse
import os
from datetime import datetime

from dotenv import load_dotenv
import utils

from ops_twitter import OperatorTwitter
from ops_article import OperatorArticle
from ops_youtube import OperatorYoutube
from ops_rss import OperatorRSS
from ops_reddit import OperatorReddit


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
                    default=os.getenv("CONTENT_SOURCES", "Twitter,Reddit,Article,Youtube,RSS"))
parser.add_argument("--targets", help="targets to push, comma separated",
                    default="notion")
parser.add_argument("--topics-top-k", help="pick top-k topics to push",
                    default=3)
parser.add_argument("--categories-top-k", help="pick top-k categories to push",
                    default=3)
parser.add_argument("--dedup", help="whether dedup item",
                    default=True)
parser.add_argument("--min-score-to-rank",
                    help="The minimum relevant score to start ranking",
                    default=4)
parser.add_argument("--max-distance",
                    help="Max distance for similarity search, range [0.0, 1.0]",
                    default=0.5)


def process_twitter(args):
    """
    Twitter has tons of tweets to process, apply embedding-based algo
    to calcuate the candidates and merge/select into final data_ranked

    The score source is based on user_rating field: [1, 5], ideally
    >= 4 will be a good

    cold start: user still filing GPT ranked score
    warm/hot start: user can filter the new relevant score, e.g.
                    filter score >= 4
    """
    print("#####################################################")
    print("# Process Twitter")
    print("#####################################################")
    op = OperatorTwitter()
    data = op.readFromJson(args.data_folder, args.run_id, "twitter.json")
    data_deduped = op.dedup(data, target="toread")

    # To save LLM tokens, do score on all deduped tweets, then
    # do rank for score >= 4 tweets
    data_scored = op.score(
        data_deduped,
        start_date=args.start,
        max_distance=args.max_distance)

    data_filtered = op.filter(data_scored, min_score=4)

    data_ranked = op.rank(
        data_filtered, min_score=args.min_score_to_rank)

    targets = args.targets.split(",")
    pushed_stats = op.push(
        data_ranked, targets, args.topics_top_k, args.categories_top_k)

    # Print and create stats
    op.printStats("Twitter", data, data_deduped, data_ranked)
    return op.createStats(
        data, data_deduped, data_scored, data_filtered, data_ranked,
        pushed_stats)


def process_article(args):
    print("#####################################################")
    print("# Process Article")
    print("#####################################################")
    op = OperatorArticle()

    data = op.readFromJson(args.data_folder, args.run_id, "article.json")
    data_deduped = op.dedup(data, target="toread")
    data_summarized = op.summarize(data_deduped)
    data_ranked = op.rank(data_summarized)

    targets = args.targets.split(",")
    pushed_stats = op.push(data_ranked, targets)

    return op.createStats(
        "Article",
        "",
        data,
        data_deduped=data_deduped,
        data_summarized=data_summarized,
        data_ranked=data_ranked,
        pushed_stats=pushed_stats)


def process_youtube(args):
    print("#####################################################")
    print(f"# Process Youtube, dedup: {args.dedup}")
    print("#####################################################")
    op = OperatorYoutube()

    data = op.readFromJson(args.data_folder, args.run_id, "youtube.json")
    data_deduped = data
    need_dedup = utils.str2bool(args.dedup)
    if need_dedup:
        data_deduped = op.dedup(data, target="toread")
    else:
        data_deduped = [x for x in data.values()]

    data_summarized = op.summarize(data_deduped)
    data_ranked = op.rank(data_summarized)

    targets = args.targets.split(",")
    pushed_stats = op.push(data_ranked, targets)

    return op.createStats(
        "YouTube",
        "",
        data,
        data_deduped=data_deduped,
        data_summarized=data_summarized,
        data_ranked=data_ranked,
        pushed_stats=pushed_stats)


def process_rss(args):
    print("#####################################################")
    print(f"# Process RSS, dedup: {args.dedup}")
    print("#####################################################")
    op = OperatorRSS()

    data = op.readFromJson(args.data_folder, args.run_id, "rss.json")
    data_deduped = data

    need_dedup = utils.str2bool(args.dedup)
    if need_dedup:
        data_deduped = op.dedup(data, target="toread")
    else:
        data_deduped = [x for x in data.values()]

    data_scored = op.score(
        data_deduped,
        start_date=args.start,
        max_distance=args.max_distance)

    # Only pick top 1 to reduce the overflow
    data_filtered = op.filter(data_scored, k=1, min_score=4)
    data_summarized = op.summarize(data_filtered)

    targets = args.targets.split(",")
    pushed_stats = op.push(data_summarized, targets)

    return op.createStats(
        "RSS",
        "",
        data,
        data_deduped=data_deduped,
        data_scored=data_scored,
        data_filtered=data_filtered,
        data_summarized=data_summarized,
        pushed_stats=pushed_stats)


def process_reddit(args):
    """
    Reddit has tons of posts to process, apply embedding-based algo
    to calcuate the candidates and merge/select into final data_ranked

    The score is based on user_rating field: [1, 5], ideally
    >= 4 will be a good rating

    cold start: user is still filing GPT ranked score
    warm/hot start: user can filter the new relevant score, e.g.
                    filter score >= 4
    """
    print("#####################################################")
    print("# Process Reddit")
    print("#####################################################")
    op = OperatorReddit()
    data = op.readFromJson(args.data_folder, args.run_id, "reddit.json")
    data_deduped = op.dedup(data, target="toread")

    # To save LLM tokens, do score on all deduped posts, then
    # do rank for score >= 4 posts
    data_scored = op.score(
        data_deduped,
        start_date=args.start,
        max_distance=args.max_distance)

    data_filtered = op.filter(data_scored, min_score=4)

    data_summarized = op.summarize(data_filtered)
    data_ranked = op.rank(
        data_summarized, min_score=args.min_score_to_rank)

    targets = args.targets.split(",")
    pushed_stats = op.push(
        data_ranked, targets, args.topics_top_k, args.categories_top_k)

    # Print and create stats
    op.printStats("Reddit", data, data_deduped, data_ranked)

    return op.createStats(
        data, data_deduped, data_scored, data_filtered,
        data_summarized, data_ranked, pushed_stats)


def run(args):
    sources = args.sources.split(",")
    stats = []

    for source in sources:
        print(f"Pushing data for source: {source} ...")

        # Notes: For twitter we don't need summary step
        if source == "Twitter":
            stat = process_twitter(args)

        elif source == "Article":
            stat = process_article(args)

        elif source == "Youtube":
            stat = process_youtube(args)

        elif source == "RSS":
            stat = process_rss(args)

        elif source == "Reddit":
            stat = process_reddit(args)

        stats.extend(stat)

    # Print stats
    print("#####################################################")
    print("# Stats")
    print("#####################################################")
    for stat in stats:
        stat.print()


if __name__ == "__main__":
    args = parser.parse_args()
    load_dotenv()

    run(args)
