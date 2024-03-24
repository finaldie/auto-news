# Auto-News: An Automatic News Aggregator with LLM

[![GitHub Build](https://github.com/finaldie/auto-news/actions/workflows/python.yml/badge.svg)](https://github.com/finaldie/auto-news/actions)
![Kubernetes](https://img.shields.io/badge/kubernetes-%23326ce5.svg?style=Flat&logo=kubernetes&logoColor=white)
![Notion](https://img.shields.io/badge/Notion-%23000000.svg?style=Flat&logo=notion&logoColor=white)
![ChatGPT](https://img.shields.io/badge/chatGPT-74aa9c?style=Flat&logo=openai&logoColor=white)

A personal news aggregator to pull information from multi-sources + LLM (ChatGPT) to help us read efficiently with less noise, the sources including Tweets, RSS, YouTube, Web Articles, Reddit, and random Journal notes.

<img src="https://github.com/finaldie/auto-news/assets/1088543/ca046ce6-17e5-4fcf-b5a3-6444ad69af3c" width="90%"/>

## Why need it?
In the world of this information explosion, we live with noise every day, it becomes even worse after the generative AI was born. Time is a precious resource for each of us, How to use our time more efficiently? It becomes more challenging than ever. Think about how much time we spent on pulling/searching/filtering content from different sources, how many times we put the article/paper or long video as a side tab, but never got a chance to look at, and how much effort to organize the information we have read. We need a better way to get rid of the noises, focus on reading the information efficiently based on our interests, and stay on track with the goals we defined.

See this [Blog post](https://finaldie.com/blog/auto-news-an-automated-news-aggregator-with-llm/) and these videos [Introduction](https://www.youtube.com/watch?v=hKFIyfAF4Z4), [Data flows](https://www.youtube.com/watch?v=WAGlnRht8LE) for more details.

https://github.com/finaldie/auto-news/assets/1088543/4387f688-61d3-4270-b5a6-105aa8ee0ea9

## Features
- Aggregate feed sources (including RSS, Reddit, Tweets, etc) with summarization
- Summarize YouTube videos (generate transcript if needed)
- Summarize Web Articles (generate transcript if needed)
- Filter content based on personal interests and remove 80%+ noises
- A unified/central reading experience (e.g., RSS reader-like style, Notion based)
- [LLM] Generate `TODO` list from Takeaways/Journal-notes
- [LLM] Organize Journal notes with summarization and insights
- [LLM] **Experimental** [Deepdive](https://github.com/finaldie/auto-news/wiki/Deepdive-(Experimental)) topic via web search agent and [autogen](https://github.com/microsoft/autogen)
- Multi-LLM backend: OpenAI ChatGPT, Google Gemini
- Weekly top-k aggregations


![image](https://github.com/finaldie/auto-news/assets/1088543/778242a7-5811-49e1-8982-8bd32d141639)

## Documentation
https://github.com/finaldie/auto-news/wiki

## Architecture
* UI: Notion-based, cross-platform (Web browser, iOS/Android app)
* Backend: Runs on Linxu/MacOS
  * For deployment: Support both [docker-compose](https://docs.docker.com/compose/) and [kubernetes](https://kubernetes.io/)

![image](https://github.com/finaldie/auto-news/assets/1088543/d1923ea8-6e4f-46b8-a654-45e21372438e)


## Backend System Requirements
| Component | Minimum Requirements | Recommended  |
| --------- | -----------          | ----         |
| OS        | Linux, MacOS         | Linux, MacOS |
| CPU       | 2 cores              | 8 cores      |
| Memory    | 6GB                  | 16GB         |
| Disk      | 20GB                 | 100GB        |

# Quick Start Guide (Docker-compose)
## Preparison
* [Required] [Docker](https://www.docker.com/)
* [Required] [Notion Token](https://www.notion.so/my-integrations)
* [Required] [OpenAI API KEY](https://openai.com/blog/openai-api)
* [Optional] [Google API KEY](https://makersuite.google.com/app/apikey)
* [Optional] [Notion Web Clipper](https://chrome.google.com/webstore/detail/notion-web-clipper/knheggckgoiihginacbkhaalnibhilkk) Highly Recommended! 
* [Optional] [Reddit Tokens](https://www.reddit.com/prefs/apps)
* [Optional] [Twitter Developer Tokens](https://developer.twitter.com/en), **Paid Account Only**

## [UI] Create Notion Entry Page

Go to [Notion](https://www.notion.so/), create a page as the main entry (For example `Readings` page), and enable Notion `Integration` for this page

## [Backend] Create Environment File
Checkout the repo and copy `.env.template` to `build/.env`, then fill up the environment vars:
* `NOTION_TOKEN`
* `NOTION_ENTRY_PAGE_ID`
* `OPENAI_API_KEY`
* [Optional] `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET`
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

## [UI] Set up Notion Tweet/RSS/Reddit list

Go to the Notion entry page we created before, and we will see the following folder structure has been created automatically:
```bash
Readings
├── Inbox
│   ├── Inbox - Article
│   └── Inbox - YouTube
│   └── Inbox - Journal
├── Index
│   ├── Index - Inbox
│   ├── Index - ToRead
│   ├── RSS_List
│   └── Tweet_List
│   └── Reddit_List
└── ToRead
    └── ToRead
```

- Go to `RSS_List` page, and fill in the RSS name and URL
- Go to `Reddit_List` page, and fill the subreddit names
- Go to `Tweet_List` page, and fill in the Tweet screen names (Tips: **Paid Account Only**)

## [UI] Set up Notion database views
Go to Notion `ToRead` database page, all the data will flow into this database later on, create the database views for different sources to help us organize flows easier. E.g. Tweets, Articles, YouTube, RSS, etc

Now, enjoy and have fun.

# Kubernetes Deployment

See the installation guide from: [Installation using Helm](https://github.com/finaldie/auto-news/wiki/Installation-using-Helm)

# Operations
## [Monitoring] Control Panel
For troubleshooting, we can use the URLs below to access the services and check the logs and data

| Service | Role            | Panel URL             |
| ---     | ---             | ---                   |
| Airflow | Orchestration   | http://localhost:8080 |
| Milvus  | Vector Database | http://localhost:9100 |
| Adminer | DB accessor     | http://localhost:8070 |

## Stop/Restart Services
In case we want, apply the following commands from the codebase folder.

```bash
# stop
make stop

# restart
make stop && make start
```

## Redeploy `.env` and DAGs
```bash
make stop && make init && make start
```

## Upgrade to the latest code
```bash
make upgrade && make stop && make init && make start
```

## Rebuild Docker Images
```bash
make stop && make build && make init && make start
```
