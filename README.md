# auto-news
News from multi-sources + LLM (ChatGPT) to help us reading efficiently without noise

placeholder: image for notion ui

## Architecture

placeholder: image for high-level architecture

## Hardware Requirement

| Component | Requirement |
| Memory    | 6GB         |
| Disk      | 20GB+       |

# Installation
## Preparison
* Notion token (Required)
* Docker (Required)
* Twitter token (optional)

Copy `.env.template` to `build/.env`, and fill up the environment vars:
* `NOTION_TOKEN`
* `NOTION_DATABASE_ID_INDEX_INBOX`
* `NOTION_DATABASE_ID_INDEX_TOREAD`
* `OPENAI_API_KEY`
* [Optional] Vars with `TWITTER_` prefix

## Start Services
```bash
make build
make start
```

After 2 minutes, the services would be started, then enable DAGs:
```bash
make enable_dags
```

## Set up Notion database views
Go to Notion, and create the database views for different source, e.g. Tweets, Article, Youtube, RSS, etc

## Control Panel
For troubleshooting, we can use the URLs below to access the services and check the logs and data

| Service | Responsibility  | Panel URL             |
| Airflow | Orchestration   | http://localhost:8080 |
| Milvus  | Vector Database | http://localhost:9100 |
