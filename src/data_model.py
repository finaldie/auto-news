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
# ttl: 2 weeks
NOTION_RANKING_ITEM_ID = "notion_ranking_item_id_{}_{}_{}"

# key: prefix + source_name + list_name + id
# val: llm summary respones
# ttl: 2 weeks
NOTION_SUMMARY_ITEM_ID = "notion_summary_item_id_{}_{}_{}"

# key: prefix + source_name + list_name + id
# val: true/false
OBSIDIAN_INBOX_ITEM_ID = "obsidian_inbox_item_id_{}_{}_{}"

# key: prefix + source_name + provider (openai/hf) + id
# val: embedding data
# ttl: 4 weeks
EMBEDDING_ITEM_ID = "embedding_item_id_{}_{}_{}"

# key: prefix + provider + model_name + source_name + id
# val: embedding data
# ttl: 4 weeks
MILVUS_EMBEDDING_ITEM_ID = "milvus_embedding_item_id_{}_{}_{}_{}"

# key: prefix + source_name + date + id
# val: true/false
# ttl: 4 weeks
MILVUS_PERF_DATA_ITEM_ID = "milvus_collection_item_id_{}_{}_{}"

# key: page_id
# val: json format: {"user_rating": xx}
# ttl: 4 weeks
PAGE_ITEM_ID = "page_item_id_{}"

# key: page_id
# val: json format: {"last_edited_time": xx, "todo": xx}
TODO_ITEM_ID = "todo_item_id_{}"

# key: page_id
# val: json format: {"last_edited_time": xx, "action": xx}
ACTION_ITEM_ID = "action_item_id_{}"
