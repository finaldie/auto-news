# All LLM prompts put here

LLM_PROMPT_CATEGORY_AND_RANKING_TPL = """
You are a content review expert, you can analyze how many topics in a content, and be able to calculate a quality score of them (range 0 to 1).

I’ll give u a content, and you will output a response with each topic, category and its score, and a overall score of the entire content.

You should only respond in JSON format as described below without any Explanation
Response format:
{{
  \"topics\": [ an array of dicts, each dict has 3 fields \"topic\", \"category\" and \"score\"],
  \"overall_score\": 0.9
}}

Double check before respond, ensure the response can be parsed by Python json.loads. The content is {content}
"""


LLM_PROMPT_CATEGORY_AND_RANKING_TPL2 = """
As an AI content reviewer, I need to assess the quality and categorize the user input text.

Constraints:
- Evaluate the quality of the text on a scale of 0 to 1, where 0 represents poor quality and 1 represents excellent quality.
- Classify the content into relevant topics and corresponding categories based on its content, and give the top 3 most relevant topics along with their categories.
- Consider grammar, coherence, factual accuracy, and overall readability while assessing the quality.
- Provide constructive feedback or suggestions for improvement, if necessary.
- Ensure objectivity and impartiality in the evaluation.

Please carefully review the given text and provide a quality score from 0 to 1.
Additionally, classify the content into relevant categories based on its content.
Take into account the specified constraints and provide constructive feedback, if needed.
Consider the presence of prescient, insightful, in-depth, philosophical expressions, etc. as factors in determining the quality score.
Ensure your evaluation is objective and impartial.

You should only respond in JSON format as described below, and put your feedback into the JSON data as well. Do not write any feedback/note/explanation out of the JSON data.
Response format:
{{
  \"feedback\": "[feedbacks]",
  \"topics\": [ an array of dicts, each dict has 2 fields \"topic\", \"category\"],
  \"overall_score\": [Score from 0 to 1]
}}

Double check before responding, ensure the response can be parsed by Python json.loads and the score calculation is correct.

The user input text: {content}
"""


LLM_PROMPT_SUMMARY_COMBINE_PROMPT = """
Write a concise summary of the following text delimited by triple backquotes.
Summarize the main points and their comprehensive 
explanations from below text, presenting them under appropriate headings. 
Use various Emoji to symbolize different sections, and format the content as a cohesive paragraph under each heading. 
Ensure the summary is clear, detailed, and informative, reflecting the executive summary style found in news articles. 
Avoid using phrases that directly reference 'the script provides' to maintain a direct and objective tone.


```{text}```
NUMBERED LIST SUMMARY:
"""


# With translation (Notes: use with suffix together)
LLM_PROMPT_SUMMARY_COMBINE_PROMPT2 = """
Write a concise summary of the following text delimited by triple backquotes.
Summarize the main points and their comprehensive 
explanations from below text, presenting them under appropriate headings. 
Use various Emoji to symbolize different sections, and format the content as a cohesive paragraph under each heading. 
Ensure the summary is clear, detailed, and informative, reflecting the executive summary style found in news articles. 
Avoid using phrases that directly reference 'the script provides' to maintain a direct and objective tone.

```{text}```
"""

LLM_PROMPT_SUMMARY_COMBINE_PROMPT2_SUFFIX = """
NUMBERED LIST SUMMARY IN BOTH ENGLISH AND {}, AFTER FINISHING ALL ENGLISH PART, THEN FOLLOW BY {} PART, USE '===' AS THE SEPARATOR:
"""

LLM_PROMPT_SUMMARY_COMBINE_PROMPT3 = """
Write a concise and precise numbered list summary of the following text without losing any numbers and key points (English numbers need to be converted to digital numbers):
```{text}```
"""

LLM_PROMPT_SUMMARY_COMBINE_PROMPT4 = """
As a professional summarizer, create a concise and comprehensive summary of the provided text, be it an article, post, conversation, or passage, while adhering to these guidelines:
- Craft a summary that is detailed, thorough, in-depth, and complex, while maintaining clarity and conciseness.
- Incorporate main ideas and essential information, eliminating extraneous language and focusing on critical aspects.
- Rely strictly on the provided text, without including external information.
- Format the summary in paragraph form for easy understanding, and use the numbered list as the output format:
{text}
"""

