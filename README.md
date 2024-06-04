# Auto-News: An Automatic News Aggregator with LLM

[![GitHub Build](https://github.com/finaldie/auto-news/actions/workflows/python.yml/badge.svg)](https://github.com/finaldie/auto-news/actions)
![Kubernetes](https://img.shields.io/badge/kubernetes-%23326ce5.svg?style=Flat&logo=kubernetes&logoColor=white)
![ChatGPT](https://img.shields.io/badge/chatGPT-74aa9c?style=Flat&logo=openai&logoColor=white)
![Notion](https://img.shields.io/badge/Notion-%23000000.svg?style=Flat&logo=notion&logoColor=white)
![Helm](https://img.shields.io/badge/Helm-0F1689?style=Flat&logo=Helm&labelColor=0F1689)
[![iOS](https://img.shields.io/itunes/v/6481704531)](https://apps.apple.com/app/dots-agent/id6481704531)
[![Android](https://img.shields.io/badge/Google_Play-v1.1.2-blue)](https://play.google.com/store/apps/details?id=com.dotsfy.dotsagent)

A personal news aggregator to pull information from multi-sources + LLM (ChatGPT) to help us read efficiently with less noise, the sources including Tweets, RSS, YouTube, Web Articles, Reddit, and random Journal notes.

## Why need it?
In the world of this information explosion, we live with noise every day, it becomes even worse after the generative AI was born. Time is a precious resource for each of us, How to use our time more efficiently? It becomes more challenging than ever.

Also, think about how much time we spent on pulling/searching/filtering content from different sources, how many times we put the article/paper or long video as a side tab, but never got a chance to look at, and how much effort to organize the information we have read. We need a better way to get rid of the noises, focus on reading the information efficiently based on our interests, and stay on track with the goals we defined.

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

<img src="https://github.com/finaldie/auto-news/assets/1088543/778242a7-5811-49e1-8982-8bd32d141639" width="80%" />

## Documentation
https://github.com/finaldie/auto-news/wiki

## Installation
### :star: :star: Managed Solution :star: :star:
Great News! Now we have the in-house managed solution, it is powered by the `auto-news` as the backend. For the client App, download it from `App Store` or `Google Play`, install and enjoy. It is the **quickest** and **easiest** solution for anyone who doesn't want to/or does not have time to set up by themselves. (**Notes:** _App is available in US and Canada at this point_)

<img src="https://github.com/finaldie/auto-news/assets/1088543/3b072078-17eb-4f1d-b301-75bc8295479c" width="80%" />

For more details, please check out the [App official website](https://dotsfy.com/dots-agent/). Click below to install the App directly:

* [![iOS](https://img.shields.io/itunes/v/6481704531)](https://apps.apple.com/app/dots-agent/id6481704531)
* [![Android](https://img.shields.io/badge/Google_Play-v1.1.2-blue)](https://play.google.com/store/apps/details?id=com.dotsfy.dotsagent)

### Self-Hosted
The client is using [Notion](https://www.notion.so/), and the backend is fully `self-hosted` by ourselves.

#### Backend System Requirements
| Component | Minimum Requirements | Recommended  |
| --------- | -----------          | ----         |
| OS        | Linux, MacOS         | Linux, MacOS |
| CPU       | 2 cores              | 8 cores      |
| Memory    | 6GB                  | 16GB         |
| Disk      | 20GB                 | 100GB        |

#### Docker-compose
- [Installation using Docker-compose](https://github.com/finaldie/auto-news/wiki/Docker-Installation)

#### Kubernetes
- [Installation using Helm](https://github.com/finaldie/auto-news/wiki/Installation-using-Helm)
- [Installation using ArgoCD](https://github.com/finaldie/auto-news/wiki/Installation-using-ArgoCD)

## Issues/Questions?
Feel free to open an issue and start the conversation.
