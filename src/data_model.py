##
# Describe all the data models
#

# Redis key templates
# key: prefix + source_name (article) + list_name (default)
# val: time
NOTION_INBOX_CREATED_TIME_KEY = "notion_inbox_created_time_{}_{}"

# key: prefix + source_name + list_name + id
# val: true/false
NOTION_INBOX_ITEM_ID = "notion_inbox_item_id_{}_{}_{}"

# key: prefix + source_name + list_name + id
# val: true/false
NOTION_TOREAD_ITEM_ID = "notion_toread_item_id_{}_{}_{}"

# key: prefix + source_name (article) + list_name (default)
# val: time
NOTION_TOREAD_LAST_EDITED_KEY = "notion_toread_last_edited_{}_{}"

# key: prefix + source_name + list_name + id
# val: llm ranking respones
NOTION_RANKING_ITEM_ID = "notion_ranking_item_id_{}_{}_{}"

# key: prefix + source_name + list_name + id
# val: llm summary respones
NOTION_SUMMARY_ITEM_ID = "notion_summary_item_id_{}_{}_{}"