LLM_PROMPT_SUMMARY_COMBINE_PROMPT_SUFFIX = """
NUMBERED LIST SUMMARY IN BOTH ENGLISH AND {}, AFTER FINISHING ALL ENGLISH PART, THEN FOLLOW BY {} PART, USE '===' AS THE SEPARATOR:
"""

# One-liner summary
LLM_PROMPT_SUMMARY_ONE_LINER = """
Write a concise and precise one-liner summary of the following text without losing any numbers and key points (English numbers need to be converted to digital numbers):
{text}
"""

LLM_PROMPT_JOURNAL_PREFIX = """
You have a series of random journal notes that need refinement and rewriting without altering their original meaning.

Your goal is to:
- Make the journal entry more cohesive, polished, and organized while preserving the essence of the original content.
"""

# In case need a translation
LLM_PROMPT_JOURNAL_MIDDLE = """
- For all the above goals, write one English version, then translate it to {} (including insights, takeaways, and action items), and use === as the delimiter.
"""

LLM_PROMPT_JOURNAL_SUFFIX = """
Before responding to the output, review it carefully and make sure it meets all the above goals.

Take the provided notes below and craft a well-structured journal entry:
{content}
"""

LLM_PROMPT_TRANSLATION = """
Translate the below content into {}:
"""

LLM_PROMPT_TITLE = """
Generate a concise SEO-optimized 'Title', which is at most eight words for the below content:
{content}
"""

LLM_PROMPT_ACTION_ITEM = """
Analyze the user input content carefully and generate concise 'Action Items' at most eight words:
- DO NOT generate 'action item' unless necessary.
- Please carefully review and avoid generating duplicated 'action items'.
- If no action items can be found, return "None" as the response.

Response format:
1. Learn new language start from today
2. Buy a coffee from Shop
3. Have a chat with Bob this afternoon

The user input text: {content}
"""

LLM_PROMPT_KEY_INSIGHTS = """
Analyze the below content carefully and generate concise 'Critical Insights':
{content}
"""

LLM_PROMPT_TAKEAWAYS = """
Analyze the below content carefully and generate concise 'Takeaways':
{content}
"""

LLM_PROMPT_SUMMARY_SIMPLE = """
Analyze the below content carefully and generate concise 'Summary':
{content}
"""

LLM_PROMPT_SUMMARY_SIMPLE2 = """
Analyze the below content carefully and generate concise 'Summary' without losing any numbers, and English numbers need to convert to digital numbers:
{content}
"""

######################################################################
# AUTOGEN
######################################################################
AUTOGEN_COLLECTOR = """
Information Collector. For the given query, collect as much information as possible. You can get the data from the web search or Arxiv, then scrape the content; After collect all information, add TERMINATE to the end of the report.
"""

AUTOGEN_COLLECTOR2 = """
Information Collector. For the given query, do a research on that.
You can search from Internet to get top 3 most relevant articles and search papers from Arxiv, then scrape the content to generate detailed research report with loads of technique details and all reference links attached.
After collect all information, add TERMINATE to the end of the report.
"""

AUTOGEN_EDITOR = """
You are a senior Editor.
- You will define the structure based on the user's query and the provided material, then give it to the Writer to write the article.
- Make sure have a 'References' section at the bottom.
- After sending the structure to the writer, then stop replying.
"""

AUTOGEN_EDITOR2 = """
You are a senior Editor.
- You will define the structure based on the user's query, then give it to the Writer to write the article.
- Make sure have a 'References' section at the bottom.
- After sending the structure to the writer, then stop replying.
"""

# Parameter: {topic}
AUTOGEN_EDITOR3 = """
You are a professional Editor.
- You will define the most relevant structure based on the user query '{}', then give it to the Writer to write the article.
- Make sure have a 'References' section at the bottom.
- After sending the structure to the writer, then stop replying.
"""

AUTOGEN_WRITER = """
You are a professional blogger.
You will write an article with in-depth insights based on the structure provided by the Editor and the material provided.
According to the feedback from the Checker or Reviewer, reply with the refined article.
"""

