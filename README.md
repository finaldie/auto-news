# Auto-News: An Automatic News Aggregator with LLM
A personal news aggregator to pull information from multi-sources + LLM (ChatGPT) to help us read efficiently with less noise, the sources including Tweets, RSS, YouTube and Articles.

## Why need it?
In the world of this information explosion, we live with noise every day, it becomes even worse after the generative AI was born. Time is a precious resource for each of us, How to use our time more efficiently? It becomes more challenging than ever. Think about how much time we spent on pulling/searching/filtering content from different sources, how many times we put the article/paper or long video as a side tab, but never got a chance to look at, and how much effort to organize the information we have read. We need a better way to get rid of the noises, focus on reading the information efficiently based on our interests, and stay on track with the goals we defined.

See this [Blog post](https://finaldie.com/blog/auto-news-an-automated-news-aggregator-with-llm/) for more details.

## Goals
The Auto-News was born for the following goals:
- Automatically pull feed sources, including RSS and Tweets.
- Support clip content from source directly, later generate summary and translation (nice to have), including random web articles, YouTube videos
- Filter content based on personal interests and remove noises
- A unified/central reading experience (e.g. RSS reader)
- Weekly/Monthly top-k aggregations (nice to have)


![image](https://github.com/finaldie/auto-news/assets/1088543/778242a7-5811-49e1-8982-8bd32d141639)

## Architecture
![image](https://github.com/finaldie/auto-news/assets/1088543/d1923ea8-6e4f-46b8-a654-45e21372438e)


## Hardware Requirements

| Component | Requirement |
| --------- | ----------- |
| Memory    | 6GB         |
| Disk      | 20GB+       |

## System Requirements
- Backend
  - [x] Linux
  - [x] MacOS
- UI (Notion)
  - [x] Cross-platform (Web browser, iOS/Android app)

# Installation
## Preparison
* [Required] [Notion token](https://www.notion.so/my-integrations)
* [Required] [OpenAI token](https://openai.com/blog/openai-api)
* [Required] [Docker](https://www.docker.com/)
* [Optional] [Notion Web Clipper](https://chrome.google.com/webstore/detail/notion-web-clipper/knheggckgoiihginacbkhaalnibhilkk)
* [Optional] [Twitter Developer Tokens](https://developer.twitter.com/en)

## [UI] Create Notion Entry Page

Go to [Notion](https://www.notion.so/), create a page as the main entry (For example `Readings` page), and enable Notion `Integration` for this page

## [Backend] Create Environment File
Checkout the repo and copy `.env.template` to `build/.env`, then fill up the environment vars:
* `NOTION_TOKEN`
* `NOTION_ENTRY_PAGE_ID`
* `OPENAI_API_KEY`
* [Optional] Vars with `TWITTER_` prefix

## [Backend] Build Services
```bash
make deps && make build && make deploy && make init
```

## [Backend] Start Services
```bash
make start
```

Now, the services are up and running, it will pull sources every hour.

## [UI] Set up Notion Tweet and RSS list

Go to Notion entry page we created before, and we will see the following folder structure has been created automatically:
```bash
Readings
├── Inbox
│   ├── Inbox - Article
│   └── Inbox - YouTube
├── Index
│   ├── Index - Inbox
│   ├── Index - ToRead
│   ├── RSS_List
│   └── Tweet_List
└── ToRead
    └── ToRead
```

- Go to `RSS_List` page, and fill the RSS name and URL
- Go to `Tweet_List` page, and fill the Tweet screen names


## [UI] Set up Notion database views
Go to Notion `ToRead` database page, all the data will flow into this database later on, create the database views for different sources to help us organize flows easier. E.g. Tweets, Articles, YouTube, RSS, etc

Now, enjoy and have fun.

## [Monitoring] Control Panel
For troubleshooting, we can use the URLs below to access the services and check the logs and data

| Service | Role            | Panel URL             |
| ---     | ---             | ---                   |
| Airflow | Orchestration   | http://localhost:8080 |
| Milvus  | Vector Database | http://localhost:9100 |
| Adminer | DB accessor     | http://localhost:8070 |

## Operations
In case we want, apply the follow commands from the codebase folder

### Stop/Restart Services
```bash
# stop
make stop

# restart
make stop && make start
```

### Redeploy `.env` and DAGs
```bash
make stop && make init && make start
```

### Upgrade to the latest code
```bash
make upgrade && make stop && make init && make start
```
