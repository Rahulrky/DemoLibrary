import nltk
import pandas as pd
import tiktoken
import requests

from openai.embeddings_utils import distances_from_embeddings, cosine_similarity
from langchain.text_splitter import NLTKTextSplitter
from PyPDF2 import PdfReader

nltk.download('punkt')

def chunks_and_embeddings(path):
    """
    Create Chunks from the input PDF
    """
    global pdf_read_list, faiss_idx_list, len_chunks_n
    pdf_read_list = []
    faiss_idx_list = []
    text=''
    pdf_reader = PdfReader(path)

    for page in pdf_reader.pages:
        text += page.extract_text()

    text_splitter_nltk = NLTKTextSplitter(chunk_size=500)

    chunks_n=text_splitter_nltk.split_text(text)

    return chunks_n


def embed_text(text):
    """
    Function to process each text sentence to embedding
    """

    # Request payload
    payload = {
        "input": text
    }

    # Azure OpenAI API endpoint
    url_embed = "https://btg-ai-nlp-ins.openai.azure.com/openai/deployments/text-embedding-ada-002/embeddings?api-version=2022-12-01"

    # Request headers
    headers_embed = {
        "Content-Type": "application/json",
        "api-key": "5ce8958a8f6f47bcbd2da82cdf8ee7bb",
    }

    # Send POST request
    response = requests.post(url_embed, headers=headers_embed, json=payload)

    # Check response status
    if response.status_code == 200:
        # Get the embedding
        embedding = response.json()["data"][0]["embedding"]
        return embedding
    else:
        print("Request failed with status code:", response.status_code)
        print("Response body:", response.text)
        return None
    

def create_context(question, df, max_len=2000, size="ada"):
    """
    Create a context for a question by finding the most similar context from the dataframe
    """

    # Get the embeddings for the question
    q_embeddings = embed_text(question)

    # Get the distances from the embeddings
    df['distances'] = distances_from_embeddings(q_embeddings, df['embedding'].values, distance_metric='cosine')

    returns = []
    cur_len = 0
    sec_cnt = 0

    # Sort by distance and add the text to the context until the context is too long
    for i, row in df.sort_values('distances', ascending=True).iterrows():

        # Add the length of the text to the current length
        cur_len += row['n_tokens'] + 4

        # If the context is too long or number of sections more than 5, break
        if cur_len > max_len:
            break
        elif sec_cnt > 5:
            break

        # Else add it to the text that is being returned
        returns.append(row["section_id"] + ":" + row["text"])
        sec_cnt += 1

    return "\n###\n".join(returns)


def reference_generator(prompt: str, temperature: int = 0) -> str:
        """
        Reference Generator
        """
        headers = {
            'Content-Type': 'application/json',
            'api-key': '5ce8958a8f6f47bcbd2da82cdf8ee7bb',
        }
        params = {
            'api-version': '2023-03-15-preview',
        }
        json_data = {
            "messages": [
                {"role": "user", "content": str(prompt)},
            ],
            "temperature" : temperature
        }
        # url_prompt = 'https://btg-ai-nlp-ins.openai.azure.com/openai/deployments/gpt-35-turbo/chat/completions'
        url_prompt = 'https://btg-ai-nlp-ins.openai.azure.com/openai/deployments/gpt-35-turbo-16k/chat/completions'

        response = requests.post(url_prompt,
            params=params,
            headers=headers,
            json=json_data,
            verify=False,
        )

        result = eval(response.text.replace("null", "''"))
        return result["choices"][0]["message"]["content"]

def factual_main(path, user_prompt):

    text_chunks = chunks_and_embeddings(path)
    # Convert the list to a DataFrame
    df = pd.DataFrame(text_chunks, columns=['text'])

    # Load the cl100k_base tokenizer which is designed to work with the ada-002 model
    tokenizer = tiktoken.get_encoding("cl100k_base")

    # Tokenize the text and save the number of tokens to a new column
    df['n_tokens'] = df.text.apply(lambda x: len(tokenizer.encode(x)))

    # add a new column called section_id
    df['section_id'] = ['sec_' + str(i) for i in range(1, len(df)+1)]

    # Apply the processing function to the 'text' column using .apply()
    df['embedding'] = df['text'].apply(embed_text)

    context = create_context(user_prompt, df, max_len=2000, size="ada",)

    prompt=f'''Answer the question  based on the article below. Answer must contain text from the article only. If the question can't be answered from the text in the article, then tell the user that you don't know. \
article: {context} \
Question: {user_prompt} \
Provide the response in below format.
"Answer": str \
"article_id": str \
"article_text": str \
'''
    try:
        reference = reference_generator(prompt=prompt)
    except Exception as e:
        reference = ""
    return reference


if __name__ == "__main__":
    prompt = "What are the hallucination updates?"
    path = r"C:\Users\Rahul\Workspace\GenAI Guardrails\Update for Guardrails Implementation for GenAI.pdf"
    print(factual_main(path=path, user_prompt=prompt))