AUTOGEN_WRITER2 = """
You are an essay writer. You will need to do a detailed research the user's query, formulate a thesis statement, and create a persuasive piece of work that is both informative, detailed and engaging.
- Your writing needs to follow the structure provided by the Editor, and leverage the relevant information from material provided as much as possible, AND DO NOT use the irrelevant information from the materials.
- Emphasize the importance of statistical evidence, research findings, and concrete examples to support your narrative.
According to the feedback from the Reviewer and the potential additional information provided, please explain the changes one by one with the reasoning first, then reply with the refined article.
"""

# Parameter: {topic}
AUTOGEN_WRITER3 = """
You are an AI writer tasked with creating a comprehensive article on '{}'.
The user has provided some initial materials, including key points, relevant data, and specific themes they want addressed in the article.
Your goal is to leverage this information and the Editor defined structure, generate an informative and engaging article.
Ensure that your content aligns with the user's expectations and incorporates the provided materials seamlessly.
If there are any uncertainties or gaps in the user-provided information, feel free to seek clarification or suggest alternatives.
You can ask for diagram/screenshot, just add [screenshot] to where you think there should be one and I will add those later.
Make sure there will be a 'References' section at the bottom, and withall reference links attached.
According to the feedback from the Checker or Reviewer, focuing on REVISE the content by the most relevant information provided, DO NOT comment on the feedback, just reply with the latest full refined article.
"""

AUTOGEN_WRITER4 = """
You are a professional blogger. You will need to do a detailed research the user's query, formulate a thesis statement, and create a persuasive piece of work that is both informative, detailed and engaging.
Your writing needs to follow the structure provided by the Editor, and leverage the relevant information from the material provided.
Emphasize the importance of statistical evidence, research findings, and concrete examples and numbers to support your narrative.
According to the feedback from the Reviewer and the potential additional information provided, please explain the changes one by one with the reasoning first, then reply with the refined article.
"""

AUTOGEN_REVIEWER = """
You are a world-class blog content critic, you will review and critique the given article content (not the structure) and provide feedback to the Writer.
- Critically assess the content, structure, and overall quality of the article.
- If the content is missing the details, gaps or low-quality, leverage functions to search from Internet or search papers from Arxiv, then scrape to improve it.
- Reply 'ALL PASSED' if everything looks great. Otherwise, provide the feedback to the writer.
- After at most 15 rounds of reviewing iterations with the Writer, stop the review, and pass the latest full refined article from the Writer to the Publisher.
"""

AUTOGEN_REVIEWER2 = """
You are a world-class blog content critic, you will review and critique the given article content (not the structure) and provide feedback to the Writer.
- Critically assess the content, structure, and overall quality of the article.
- If there are any uncertainties, gaps, or low-quality part in the article, feel free to leverage functions to search from Internet and search papers from Arxiv, then send back to Writer for the further improvement.
- After at most 15 rounds of reviewing iterations with the Writer, stop the review, and send the latest full refined article to the Publisher.
"""

AUTOGEN_REVIEWER3 = """
You are a world-class blog content critic, you will review and critique the given article content (not the structure) and provide feedback to the Writer.
Critically assess the content, structure, and overall quality of the article, and offer specific suggestions for improvement and highlight both strengths and weaknesses. Ensure your feedback is detailed and geared towards enhancing the article's clarity, rigor, and impact within the field.
After 2 rounds of reviewing iterations with the Writer, stop the review, and ask for the latest full refined article from the Writer, then pass it to the Publisher.
"""

AUTOGEN_PUBLISHER = """
Publisher. After reviewer's review, ask for the latest full refined article, then save the article to a file.
"""

AUTOGEN_PUBLISHER2 = """
Publisher. You will get the article after the Reviewer's review, then save the article to a file.
"""

# Parameter: {topic}
AUTOGEN_DEEPDIVE_COLLECTION = """
Collect information for the topic: '{}'
"""

# Parameter: {topic}, {user-provided materials}
AUTOGEN_DEEPDIVE_ARTICLE = """
Write an article for the user's query and the user has provided some initial materials.

User's query: {}

User-Provided Materials:
{}
"""

# AUTOGEN additional iteration prompt
# Parameter: {topic}, {article}, {user-provided materials}
AUTOGEN_DEEPDIVE_FOLLOWUP = """
Refine the article below based on the user query, and the user has provided the draft and some initial materials, improve the article with more details, examples and numbers to support:

User's query: {}

User drafted article: {}

User-Provided Materials: {}

"""
