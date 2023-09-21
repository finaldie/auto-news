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
Return your response in numbered list which covers the key points of the text and ensure that a 5 year old would understand.

```{text}```
NUMBERED LIST SUMMARY:
"""


# With translation (Notes: use with suffix together)
LLM_PROMPT_SUMMARY_COMBINE_PROMPT2 = """
Write a concise summary of the following text delimited by triple backquotes.
Return your response in numbered list which covers the key points of the text and ensure that a 5 year old would understand.

```{text}```
"""

LLM_PROMPT_SUMMARY_COMBINE_PROMPT2_SUFFIX = """
NUMBERED LIST SUMMARY IN BOTH ENGLISH AND {}, AFTER FINISHING ALL ENGLISH PART, THEN FOLLOW BY {} PART, USE '===' AS THE SEPARATOR:
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
Analyze the user input content carefully and generate concise 'Action Items' at most eight words. Please carefully review and avoid generating duplicated 'action items'.

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
