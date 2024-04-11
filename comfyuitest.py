import os
import random
from PIL import Image
import asyncio
import anthropic

from comfyuiclient import ComfyUIClient
import pose_selector
from pickle_memory import load_memory, save_memory


# use .env file to store the API key
# ex) ANTHROPIC_API_KEY="sk-ant-api..."
from dotenv import load_dotenv
load_dotenv()


claude_client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
)

prompt_background = "You are a game CG background designer. Based on the theme the customer wants, we show them what will be reflected in the background image and explain what to draw. We will supplement what should be in the background, or what will fit perfectly. You don't need your own explanations, explanations, or emotional poetics. Please explain exactly what you are drawing and what you are drawing about the background image. The image you create is a background image, so it should never feature a person as the main character. However, it is permissible for people to exist as part of the background, such as in cityscapes or intersections. Please output in English."
prompt_cast = "You are a character designer. We will explain the character's appearance in detail according to the theme requested by the customer. We do not explain the character's posture, facial expressions, character settings, or reasons for choosing the character's appearance; instead, we only explain the character design without emotional expression. Do not express the character's age in numbers, but use words that allow you to roughly guess the age, such as boy, girl, young man, beauty, middle-aged, old man, crone, age unknown, etc. Don't describe what's in your character's hands. Please only explain the details of the character design (clothing, accessories, hair color, hairstyle, presence or absence of bangs, bangs style, eye color, etc.). Your thoughts and poetic expressions are not required. Just print out your design. All output should be in English. Please output in English."
prompt_face = "You are a character designer. From the specified text, find out the characteristics of the person's face, such as the color and shape of the eyes, the presence or absence of bangs and their style, the color of the hair, the presence or absence of makeup, the color of makeup, if any, the presence or absence of glasses, etc. Write down only information about facial features such as color and shape in an easy-to-understand manner. Your opinions, explanations, and explanations are not necessary. Please output as English sentences without using bullet points. Please output in English."


def get_claude(system, text):
    key = f"get_claude: system={system} , text={text}"
    cached = load_memory(key)
    if cached is not None:
        return cached
    
    message = claude_client.messages.create(
        model="claude-3-haiku-20240307", # "claude-3-sonnet-20240229", "claude-3-opus-20240229", "claude-3-haiku-20240307"
        max_tokens=1000,
        temperature=0,
        system=system,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Theme(Japanese) : {text}\n\nPlease output in English."
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

def get_charactor(text):
    return get_claude(prompt_cast, text)

def get_face(text):
    return get_claude(prompt_face, text)


async def gen_background(text, file_name=None) -> Image.Image:
    print("-----------------------------------------")
    background = get_background(text)
    print(background)
    
    comfyui_client = None
    try:
        comfyui_client = ComfyUIClient("127.0.0.1:8188", "bgimage_api.json")
        await comfyui_client.connect()
        comfyui_client.set_data(key='KSampler', seed=random.randint(0, 1000000))
        comfyui_client.set_data(key='Input Prompt', text=background)
        for key, image in (await comfyui_client.generate(["Result Image"])).items():
            if file_name is not None:
                image.save(file_name)
            else:
                output_dir = "output/background"
                output_dir_final = output_dir
                countup = 0
                while os.path.exists(output_dir_final):
                    output_dir_final = f"{output_dir}_{countup}"
                    countup += 1

                os.makedirs(output_dir_final, exist_ok=True)
                image.save(f"{output_dir_final}/{key}.png")

            return image
    finally:
        if comfyui_client is not None:
            await comfyui_client.close()


async def gen_charactor(text, file_path=None, base_name=None):
    print("-----------------------------------------")
    cast = get_charactor(text)
    face = get_face(cast)
    print(cast)
    print(face)
    
    comfyui_client = ComfyUIClient("127.0.0.1:8188", "text2cast_api.json")
    await comfyui_client.connect()
    comfyui_client.set_data(key='KSampler', seed=random.randint(0, 1000000))
    comfyui_client.set_data(key='Input Charactor Prompt', text=cast)
    comfyui_client.set_data(key='Input Face Prompt', text=face)

    used_poses = load_memory("used_poses") or []
    pose_file = random.choice(pose_selector.get_pose_image(cast, used_poses))
    used_poses.append(pose_file)
    save_memory("used_poses", used_poses)

    comfyui_client.set_data(key='Load Image', image=Image.open(pose_file))

    output_dir_final = ""
    if file_path is None:
        output_dir = "output/charactor"
        output_dir_final = output_dir
        countup = 0
        while os.path.exists(output_dir_final):
            output_dir_final = f"{output_dir}_{countup}"
            countup += 1

        os.makedirs(output_dir_final, exist_ok=True)

    for key, image in (await comfyui_client.generate(["Result Smile", "Result Angly", "Result Shy", "Result Evil", "Result Surprise", "Result Sad"])).items():
        expression = key.replace("Result ", "").lower()
        if file_path is not None:
            image.save(f"{file_path}/{base_name}_{expression}.png")
        else:
            image.save(f"{output_dir_final}/{key}.png")

    await comfyui_client.close()


async def main():

    bg_prompt = """
Country: Japan
Year: modern
Time: Noon
Weather: Sunny
Approximate location: school
Specific location: Classroom
Atmosphere: Many students are taking breaks as they wish.
Style: Illustration (game CG style)
"""
    bg_task = asyncio.create_task(gen_background(bg_prompt))
    chara_task = asyncio.create_task(gen_charactor("日本の女子高生、絶世の美少女、恥ずかしがりや"))

    await bg_task, chara_task


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
