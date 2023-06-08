import os
import time
import traceback
from datetime import date

from notion_client import Client

import utils


class NotionAgent:
    """
    A notion agent to operate page/database
    """
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("NOTION_TOKEN")

        self.api = self._init_client(self.api_key)
        self.databases = {}  # <source, {database_id}>

    def _init_client(self, api_key):
        return Client(auth=api_key)

    def addDatabase(self, source_name, database_id):
        self.databases[source_name] = {
            "database_id": database_id,
        }

    def extractRichText(self, data, prefix="", suffix=""):
        """
        The rich_text is a data type and can be used for many blocks,
        e.g. paragraph, bulleted_list_item, headings, etc

        @param data - the rich_text array from one block
        @return the extracted content
        """
        content = ""

        for rich_text in data:
            plain_text = rich_text["plain_text"]

            text = f"{prefix}{plain_text}{suffix}"
            # print(f"Block's rich_text: {text}")

            content += text

        return content

    def extractBlockParagraph(self, block):
        """
        block: notion block object (paragraph type)
        """
        return self.extractRichText(block["paragraph"]["rich_text"])

    def extractQuote(self, block):
        """
        block: notion block object (quote type)
        """
        return self.extractRichText(block["quote"]["rich_text"])

    def extractBulletedListItems(self, block):
        """
        block: notion block object (bulleted_list_item type)
        """
        return self.extractRichText(
            block["bulleted_list_item"]["rich_text"],
            prefix="- ",
            suffix="\n")

    def extractNumberedListItems(self, block):
        """
        block: notion block object (numbered_list_item type)
        """
        return self.extractRichText(
            block["numbered_list_item"]["rich_text"],
            prefix="1. ",
            suffix="\n")

    def extractHeading_1(self, block):
        """
        block: notion block object (heading_1 type)
        """
        return self.extractRichText(block["heading_1"]["rich_text"])

    def extractHeading_2(self, block):
        """
        block: notion block object (heading_2 type)
        """
        return self.extractRichText(block["heading_2"]["rich_text"])

    def extractHeading_3(self, block):
        """
        block: notion block object (heading_3 type)
        """
        return self.extractRichText(block["heading_3"]["rich_text"])

    def extractCode(self, block):
        """
        block: notion block object (code type)
        """
        return self.extractRichText(
            block["code"]["rich_text"],
            prefix="```",
            suffix="```")

    def extractToggle(self, block):
        content = ""
        content += self.extractRichText(block["toggle"]["rich_text"])
        content += "\n"

        if block["has_children"]:
            block_id = block["id"]
            blocks = self.extractBlocks(block_id)
            content += self.concatBlocksText(blocks)

        return content

    def extractTableRow(self, block):
        """
        block: notion block object (table_row type)
        """
        table_row = block["table_row"]
        cells = table_row["cells"]
        content = ""

        for cell in cells:
            # Like rich_text, one cell may contact with
            # multiple cell pieces
            for cell_data in cell:
                content += cell_data["plain_text"]
                # print(f"cell data: {cell_data['plain_text']}")

            content += ","

        return content

    def extractMultiSelect(self, block):
        selects = []

        for select in block["multi_select"]:
            selects.append(select["name"])

        return selects

    def extractBlocks(self, block_id):
        # block_id -> block data
        blocks = {}

        childs = self.api.blocks.children.list(block_id=block_id).get("results")
        # print(f"n: {len(childs)}, childs: {childs}")

        for block in childs:
            block_data = self.extractBlock(block)

            block_id = block["id"]
            blocks[block_id] = block_data

        return blocks

    def extractBlock(self, block):
        """
        block: notion block object

        @return a simplified block_data only contain id, type and text
        """
        block_id = block["id"]
        block_data = {
            "id": block_id,
            "type": block["type"],
            "text": "",
        }

        # print(f"Read block type: {block['type']}, block: {block}")

        text = ""

        if block["type"] == "paragraph":
            text = self.extractBlockParagraph(block)

        elif block["type"] == "bulleted_list_item":
            text = self.extractBulletedListItems(block)

        elif block["type"] == "numbered_list_item":
            text = self.extractNumberedListItems(block)

        elif block["type"] == "heading_1":
            text = self.extractHeading_1(block)

        elif block["type"] == "heading_2":
            text = self.extractHeading_2(block)

        elif block["type"] == "heading_3":
            text = self.extractHeading_3(block)

        elif block["type"] == "table":
            # depth forward in the child blocks
            pros, blocks = self.extractPage(block_id)
            text = self.concatBlocksText(blocks)

        elif block["type"] == "table_row":
            text = self.extractTableRow(block)

            # Easier for human reading
            text += "\n"

        elif block["type"] == "quote":
            text = self.extractQuote(block)

        elif block["type"] == "code":
            text = self.extractCode(block)

        elif block["type"] == "toggle":
            text = self.extractToggle(block)

        else:
            print(f"[Unsupported block type]!!!: {block['type']}, block: {block}")

        block_data["text"] = text
        block_data["type"] = block["type"]
        block_data["__raw"] = block
        return block_data

    def _extractPageProps(self, page):
        """
        cherry pick props from notion page object
        """
        return {
            "id": page["id"],

            # below two time are utc time
            "created_time": page["created_time"],
            "last_edited_time": page["last_edited_time"],

            "url": page["url"],
            "properties": page["properties"],
        }

    def concatBlocksText(self, blocks, separator=''):
        """
        blocks: Converted internal blocks dict (not notion block
                object). format: <block_id, block_data>

        """
        content = ""

        for block_id, block_data in blocks.items():
            text = block_data["text"]

            content += text
            content += separator

        return content

    def extractPage(
            self,
            page_id,
            extract_blocks=True,
            retrieval_retry=3,
    ):
        properties = {}

        # block_id -> block data
        blocks = {}

        page = None
        trying_cnt = 0
        retry_sleep_time = 5  # 5 seconds

        while trying_cnt < retrieval_retry:
            trying_cnt += 1

            try:
                print(f"Retrieving {trying_cnt}/{retrieval_retry}, page id: {page_id}")
                page = self.api.pages.retrieve(page_id=page_id)
                properties = self._extractPageProps(page)
                break

            except Exception as e:
                print(f"Retry {trying_cnt}/{retrieval_retry}, sleep for {retry_sleep_time}s, error: {e}")
                time.sleep(retry_sleep_time)

        if not page:
            print(f"[ERROR] After {trying_cnt} retries (max {retrieval_retry}), still cannot fetch the page {page_id}, exit...")
            return properties, blocks

        if extract_blocks:
            blocks = self.extractBlocks(page_id)

        return properties, blocks

    def queryDatabase_RSSList(self, database_id):
        query_data = {
            "database_id": database_id,
            "sorts": [
                {
                    "property": "Created time",
                    "direction": "descending",
                },
            ],

            "filter": {
                "and": [
                    {
                        "property": "Enabled",
                        "checkbox": {
                            "equals": True,
                        },
                    },
                ]
            }
        }

        pages = self.api.databases.query(**query_data).get("results")
        extracted_pages = []

        for page in pages:
            print(f"result: page id: {page['id']}")
            page_id = page["id"]

            extracted_pages.append({
                "page_id": page_id,
                "database_id": database_id,
                "name": page["properties"]["Name"]["title"][0]["text"]["content"],
                "url": page["properties"]["URL"]["url"],
                "created_time": page["created_time"],
                "last_edited_time": page["last_edited_time"],
            })

        return extracted_pages

    def queryDatabaseIndex_Inbox(self, database_id, source):
        query_data = {
            "database_id": database_id,
            "sorts": [
                {
                    "property": "Created time",
                    "direction": "descending",
                },
            ],

            "filter": {
                "and": [
                    {
                        "property": "Source",
                        "select": {
                            "equals": source,
                        }
                    },
                ]
            }
        }

        pages = self.api.databases.query(**query_data).get("results")
        extracted_pages = []

        for page in pages:
            print(f"result: page id: {page['id']}")
            page_id = page["id"]

            extracted_pages.append({
                "page_id": page_id,
                "database_id": page["properties"]["id"]["title"][0]["text"]["content"],
                "created_time": page["created_time"],
                "last_edited_time": page["last_edited_time"],
                "source": source,
            })

        return extracted_pages

    def queryDatabaseIndex_ToRead(self, database_id):
        query_data = {
            "database_id": database_id,
            "sorts": [
                {
                    "property": "Created time",
                    "direction": "descending",
                },
            ],
        }

        pages = self.api.databases.query(**query_data).get("results")
        extracted_pages = []

        for page in pages:
            print(f"result: page id: {page['id']}")
            page_id = page["id"]

            extracted_pages.append({
                "page_id": page_id,
                "database_id": page["properties"]["id"]["title"][0]["text"]["content"],
                "created_time": page["created_time"],
                "last_edited_time": page["last_edited_time"],
            })

        return extracted_pages

    def createDatabaseItem_Index_ToRead(
        self,
        database_id,
        to_read_db_id,
        title
    ):
        properties = {
            "id": {
                "title": [
                    {
                        "text": {
                            "content": to_read_db_id
                        }
                    }
                ]
            },

            "Title": {
                "rich_text": [
                    {
                        "text": {
                            "content": title,
                        },
                    },
                ]
            },
        }

        # Add the new page to the database
        new_page = self.api.pages.create(
            parent={"database_id": database_id},
            properties=properties)

        return new_page

    def createDatabase_ToRead(self, name, parent_page_id):
        """
        Create a database for ToRead, Collection, etc
        """
        title = [
            {
                "type": "text",
                "text": {
                    "content": name,
                }
            }
        ]

        # Set the properties of the new database
        new_database_properties = {
            "Name": {
                "title": {}
            },
            "To": {
                "rich_text": {}
            },
            "Created at": {
                "date": {}
            },
            "Topic": {
                "multi_select": {}
            },
            "Category": {
                "multi_select": {}
            },
            "Rating": {
                "number": {}
            },
            "Read": {
                "checkbox": {}
            },
            "Created time": {
                "created_time": {}
            },
            "List Name": {
                "multi_select": {}
            },
            "Last edited time": {
                "last_edited_time": {}
            },
            "User Rating": {
                "select": {}
            },
            "Relevant Score": {
                "number": {}
            },
            "Tags": {
                "multi_select": {}
            },
            "Source": {
                "select": {}
            },
            "Take Aways": {
                "rich_text": {}
            },
        }

        # Create the new database under the specified page
        new_database = self.api.databases.create(
            parent={"type": "page_id", "page_id": parent_page_id},
            title=title,
            properties=new_database_properties
        )

        return new_database

    def queryDatabaseInbox_Twitter(self, database_id, created_time=None):
        query_data = {
            "database_id": database_id,
            "sorts": [
                {
                    "property": "Created time",
                    "direction": "ascending",
                },
            ],

            "filter": {}
        }

        # filter by created_time
        if created_time:
            query_data["filter"]["and"] = []
            query_data["filter"]["and"].append({
                "property": "Created time",
                "date": {
                    "on_or_after": created_time,
                }
            })

        pages = self.api.databases.query(**query_data).get("results")

        extracted_pages = {}
        for page in pages:
            print(f"result: page id: {page['id']}")

            page_id = page["id"]
            props, blocks = self.extractPage(page_id)
            page_content = self.concatBlocksText(blocks)

            extracted_pages[page_id] = {
                "name": page["properties"]["Name"]["title"][0]["text"]["content"],
                "to": page["properties"]["To"]["rich_text"][0]["text"]["content"],
                # pdt timezone
                "created_at": page["properties"]["Created at"]["date"]["start"],
                "created_time": page["created_time"],
                "preview": page["properties"]["Preview"]["rich_text"][0]["text"]["content"],
                "notion_url": page["url"],
                "source": "Twitter",

                "content": page_content,
            }

        return extracted_pages

    def queryDatabaseInbox_Article(
        self,
        database_id,
        filter_last_edited_time=None,
        filter_created_time=None
    ):
        query_data = {
            "database_id": database_id,

            "sorts": [
                {
                    "property": "Created time",
                    "direction": "ascending",
                },
            ],

            "filter": {
                "and": [],
            },
        }

        if filter_last_edited_time:
            query_data["filter"]["and"].append({
                "property": "Last edited time",
                "date": {
                    # "on_or_after": filter_last_edited_time,
                    "after": filter_last_edited_time,
                }
            })

        if filter_created_time:
            query_data["filter"]["and"].append({
                "property": "Created time",
                "date": {
                    "on_or_after": filter_created_time,
                }
            })

        print(f"Query article inbox, query: {query_data}")

        pages = self.api.databases.query(**query_data).get("results")
        print(f"Queried pages: {pages}")

        extracted_pages = {}
        for page in pages:
            print(f"result: page id: {page['id']}")

            page_id = page["id"]
            props, blocks = self.extractPage(page_id)
            page_content = self.concatBlocksText(blocks)

            print(f"Extracting one page: {page}, props: {props}")

            extracted_pages[page_id] = {
                "id": page_id,

                # article title
                "title": props["properties"]["Name"]["title"][0]["plain_text"],
                # utc timezone (notion auto-created)
                "created_time": props["created_time"],

                # utc timezone (notion auto-created)
                "last_edited_time": props["last_edited_time"],
                "notion_url": props["url"],
                "source_url": props["properties"]["URL"]["url"],
                "source": "Article",

                "props": props,
                "blocks": blocks,

                "content": page_content,
            }

        return extracted_pages

    def queryDatabaseInbox_Youtube(
        self,
        database_id,
        filter_last_edited_time=None,
        filter_created_time=None
    ):
        extracted_pages = self.queryDatabaseInbox_Article(
            database_id,
            filter_last_edited_time=filter_last_edited_time,
            filter_created_time=filter_created_time)

        # Fix fields such as 'source'
        for page_id, page in extracted_pages.items():
            page["source"] = "Youtube"

        return extracted_pages

    def queryDatabaseToRead(
        self,
        database_id,
        source: str,
        last_edited_time=None
    ):
        query_data = {
            "database_id": database_id,
            "sorts": [
                {
                    "property": "Last edited time",
                    "direction": "ascending",
                },
            ],

            "filter": {
                "and": [
                    {
                        "property": "Source",
                        "select": {
                            "equals": source,
                        }
                    },
                    {
                        "property": "User Rating",
                        "select": {
                            "is_not_empty": True,
                        }
                    },
                ]
            }
        }

        # filter by created_time
        if last_edited_time:
            query_data["filter"]["and"].append({
                "property": "Last edited time",
                "date": {
                    "on_or_after": last_edited_time,
                }
            })

        pages = self.api.databases.query(**query_data).get("results")

        extracted_pages = {}
        for page in pages:
            print(f"result: page id: {page['id']}")

            page_id = page["id"]
            props, blocks = self.extractPage(page_id)

            rating_prop = page["properties"]["User Rating"]["select"]

            extracted_pages[page_id] = {
                "id": page_id,
                "name": page["properties"]["Name"]["title"][0]["text"]["content"],
                # pdt timezone
                "created_at": page["properties"]["Created at"]["date"]["start"],
                "created_time": page["created_time"],
                "last_edited_time": props["last_edited_time"],
                "notion_url": page["url"],

                # extract user rating (frequent used field)
                "user_rating": rating_prop["name"] if rating_prop else None,
                "source": source,

                "properties": props,
                "blocks": blocks,
            }

        return extracted_pages

    def _createDatabaseItem_TwitterBase(self, list_names, tweet):
        """
        Create page properties and blocks
        """

        # assemble list name(s), sub-category of source, e.g.
        # The content from twitter and AI list
        source_list_names = [{"name": ln} for ln in list_names]

        preview_content = tweet['text']
        if tweet["retweeted"]:
            preview_content = f"Retweeted: {preview_content}"

        properties = {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": f"{tweet['name']}"
                        }
                    }
                ]
            },

            "To": {
                "rich_text": [
                    {
                        "text": {
                            "content": tweet['reply_to_name'] if tweet['reply_to_name'] else ""
                        }
                    }
                ]
            },

            "Created at": {
                "date": {
                    "start": tweet['created_at_pdt'],
                    # "time_zone": "America/Los_Angeles",
                }
            },

            # "Preview": {
            #     "rich_text": [
            #         {
            #             "text": {
            #                 "content": preview_content,
            #                 "link": {
            #                     "url": tweet_url,
            #                 }
            #             },
            #             "href": tweet_url,
            #         },
            #     ]
            # },

            "List Name": {
                "multi_select": source_list_names,
            },
        }

        blocks = []

        if tweet['reply_text']:
            blocks.append({
                "object": "block",
                "type": "quote",
                "quote": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": f"{tweet['reply_to_name']}: {tweet['reply_text']}",
                                # "link": tweet["reply_url"],
                            },
                            # "href": tweet["reply_url"],
                        }
                    ]
                }
            })

            # assemble embeding content if it's in the replied content
            if tweet['reply_embed']:
                blocks.append({
                    "type": "embed",
                    "embed": {
                        "url": utils.urlUnshorten(tweet['reply_embed'])
                    }
                })

            # print(f"reply_tweet.url: {tweet['reply_embed']}")

        elif tweet['reply_deleted']:
            blocks.append({
                "object": "block",
                "type": "quote",
                "quote": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": f"@{tweet['reply_to_screen_name']}: Tweet has been deleted / hidden :(",
                                # "link": tweet["reply_url"],
                            },
                            # "href": tweet["reply_url"],
                        }
                    ]
                }
            })

        # Append author's tweet
        block_content = f"{tweet['name']}"
        if tweet["retweeted"]:
            block_content += " (Retweeted)"

        block_content += f": {tweet['text']}"

        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": self._createBlock_RichText(block_content)
            }
        })

        # append embeded content (if have)
        if tweet['embed']:
            blocks.append({
                "type": "embed",
                "embed": {
                    "url": utils.urlUnshorten(tweet['embed'])
                }
            })

        # In the bottom, append the original tweet link
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "text": {
                            "content": "Tweet link",
                            "link": {
                                "url": tweet["url"],
                            },
                        },
                        "href": tweet["url"],
                    },
                ],
            }
        })

        return properties, blocks

    def _createDatabaseItem_ArticleBase(self, ranked_page, **kwargs):
        """
        Create page properties and blocks, will put the summary
        instead of orignal content

        Special fields:
        - content    The original content (Could be very huge), notes that each block has 2000 chars limitation
        - __summary  The summary content
        """
        summary = ranked_page.get("__summary") or ""
        # preview_content = summary[:100] + "..."

        created_time_pdt = utils.convertUTC2PDT_str(ranked_page["created_time"])

        append_notion_url = kwargs.setdefault("append_notion_url", True)
        prop_add_take_away = kwargs.setdefault("prop_add_take_away", False)

        properties = {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": f"{ranked_page['title']}"
                        }
                    }
                ]
            },

            "Created at": {
                "date": {
                    "start": created_time_pdt.isoformat(),
                    # "time_zone": "America/Los_Angeles",
                }
            },

            # "Preview": {
            #     "rich_text": [
            #         {
            #             "text": {
            #                 "content": preview_content,
            #                 "link": {
            #                     "url": ranked_page["source_url"],
            #                 }
            #             },
            #             "href": ranked_page["source_url"],
            #         },
            #     ]
            # },
        }

        if prop_add_take_away:
            properties.update({
                "Take Aways": {
                    "rich_text": [
                        {
                            "text": {
                                "content": ranked_page["__take_aways"],
                            },
                        },
                    ]
                },
            })

        # put summary content
        summary_en, summary_trans = utils.splitSummaryTranslation(summary)
        block_content = f"Summary:\n{summary_en}"

        blocks = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": self._createBlock_RichText(block_content)
                }
            }
        ]

        if summary_trans:
            blocks.append(self._createBlock_Toggle(
                "Translation", summary_trans))

        # append orginal notion url
        if append_notion_url:
            blocks.append({
                "type": "link_to_page",
                "link_to_page": {
                    "type": "page_id",
                    "page_id": ranked_page['id']
                }
            })

        return properties, blocks

    def _createDatabaseItem_YoutubeBase(self, ranked_page):
        """
        Create page properties and blocks, will put the summary first
        Follow by the video

        Special fields:
        - content    The original content (Could be very huge), notes that each block has 2000 chars limitation
        - __summary  The summary content
        """
        summary = ranked_page["__summary"]
        preview_content = summary[:100] + "..."

        created_time_pdt = utils.convertUTC2PDT_str(ranked_page["created_time"])

        # For title, some apps may create the notion page title with
        # the URL directly, not the title, here we use extracted title
        # first, if empty, fallback to the notion page title
        title = ranked_page["__title"] or ranked_page['title']

        # Notes: if source_url is empty, fallback to
        # notion page title (it could be the url)
        source_url = ranked_page["source_url"] or ranked_page["title"]

        # Dirty fix to get rid of the unnecessary url parameters
        source_url = source_url.replace("&feature=share", "")

        print(f"[notion] push page, title: {title}, summary: {summary}, preview: {preview_content}, source_url: {source_url}")

        properties = {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            },

            "Created at": {
                "date": {
                    "start": created_time_pdt.isoformat(),
                    # "time_zone": "America/Los_Angeles",
                }
            },

            # "Preview": {
            #     "rich_text": [
            #         {
            #             "text": {
            #                 "content": preview_content,
            #                 "link": {
            #                     "url": source_url,
            #                 }
            #             },
            #             "href": source_url,
            #         },
            #     ]
            # },
        }

        summary_en, summary_trans = utils.splitSummaryTranslation(summary)
        block_content = f"Summary:\n{summary_en}"

        blocks = [
            # put summary content
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": self._createBlock_RichText(block_content)
                }
            },
        ]

        if summary_trans:
            blocks.append(self._createBlock_Toggle(
                "Translation", summary_trans))

        blocks.append({
            "object": "block",
            "type": "video",
            "video": {
                "type": "external",
                "external": {
                    "url": source_url,
                },
            }
        })

        return properties, blocks

    def createDatabaseItem_TwitterInbox(
        self,
        database_id,
        list_names,
        tweet
    ):
        """
        Create a page under a database
        database_id: the target notion database id
        tweet: the extracted tweet from TwitterAgent
        """
        properties, blocks = self._createDatabaseItem_TwitterBase(
            list_names, tweet)

        print(f"notion twitter inbox: database_id: {database_id}, properties: {properties}, blocks: {blocks}")

        # Add the new page to the database
        new_page = self.api.pages.create(
            parent={"database_id": database_id},
            properties=properties,
            children=blocks)

        return new_page

    def _createBlock_RichText(self, text, chunk_size=1900):
        """
        Each rich text content must be <= 2000, use 1900 to be safer
        """
        arr = text.split("\n")
        cur_size = 0
        cur_text = []
        rich_texts = []

        for i in range(len(arr)):
            new_size = cur_size + len(arr[i])

            if new_size <= chunk_size:
                cur_size += len(arr[i])
                cur_text.append(arr[i])
            else:
                rich_texts.append({
                    "text": {
                        "content": "\n".join(cur_text)
                    },
                })

                # reset to arr[i]
                cur_text = [arr[i]]
                cur_size = len(arr[i])

        # append last
        rich_texts.append({
            "text": {
                "content": "\n".join(cur_text)
            },
        })

        if len(rich_texts) > 1:
            print(f"[notion._createBlock_RichText]: chunked rich text content into {len(rich_texts)} chunks")

        return rich_texts

    def _createBlock_Toggle(self, title, content):
        return {
            "type": "toggle",

            "toggle": {
                "rich_text": [{
                    "type": "text",
                    "text": {
                        # This is usually very short
                        "content": title,
                    }
                }],

                "color": "default",
                "children": [{
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": self._createBlock_RichText(content)
                    }
                }]
            }
        }

    def createDatabaseItem_ToRead(
        self,
        database_id,
        list_names: list,
        tweet,
        topics: list,
        categories: list,
        rate_number
    ):
        """
        Create toread database item, source twitter
        """
        properties, blocks = self._createDatabaseItem_TwitterBase(
            list_names, tweet)

        # assemble topics
        topics_list = [{"name": t} for t in topics]

        # assemble category (multi-select)
        categories_list = [{"name": c} for c in categories]

        properties["Source"] = {
            "select": {
                "name": "Twitter",
            }
        }

        properties.update({"Topic": {
            "multi_select": topics_list,
        }})

        properties.update({"Category": {
            "multi_select": categories_list,
        }})

        properties.update({"Rating": {
            "number": rate_number
        }})

        if tweet.get("__relevant_score"):
            properties.update({"Relevant Score": {
                "number": tweet["__relevant_score"]
            }})

        print(f"notion ToRead: database_id: {database_id}, properties: {properties}, blocks: {blocks}")

        # Add the new page to the database
        new_page = self.api.pages.create(
            parent={"database_id": database_id},
            properties=properties,
            children=blocks)

        # Try to add comments for user and reply_user
        try:
            page_id = new_page["id"]

            print(f"Add user description as comment: {tweet['name']}, desc: {tweet['user_desc']}")
            self.createPageComment(
                page_id,
                f"{tweet['name']}: {tweet['user_desc']}")

            if tweet["reply_to_name"] and tweet["name"] != tweet["reply_to_name"]:
                self.createPageComment(
                    page_id,
                    f"{tweet['reply_to_name']}: {tweet['reply_user_desc']}")

        except Exception as e:
            print(f"[ERROR] Failed to add comment: {e}")
            traceback.print_exc()

        return new_page

    def _postprocess_ToRead(
        self,
        properties,
        blocks,
        database_id,
        ranked_page,
        topics: list,
        categories: list,
        rate_number,
        **kwargs
    ):
        # assemble topics
        topics_list = [{"name": t} for t in topics]

        # assemble category (multi-select)
        categories_list = [{"name": c} for c in categories]

        list_names = kwargs.setdefault("list_names", [])
        source_list_names = [{"name": ln} for ln in list_names]

        properties.update({"Source": {
            "select": {
                "name": ranked_page["source"],
            }
        }})

        if len(list_names) > 0:
            properties.update({
                "List Name": {
                    "multi_select": source_list_names,
                },
            })

        properties.update({"Topic": {
            "multi_select": topics_list,
        }})

        properties.update({"Category": {
            "multi_select": categories_list,
        }})

        properties.update({"Rating": {
            "number": rate_number
        }})

        if ranked_page.get("__relevant_score"):
            properties.update({"Relevant Score": {
                "number": ranked_page["__relevant_score"]
            }})

        print(f"notion ToRead: database_id: {database_id}, properties: {properties}, blocks: {blocks}")

        # Add the new page to the database
        new_page = self.api.pages.create(
            parent={"database_id": database_id},
            properties=properties,
            children=blocks)

        return new_page

    def createDatabaseItem_ToRead_Article(
        self,
        database_id,
        ranked_page,
        topics: list,
        categories: list,
        rate_number
    ):
        properties, blocks = self._createDatabaseItem_ArticleBase(ranked_page)

        # Common fields for article, youtube, etc
        return self._postprocess_ToRead(
            properties,
            blocks,
            database_id,
            ranked_page,
            topics,
            categories,
            rate_number
        )

    def createDatabaseItem_ToRead_Youtube(
        self,
        database_id,
        ranked_page,
        topics: list,
        categories: list,
        rate_number
    ):
        properties, blocks = self._createDatabaseItem_YoutubeBase(ranked_page)

        # Common fields for article, youtube, etc
        new_page = self._postprocess_ToRead(
            properties,
            blocks,
            database_id,
            ranked_page,
            topics,
            categories,
            rate_number
        )

        # Add video metadata as a comment
        video_metadata = f"""
        Author: {ranked_page['__author']}
        Description: {ranked_page['__description']}
        Publishing date: {ranked_page['__publish_date']}
        Duration: {ranked_page['__length'] / 60:.2f} minutes
        View count: {ranked_page['__view_count']}
        """

        try:
            page_id = new_page["id"]

            print("Add video metadata as comment")
            self.createPageComment(page_id, video_metadata)

        except Exception as e:
            print(f"[ERROR] Failed to add comment: {e}")
            traceback.print_exc()

        return new_page

    def createDatabaseItem_ToRead_RSS(
        self,
        database_id,
        page,
        topics: list,
        categories: list,
        rate_number
    ):
        properties, blocks = self._createDatabaseItem_ArticleBase(
            page, append_notion_url=False)

        # Append original article link
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "text": {
                            "content": "Article Link",
                            "link": {
                                "url": page["url"],
                            },
                        },
                        "href": page["url"],
                    },
                ],
            }
        })

        # Common fields for article, youtube, etc
        return self._postprocess_ToRead(
            properties,
            blocks,
            database_id,
            page,
            topics,
            categories,
            rate_number,
            list_names=[page["list_name"]]
        )

    def createDatabaseItem_ToRead_Collection(
        self,
        database_id,
        page,
        topics: list,
        categories: list,
        rate_number,
        **kwargs
    ):
        properties, blocks = self._createDatabaseItem_ArticleBase(
            page, append_notion_url=True, **kwargs)

        # Common fields for article, youtube, etc
        return self._postprocess_ToRead(
            properties,
            blocks,
            database_id,
            page,
            topics,
            categories,
            rate_number,
            list_names=[page["list_name"]]
        )

    def createPageComment(
        self,
        page_id,
        comment_text: str
    ):
        new_comment = self.api.comments.create(
            parent={"page_id": page_id},
            rich_text=[{
                "type": "text",
                "text": {
                    "content": f"{comment_text}"
                }
            }]
        )

        print(f"Created a new comment: {comment_text}, new_comment object: {new_comment}")
        return new_comment
