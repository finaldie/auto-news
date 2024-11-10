# Auto-News: An Automatic News Aggregator with LLM

[![GitHub Build](https://github.com/finaldie/auto-news/actions/workflows/python.yml/badge.svg)](https://github.com/finaldie/auto-news/actions)
![Kubernetes](https://img.shields.io/badge/kubernetes-%23326ce5.svg?style=Flat&logo=kubernetes&logoColor=white)
![ChatGPT](https://img.shields.io/badge/chatGPT-74aa9c?style=Flat&logo=openai&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google%20Gemini-8A2BE2?style=Flat&logo=googlegemini&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-8A2BE2?style=Flat&logo=ollama&logoColor=white)
![Notion](https://img.shields.io/badge/Notion-%23000000.svg?style=Flat&logo=notion&logoColor=white)
![Helm](https://img.shields.io/badge/Helm-0F1689?style=Flat&logo=Helm&labelColor=0F1689)
[![iOS](https://img.shields.io/itunes/v/6481704531)](https://apps.apple.com/app/dots-agent/id6481704531)
[![Android](https://img.shields.io/badge/Google_Play-v1.1.2-blue)](https://play.google.com/store/apps/details?id=com.dotsfy.dotsagent)

The ultimate personal productivity content aggregator: Designed to effortlessly navigate and maximize your efficiency in the AI era.

## Use Cases

1. [x] **Super busy but still wants to catch the trends in a few minutes?** `Yes`
2. [x] **Want to be a super individual, to handle vast amounts of information in the GenAI world?** `Yes`
3. [x] **Become a super executor, tell less, and achieve more?** `Yes`

With `auto-news` you'll get:
- `Faster learning:` Navigate trends and catch up in minutes.
- `Recap reinforcement:` Smooth and periodic memory recall.
- `Intelligent actions:` Route actions with a single message.

In the AI era, speed and productivity are extremely important. We need AI tools to help us talk less and achieve more!

For more background, see this [Blog post](https://finaldie.com/blog/auto-news-an-automated-news-aggregator-with-llm/) and these videos [Introduction](https://www.youtube.com/watch?v=hKFIyfAF4Z4), [Data flows](https://www.youtube.com/watch?v=WAGlnRht8LE).

[<img src="https://img.youtube.com/vi/hKFIyfAF4Z4/0.jpg" width="80%" />](https://www.youtube.com/watch?v=hKFIyfAF4Z4 "AutoNews Intro on YouTube")

## Features
- Aggregate feed sources (including RSS, Reddit, Tweets, etc), and proactive generate with insights
- Generate insights of YouTube videos (Do transcoding if no transcript provided)
- Generate insights of Web Articles
- Filter content based on personal interests and remove 80%+ noises
- Weekly Top-k Recap
- Unified and central reading experience (RSS reader-like style, Notion-based)
- Generate `TODO` list from takeaways and journal notes
- Organize Journal notes with insights daily
- [Multi-Agents] **Experimental** [Deepdive](https://github.com/finaldie/auto-news/wiki/Deepdive-(Experimental)) topic via web search agent and [autogen](https://github.com/microsoft/autogen)
- Multi-LLM backend: OpenAI ChatGPT, Google Gemini, Ollama

<img src="https://github.com/finaldie/auto-news/assets/1088543/778242a7-5811-49e1-8982-8bd32d141639" width="80%" />

## Documentation
https://github.com/finaldie/auto-news/wiki

## Installation
### :star: :star: Managed Solution :star: :star:
Great News! Now we have the in-house managed solution, it is powered by the `auto-news` as the backend. It supports the [Web version](https://dots.dotsfy.com/) and the mobile Apps, download it from `App Store` or `Google Play`, install and enjoy. It is the **quickest** and **easiest** solution for anyone who doesn't want to/or does not have time to set up by themselves. (**Notes:** _App is available in US and Canada at this point_)

<img src="https://github.com/finaldie/auto-news/assets/1088543/3b072078-17eb-4f1d-b301-75bc8295479c" width="80%" />

For more details, please check out the [App official website](https://dotsfy.com/dots-agent/). Click below to install the App directly:

* [Web version (Beta)](https://dots.dotsfy.com/)
* [![iOS](https://img.shields.io/itunes/v/6481704531)](https://apps.apple.com/app/dots-agent/id6481704531)
* [![Android](https://img.shields.io/badge/Google_Play-v1.1.2-blue)](https://play.google.com/store/apps/details?id=com.dotsfy.dotsagent)

### Self-Hosted
The client is using [Notion](https://www.notion.so/), and the backend is fully `self-hosted` by ourselves.

#### Backend System Requirements
| Component | Minimum      | Recommended  |
| --------- | -----------  | ----         |
| OS        | Linux, MacOS | Linux, MacOS |
| CPU       | 2 cores      | 8 cores      |
| Memory    | 6GB          | 16GB         |
| Disk      | 20GB         | 100GB        |

#### Docker-compose
- [Installation using Docker-compose](https://github.com/finaldie/auto-news/wiki/Docker-Installation)
- [Installation using Portainer](https://github.com/finaldie/auto-news/wiki/Installation-using-Portainer)

#### Kubernetes
- [Installation using Helm](https://github.com/finaldie/auto-news/wiki/Installation-using-Helm)
- [Installation using ArgoCD](https://github.com/finaldie/auto-news/wiki/Installation-using-ArgoCD)

## Issues/Questions?
Feel free to open an issue and start the conversation.
