from openai import OpenAI
import configparser

config = configparser.ConfigParser()
config.read("config.ini")
api_key = config.get("API_KEYS", "OPENAI_API_KEY")

def call_llm(prompt: str, model: str = "gpt-4o") -> str:
    """
    Calls OpenAI's GPT-4o model with the given prompt, expecting a JSON response.

    Args:
        prompt (str): The full instruction to be sent.
        model (str): OpenAI model to use (default: gpt-4o).

    Returns:
        str: The raw JSON response from the model as a string.
    """
    openai_client = OpenAI(api_key=api_key)
    try:
                 
        response = openai_client.chat.completions.create(
                model=model,
                messages=[
                {
                    "role": "system",
                    "content": "You are a precise assistant. Always follow instructions exactly."
                },
                {
                    "role": "user",
                    "content": prompt
                }
                ],
                temperature=0.2,
            )
        content = str(response.choices[0].message.content).strip()
        return content

    except Exception as ex:
        print(f"[Unexpected Error] {ex}")
        return '{"answerable": false}'
