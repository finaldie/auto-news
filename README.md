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
- UI
  - [x] Cross-platform (Web browser, iOS/Android app)  

# Installation
## Preparison
* [Required] Notion token ([Integration](https://www.notion.so/my-integrations))
* [Required] OpenAI token
* [Required] Docker
* [Optional] Notion web clipper browser extension
* [Optional] Twitter token

## Create Notion Entry Page

Go to [Notion](https://www.notion.so/), create a page (For example `Readings`) and enable notion `Integration` for this page

## Create Environment File
Copy `.env.template` to `build/.env`, and fill up the environment vars:
* `NOTION_TOKEN`: The `Integration` token
* `NOTION_ENTRY_PAGE_ID`: Notion page id
* `OPENAI_API_KEY`
* [Optional] Vars with `TWITTER_` prefix

## Start Services
```bash
make build
make start
```

Now, the services are up and running, it will pull sources every hour.

## Set up Notion Tweet and RSS list

Go to notion page we created before, we would see the following folder structure has been created automatically:
```bash
Reading
├── inbox
│   ├── Inbox-Article
│   └── Inbox-YouTube
├── index
│   ├── Index-Inbox
│   ├── Index-ToRead
│   ├── RSS_List
│   └── Tweet_List
└── toread
    └── ToRead
```

- Go to `RSS_List` page, and fill the RSS name and URL
- Go to `Tweet_List` page, and fill the Tweet screen names


## Set up Notion database views
Go to Notion, and create the database views for different sources, e.g. Tweets, Articles, YouTube, RSS, etc

## Control Panel
For troubleshooting, we can use the URLs below to access the services and check the logs and data

| Service | Responsibility  | Panel URL             |
| ---     | ---             | ---                   |
| Airflow | Orchestration   | http://localhost:8080 |
| Milvus  | Vector Database | http://localhost:9100 |
