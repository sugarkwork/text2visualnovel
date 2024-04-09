import os
import json
import asyncio
import anthropic

from pickle_memory import save_memory, load_memory

from dotenv import load_dotenv
load_dotenv()


client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)

sound_select_prompt = "You are a pro when it comes to music selection. We can provide the hash information of the music file that is closest to the situation the user is looking for. Since the song file name is a hash value, the user only needs the hash information to play the song. Please output only the hash value of the selected song. Your comments and explanations are not necessary. Be sure to output from \"hash:...\".\n\nThe song list data is as follows.\n\n"


def sound_selector(text):
    key = f"sound_selector result : {text}"
    result = load_memory(key)
    if result:
        return result

    with open("all_data.json") as f:
        all_data = json.load(f)

    message = message = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1000,
        temperature=0,
        system=f"{sound_select_prompt}\n{all_data}",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": text
                    }
                ]
            }
        ]
    )

    result = message.content[0].text.replace('hash:', '').strip()
    save_memory(key, result)
    return result


async def main():
    text = "lovery"
    response = sound_selector(text)
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
