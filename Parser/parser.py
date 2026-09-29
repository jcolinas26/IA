#Getting a text and parse it in JSON format so another fucntion can take it.

import requests
import sys
import os
from dotenv import load_dotenv
import anthropic
from datetime import date


load_dotenv()
API_KEY = os.getenv("API_KEY")  # pull the key
MODEL_NAME = os.getenv("MODEL_NAME") #pull model name


def main():
    try:
        input_data = input("Text: ")#to simplify the exercise, it will take text input from the user but this parser can be called from outside with the data
        if input_data == "":
            sys.exit("Data cannot be empty")#always require some input

        prompt, system_prompt = get_prompt(input_data)

        output = get_completion(prompt, system_prompt)

        print(output)#the output can be passed to other function like an inserto to a Data Base

    except (requests.RequestException):
         sys.exit("Error procesing the data")

def get_prompt(_data):#create prompt

    today = date.today().isoformat()   # getting today´s date to feed it in the prompt  
    # System prompt
    SYSTEM_PROMPT = "You are a JSON expert"
    # Prompt
    

    ######################################## COMBINE ELEMENTS ########################################
    INPUT_DATA = _data

    #giving a description about what is expected
    TASK_DESCRIPTION = """What to do:
            - Read the input text carefully.
            - Pull out only the fields listed under Output below.
            - If a field is missing from the text, use null. Do not guess or invent. 
            - Be sure to extract the due date from the text.
            - Return only the JSON object. No explanation, no markdown, no preamble."""

    TASK_CONTEXT = """Rules:
            - Every value must be traceable to something in the input text.
            - Dates in YYYY-MM-DD format. Numbers as numbers, not strings.
            - Today's date is {today}. Use exactly this for any "today" value.
            - The due date is in the future relative to {today}. If the text gives a day and month but no year, choose the nearest future year.
            - If the text is ambiguous, prefer null over a confident wrong answer."""

    EXAMPLES = """{
                    "invoice_id": 1,
                    "amount": 25.50,
                    "list_items": ["3 bananas"],
                    "today_date": 2026-09-26,
                    "due_date": 2027-03-30
                }"""


    TONE_CONTEXT = ""

    PRECOGNITION = ""

    IMMEDIATE_TASK = ""

    OUTPUT_FORMATTING = """Output: a JSON object with these fields:{
                    "invoice_id": string or null,
                    "amount": number or null,
                    "list_items": list of strings or empty list
                    "date": date
                    "due_date": date
                } do not include anything else appart form the JSON output"""

    PROMPT = ""

    if TASK_CONTEXT:
        PROMPT += f"""{TASK_CONTEXT}"""

    if TONE_CONTEXT:
        PROMPT += f"""\n\n{TONE_CONTEXT}"""

    if INPUT_DATA:
        PROMPT += f"""\n\n{INPUT_DATA}"""

    if EXAMPLES:
        PROMPT += f"""\n\n{EXAMPLES}"""

    if TASK_DESCRIPTION:
        PROMPT += f"""\n\n{TASK_DESCRIPTION}"""

    if IMMEDIATE_TASK:
        PROMPT += f"""\n\n{IMMEDIATE_TASK}"""

    if PRECOGNITION:
        PROMPT += f"""\n\n{PRECOGNITION}"""

    if OUTPUT_FORMATTING:
        PROMPT += f"""\n\n{OUTPUT_FORMATTING}"""

    return PROMPT, SYSTEM_PROMPT

def get_completion(prompt: str, system_prompt=""):#call Clause with the apropriate prompt to get the JSON formated
    client = anthropic.Anthropic(api_key=API_KEY)
    message = client.messages.create(
        model=MODEL_NAME,
        max_tokens=2000,
        system=system_prompt,
        messages=[
          {"role": "user", "content": prompt},
          {"role": "assistant", "content": "{"}
        ]
    )
    return message.content[0].text


if __name__ == "__main__":
    main()
