import os
from dotenv import load_dotenv
import anthropic
from simpleeval import simple_eval

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("API_KEY"))
MODEL_NAME = os.getenv("MODEL_NAME")


# 1. The actual function — the "hands"
def get_weather(city):
    return f"Sunny, 18°C in {city}"  # faked for now


def calculate(expression):
    # real math
    try:
        result = simple_eval(expression)
        return f"The result is {result}"
    except Exception:
        return "Sorry, I couldn't calculate that."


def search_notes(query):
    # look through a hardcoded dict
    notes = {"wifi password": "hunter2", "meeting": "3pm Thursday"}
    return notes.get(query, "No note found for that.")


# 2. The tool DEFINITION — what Claude reads to decide when/how to use it
tools = [
    {
        "name": "get_weather",
        "description": "Get the current weather for a given city. Use this whenever the user asks about weather, temperature, or conditions in a specific place.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "The city name, e.g. Bristol"}
            },
            "required": ["city"],
        },
    },
    {
        "name": "calculate",
        "description": "Get the calculacion of the expresion given by the user. Use this whenever the user asks for a mathematical operation",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression, e.g. What is the result of multiplying 3 by 4",
                }
            },
            "required": ["expression"],
        },
    },
    {
        "name": "search_notes",
        "description": "Search in the notes for something similar to what the user asks. Use this whenever the user asks for something related to notes",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Look for a note, e.g. Do I have any appointment?",
                }
            },
            "required": ["query"],
        },
    },
]

# 3. The loop
messages = []  # the whole conversation lives here, across all turns

while True:  # OUTER: one iteration per user turn
    user_input = input("You: ")
    if user_input.lower() in ("quit", "exit"):
        break
    messages.append({"role": "user", "content": user_input})

    while True:  # INNER: resolve tool calls for this turn
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=1024,
            tools=tools,
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            results = []
            for block in response.content:
                if block.type == "tool_use":
                    if block.name == "get_weather":
                        output = get_weather(block.input["city"])
                    elif block.name == "calculate":
                        output = calculate(block.input["expression"])
                    elif block.name == "search_notes":
                        output = search_notes(block.input["query"])
                    results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": output,
                        }
                    )
            messages.append({"role": "user", "content": results})
        else:
            break  # Claude gave a text answer — this turn is done

    # print Claude's final answer, and REMEMBER it in the conversation
    final = next(b.text for b in response.content if b.type == "text")
    print("Claude:", final)
    messages.append({"role": "assistant", "content": final})
