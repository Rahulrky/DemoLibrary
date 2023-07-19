import openai
import concurrent.futures

openai.api_key = 'your-api-key'

def create_chat(i):
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": f"Help me with task number {i}"}
    ], i

def call_openai(chat):
    messages, i = chat
    return i, openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )

chats = [create_chat(i) for i in range(1, 11)]  # start chats from 1

with concurrent.futures.ThreadPoolExecutor() as executor:
    responses = dict(executor.map(call_openai, chats))

for key, response in responses.items():
    print(f"Chat {key} response: {response.choices[0].message['content']}")
