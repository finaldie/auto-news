import os
import traceback

from db_cli import DBClient
import tpl_obsidian


class OperatorObsidian:
    def dedup(self, pages):
        """
        data: {
            "page_id1": page1,
            "page_id2": page2,
            ...
        }
        """
        print("#####################################################")
        print("# Dedup Obsidian pages")
        print("#####################################################")
        client = DBClient()
        deduped_pages = []

        for page_id, page in pages.items():
            name = page["name"]
            print(f"Dedupping page, title: {name}")

            if client.get_obsidian_inbox_item_id(
                    "obsidian", "default", page_id):
                print(f"Duplicated obsidian found, skip. page_id: {page_id}")
            else:
                deduped_pages.append(page)

        print(f"Pages after dedup: {len(deduped_pages)}")
        return deduped_pages

    def filters(self, pages: list, **kwargs):
        """
        pages after dedup, format: [page1, page2, ...]
        """
        print("#####################################################")
        print("# Filtering Obsidian pages")
        print("#####################################################")
        min_rating = kwargs.setdefault("min_rating", 4)
        print(f"min_rating: {min_rating}, type: {type(min_rating)}")

        filtered_pages = []
        tot = 0
        skipped = 0

        for page in pages:
            name = page["name"]
            user_rating = page["user_rating"]
            tot += 1

            if user_rating < min_rating:
                print(f"[INFO] Skip low quality content, name: {name}, user_rating: {user_rating}")
                skipped += 1
                continue

            filtered_pages.append(page)

        print(f"[INFO] Finished, total {tot}, skipped: {skipped}")
        return filtered_pages

    def push(self, pages, **kwargs):
        """
        Create and push Obsidian pages to specific folder
        """
        print("#####################################################")
        print("# Push Obsidian pages")
        print("#####################################################")

        data_folder = kwargs.setdefault("data_folder", "") or os.getenv("OBSIDIAN_FOLDER")
        if not data_folder:
            print("[ERROR] Data folder path is invalid, skip pushing")
            return

        print(f"Data folder: {data_folder}")

        client = DBClient()
        tot = 0
        err = 0

        for page in pages:
            tot += 1

            try:
                filename, content = self._gen_ob_page(page)
                self._save_ob_page(data_folder, filename, content)
                # self.markVisisted(page_id, db_client=client)

            except Exception as e:
                print(f"[ERROR] Failed to push obsidian md: {e}")
                traceback.print_exc()
                err += 1

        print(f"[INFO] Finished, total {tot}, errors: {err}")

    def markVisisted(self, page_id, db_client=None):
        client = db_client or DBClient()
        client.set_obsidian_inbox_item_id(
            "obsidian", "default", page_id)

    def _gen_ob_page(self, page):
        # print(f"[_gen_ob_page] page: {page}")
        tpl_title = tpl_obsidian.TEMPLATE_OBSIDIAN_INBOX_FILE
        tpl_body = tpl_obsidian.TEMPLATE_OBSIDIAN_INBOX_BODY

        name = page["name"]
        props = page["properties"]["properties"]
        source = page.get("source") or props["Source"]["select"]["name"]

        # TODO: Use notion util to extract content
        created_at = page["created_at"]
        rating = props["Rating"]["number"]
        user_rating = props["User Rating"]["select"]["name"]
        alias = name
        to = props["To"]["rich_text"][0]["plain_text"] if props["To"]["rich_text"] else ""
        list_name = props["List Name"]["multi_select"][0]["name"] if props["List Name"]["multi_select"] else ""
        notion_url = page["notion_url"]
        take_aways = props["Take Aways"]["rich_text"][0]["plain_text"] if props["Take Aways"]["rich_text"] else ""

        filename = tpl_title.format(source, "default", name)
        content = tpl_body.format(
            created_at,
            rating,
            user_rating,
            alias,
            to,
            source,
            list_name,
            notion_url,
            "default",  # TODO: topic
            "default",  # TODO: category
            take_aways,
            "test",     # TODO: body
        )

        print(f"[INFO] Gen obsidian page, filename: {filename}")
        print(f"[INFO] Gen obsidian body, content: {content}")
        return filename, content

    def _save_ob_page(self, data_path, filename, content):
        full_path = f"{data_path}/{filename}"
        print(f"[INFO] Obsidian data path: {data_path}, filename: {filename}, full_path: {full_path}")

        # TODO: save page
