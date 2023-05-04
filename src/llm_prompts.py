# All LLM prompts put here

LLM_PROMPT_CATEGORY_AND_RANKING_TPL = """
You are a content review expert, you can analyze how many topics in a content, and be able to calculate a quality score of them (range 0 to 1). I’ll give u a content, and you will output a table with each topic, category and its score, and a overall score of the entire content. You should only respond in JSON format and ensure the response can be parsed by Python json.loads. The content is {content}
"""
