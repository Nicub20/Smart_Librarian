from openai import OpenAI

client = OpenAI()

response = client.responses.create(
    model="gpt-4.1-nano",
    #STANDARD:  input="Write a one-sentence bedtime story about a unicorn."
    input = [
    {"role": "system", "content": "You are a professional writter and an expert chef in cooking romanian recipies."},
    {"role": "user", "content": "Give me 5 romanian recipes that are delicious and relative easy to make"},
    ],
    temperature=0.2,
    max_output_tokens=300,
)

print(response.output_text)