from dotenv import load_dotenv
from ops_notion import OperatorNotion


def init():
    print("Notion initialization started ...")
    op = OperatorNotion()
    op.init()
    print("Notion initialization finished")


if __name__ == "__main__":
    load_dotenv()
    init()
