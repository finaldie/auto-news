##
# Describe all the data models
#

# Redis key templates
# key: prefix + source_name (twitter) + list_name (AI)
# val: created_time
NOTION_INBOX_LAST_READ_TIME_KEY = "notion_inbox_last_read_{}_{}"

# key: prefix + source_name + list_name + id
# val: true/false
NOTION_INBOX_ITEM_ID = "notion_inbox_item_id_{}_{}_{}"

# key: prefix + source_name + list_name + id
# val: true/false
NOTION_TOREAD_ITEM_ID = "notion_toread_item_id_{}_{}_{}"
