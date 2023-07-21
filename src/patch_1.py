from ops_notion import OperatorNotion


def apply():
    print("Initializing Notion database tables (Reddit) ...")
    op = OperatorNotion()
    op.init_reddit_pages()

    return True, "OK"
