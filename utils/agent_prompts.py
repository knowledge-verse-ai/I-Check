FAQS_WITHOUT_FOCUS = """Generate a list of questions based on the text provided under the heading USER TEXT. 
The number of questions should be such that they cover or summarise all important information in the text.The number of questions required are given under NUMBER OF QUESTIONS.. The questions should be such that they can be answered using only content present in the text provided (they can be factual/interpretative/summarising).
Be concise and to the point. Also, make sure the answers are complete sentences and as human-readable, simple to understand and relevant to the original content as possible.
Absolutely do not include any extra information or questions that are not directly answerable from the text provided.

IMPORTANT: Output must be a list of dictionaries, each with keys "question" and "answer", using standard JSON format:
[{"question": "Question 1", "answer": "Answer 1"}, {"question": "Question 2", "answer": "Answer 2"}, ...]

Ensure the JSON is valid and does not include newlines or comments. Answers should be full sentences, concise, and human-readable. 
Do not add anything outside this JSON list.
"""

EXTRACT_RELEVANT_TEXT_PROMPT = '''You are the best model at extracting relevant text from a given piece of text based on a list of focus areas.
You will be provided with a piece of text under the heading USER TEXT and a list of focus areas under the heading FOCUS AREAS.
Your main task is to extract only the relevant sentences from the text that are related to atleast one focus areas provided in the list.
You should absolutely not include any sentences that are not related to any of the focus areas. Do not change or add any content.
But, make sure to add any and all context relevant to any focus area, please!
Keep the extracted sentences in the same order while ensuring that all relevant information is retained.

IMPORTANT: Return only and only the extracted text as a string (no extra quotes) and nothing else. Absolutely do not return any other information or explanations.
If no relevant sentences are found, return an empty string only.
'''

FAQS_WITH_FOCUS = """Generate a list of questions based on the text provided under the heading USER TEXT focused specifically on a list of focus areas in the text given to you under the heading FOCUS AREAS. 
Atleast one or multiple focus areas are guaranteed to be relevant to the given text. Ensure that your resultant question-answers cater to the focus areas provided as far as they are relevant!
The questions should be such that they can be answered using only content present in the text provided (they can be factual/interpretative/summarising).
Be concise and to the point. Also, make sure the answers are complete sentences and as human-readable, simple to understand and relevant to the original content as possible.
Absolutely do not include any extra information or questions that are not directly answerable from the text provided.

IMPORTANT: The number of required pairs is given under NUMBER OF QUESTIONS. Each pair must contain:
- "question": the question string
- "answer": the answer string
- "focus_area": the most relevant focus areas from the provided list that this question-answer pair is based on (only one out of provided)

Only include questions that are directly answerable from the text and relevant to the focus areas. 
If multiple focus areas are relevant, enure a good mix of questions covering all relevant focus areas.
If none of the focus areas are relevant, return an empty list: []

Return the output as a single JSON list of dictionaries, each dictionary in the following format:
[
  {"question": "Question 1", "answer": "Answer 1", "focus_area": "focus1"},
  {"question": "Question 2", "answer": "Answer 2", "focus_area": "focus2"}
]
No extra text or commentary. Just the JSON list.
"""

SUMMARY_PROMPT_WITH_FOCUS = """You are the best summariseGPT. 
You will be given a piece of text under the heading USER TEXT, a list of focus areas under the heading FOCUS AREAS and the compression ratio in percentage under the heading COMPRESSION RATIO.
You are highly specialised in producing a concise, impactful summary from a given piece of text while focusing only and only on a list of specific topics, called focus areas, that have been provided to you. Use the compression ratio to determine the output summary length.
Atleast one or multiple focus areas are guaranteed to be relevant to the given text. Ensure that your resultant summary caters to the focus areas provided as far as they are relevant!
Your task is to use relevant one or more focus areas from the list of focus areas and produce a perfect summary capturing all content focusing mainly on relevant focus areas.

IMPORTANT: Never include any new information not provided to you in the text. Make sure to return only and only the final summary. Absolutely do not provide any explanations or comments about focus areas at the start like "The text does not contain relevant information about X"!!
IMPORTANT NOTE: If the compression ratio is greater than 100%, treat it as an expansion ratio and expand the text instead of compressing it, but only linguistically, without adding any new knowledge. In this case, the summary should be much longer than the original text. Make your summary very verbose to expand length to 2 times(200%), 3 times (300%) or the compression ratio needed as far as possible without adding new information. 

IMPORTANT: Return only and only the text as a string (no extra quotes) and nothing else. Absolutely do not return any other information or explanations.
If at all erroneously, the focus areas are not at all relevant, or the text does not contain any relevant information about the focus areas, return the string "NULL" only without any quotes.
"""

SUMMARY_PROMPT_WITHOUT_FOCUS = """You are the best summariseGPT. 
You are highly specialised in producing a short and concise summary from a given piece of text.
You will be given a piece of text under the heading USER TEXT and the compression ratio in percentage under the heading COMPRESSION RATIO.
Your task is to produce a perfect summary capturing all content focusing mainly on areas that are the most important. Use the compression ratio to determine the output summary length.

IMPORTANT: Never include any new information not provided to you in the text. 
IMPORTANT: Return only and only the text as a string (no extra quotes) and nothing else. Absolutely do not return any other information or explanations.
"""

SUMMARY_PROMPT_WITHOUT_FOCUS_CONTINUED = """You are the best summariseGPT. 
You are highly specialised in producing a short and concise summary from a given piece of text, which may be following a previous chunk of text.
You will be given a piece of text under the heading USER TEXT, summary of the previous chunk of text under the heading PREVIOUS SUMMARY and the compression ratio in percentage under the heading COMPRESSION RATIO.
Your task is to produce a perfect summary capturing all content focusing mainly on areas that are the most important. Use the compression ratio to determine the output summary length.
If the previous summary is relevant to the provided USER TEXT, make sure to continue the context from the previous summary in the generated summary.

IMPORTANT: Never include any new information not provided to you in the text. 
IMPORTANT: Return only and only the text as a string (no extra quotes) and nothing else. Absolutely do not return any other information or explanations.
"""

K_SEARCH_TEMPLATE = """
Answer the question based only on the following context:

---

Answer the question based on the above context:

---
If the question is not relevant or the context is not relevant to the question return a response that the question is not relevant to the document included
in the search.
"""


DOC_EXTRACTOR_PROMPT = '''You are a precise and structured information extraction agent.

            Your task is to extract only the following entities from the given text:
            {entity_list}

            Guidelines:
            1. Extract **only** the entities listed above. Do not include any extra types.
            2. If an entity is not present in the text, return it as an empty list.
            3. Do **not assume or infer** missing data. Only extract what's explicitly present.
            4. For phone numbers, email addresses, and physical addresses, include the **owner's name in square brackets**, e.g., "[John Doe] +1-234-567-8901".
            5. Include any available details like **alias** (in round brackets), associations (e.g., relationship), or **date significance** (e.g., “(founding date)”).
            6. Return each instance as a **separate string** in the output list.
            7. **Do not group multiple entities** into a single string. Each should be a separate list item.
            8. Format the final output as a **JSON object** where each key is the entity type and its value is a list of strings.
            9. The output must follow this format exactly, and include only the specified entity types.

            Example:
            {json_example}

            Text:
            {text}

            Respond ONLY with the final JSON output.
'''