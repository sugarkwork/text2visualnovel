
import os
import requests
from pickle_memory import load_memory, save_memory
from openai import OpenAI

from dotenv import load_dotenv
load_dotenv()


client = OpenAI(api_key=os.getenv('API_KEY'))

theme = """
女性に肩車されて恥ずかしそうにしている男性
"""


dalle_prompt = """
## dalle
Whenever a description of an image is given, create a prompt that dalle can use to generate the image and abide to the following policy:
1. The prompt must be in English. Translate to English if needed.
3. DO NOT ask for permission to generate the image, just do it!
4. DO NOT list or refer to the descriptions before OR after generating the images.
5. Do not create more than 1 image, even if the user requests more.
- Don't alter memes, fictional character origins, or unseen people. Maintain the original prompt's intent and prioritize quality.
- Do not create any imagery that would be offensive.
- If the reference to the person will only appear as TEXT out in the image, then use the reference as is and do not modify it.
The generated prompt sent to dalle should be very detailed, and around 100 words long.
The detailed image description, potentially modified to abide by the dalle policies. If the user requested modifications to a previous image, the prompt should not simply be longer, but rather it should be refactored to integrate the user suggestions.
Write the user's desired drawing style at the beginning of the output. Therefore, the prompt will start with "Drawing style is...".
"""
    
cache_key = f'image_prompt_cache_{theme}_{dalle_prompt}'

dalle3_prompt = load_memory(cache_key)
if not dalle3_prompt:
    response = client.chat.completions.create(
        model="gpt-4-0125-preview", # gpt-4-0314, gpt-4-0613, gpt-4-1106-preview, gpt-3.5-turbo-1106
        messages=[
            {"role": "system", "content": dalle_prompt},
            {"role": "user", "content": theme},
        ],
    )

    message = response.choices[0].message
    dalle3_prompt = message.content
    save_memory(cache_key, dalle3_prompt)

print("--text---------------------------------")
print(theme)
print("---prompt--------------------------------")
print(dalle3_prompt)

response = client.images.generate(
    model="dall-e-3",
    prompt=dalle3_prompt,
    size="1024x1792", # "1792x1024", "1024x1792"
    quality="standard",
    n=1,
)
image_url = response.data[0].url

response = requests.get(image_url)
response.raise_for_status()

with open("temp.png", "wb") as f:
    f.write(response.content)
