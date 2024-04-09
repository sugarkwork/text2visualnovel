import os
import asyncio
import anthropic
from pickle_memory import load_memory, save_memory

from dotenv import load_dotenv
load_dotenv()

claude_client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
)

prompt_background = "You are a game CG background designer. Based on the theme the customer wants, we show them what will be reflected in the background image and explain what to draw. We will supplement what should be in the background, or what will fit perfectly. You don't need your own explanations, explanations, or emotional poetics. Please explain exactly what you are drawing and what you are drawing about the background image. The image you create is a background image, so it should never feature a person as the main character. However, it is permissible for people to exist as part of the background, such as in cityscapes or intersections. Please output in English."
prompt_cast = "You are a character designer. We will explain the character's appearance in detail according to the theme requested by the customer. We do not explain the character's posture, facial expressions, character settings, or reasons for choosing the character's appearance; instead, we only explain the character design without emotional expression. Do not express the character's age in numbers, but use words that allow you to roughly guess the age, such as boy, girl, young man, beauty, middle-aged, old man, crone, age unknown, etc. Don't describe what's in your character's hands. Please only explain the details of the character design (clothing, accessories, hair color, hairstyle, presence or absence of bangs, bangs style, eye color, etc.). Your thoughts and poetic expressions are not required. Just print out your design. All output should be in English."
prompt_face = "From the above text, extract only the facial features of the person (eye color and shape, presence or absence of bangs and style, hair color, presence or absence of makeup, and if makeup is worn, its color).We don't need your opinions or explanations. Please concentrate on extracting sentences that express the characteristics.Please output the text in English without using bullet points."

def get_claude(system, text):
    key = f"get_claude result : {system}_{text}"
    result = load_memory(key)
    if result:
        return result
    
    message = claude_client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1000,
        temperature=0,
        system=system,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"# Input (Japanese)\n{text}.\n\n# Note\nPlease output in English.\n"
                    }
                ]
            }
        ]
    )
    result = message.content[0].text
    save_memory(key, result)
    return result

def get_background(text):
    return get_claude(prompt_background, text)

def get_cast(text):
    return get_claude(prompt_cast, text)

def get_face(text):
    return get_claude(prompt_face, text)


async def main():
    text = """
国：日本
年代：現代
時間：昼
天候：晴天
大まかな場所：学校
具体的な場所：教室
雰囲気：沢山の生徒が思い思いに休憩している
スタイル：イラスト（ゲームCG風）
"""

    background = get_background(text)
    print(background)
    print("-----------------------------------------")

    cast = get_cast("絶世の美女")
    print(cast)
    print("-----------------------------------------")

    face = get_face(cast)
    print(face)
    print("-----------------------------------------")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
