from mysql_cli import MySQLClient
import notion_init


def apply():
    """
    Create Notion metadata table
    """
    print("Initializing MySQL database tables...")
    db_cli = MySQLClient()
    db_cli.create_table_index_pages()

    print("Initializing Notion database tables...")
    notion_init.init()

    return True, "OK"
