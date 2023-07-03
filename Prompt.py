{
  "model": "gpt-3.5-turbo",
  "messages": [
    {
      "role": "system",
      "content": "You are an AI trained to process and update regulation data chunks. If an incoming update data chunk corresponds appropriately to any segment within the original regulation data chunk, perform the update. If the update data chunk doesn't align or isn't compatible, keep the original regulation data chunk as is."
    },
    {
      "role": "user",
      "content": "Here is the original regulation data chunk: <Insert Original 4000 tokens data chunk>"
    },
    {
      "role": "user",
      "content": "Here is the update data chunk: <Insert 4000 tokens update data chunk>"
    },
    {
      "role": "user",
      "content": "Please compare the update data chunk with the original regulation data chunk and perform an update if appropriate. Return the resultant data chunk."
    }
  ],
  "options": {
    "use_cache": False,
    "max_tokens": 4000
  }
}
