#A small command-line tool that  calls a free public API, gets a JSON and then calls Claude API to format it

import requests
import sys
import os
from dotenv import load_dotenv
import anthropic

load_dotenv()
API_KEY = os.getenv("API_KEY")  # pull the key
MODEL_NAME = os.getenv("MODEL_NAME") #pull model name


def main():
    if len(sys.argv) != 2: #need to pass the name of the cryptocurrency, just 1
        sys.exit("Coin denomination missed or incorrect number of arguments")

    data = get_coin_data(sys.argv[1])#getting the JSON info
    prompt, system_prompt = get_prompt(data)

    output = get_completion(prompt, system_prompt)

    print(output)

def get_coin_data(coin_id):#getting the data for the selected coin
    try:
        response = requests.get(f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={coin_id}")
        return response.json()#returning the raw JSON so it can be passed to the IA for its formatting

    except (requests.RequestException):
        sys.exit("Please try a bit later")

def get_prompt(_data):#create prompt
    # System prompt
    SYSTEM_PROMPT = "You are a JSON expert"
    # Prompt
    PROMPT = f"Can you take this JOSN: {_data} and format it in a more legible way? the final user does not know anything about JSON so the output data should be clear and easy to understand"

    return PROMPT, SYSTEM_PROMPT

def get_completion(prompt: str, system_prompt=""):#call Clause with the apropriate prompt to get the JSON formated
    client = anthropic.Anthropic(api_key=API_KEY)
    message = client.messages.create(
        model=MODEL_NAME,
        max_tokens=2000,
        system=system_prompt,
        messages=[
          {"role": "user", "content": prompt}
        ]
    )
    return message.content[0].text


if __name__ == "__main__":
    main()
