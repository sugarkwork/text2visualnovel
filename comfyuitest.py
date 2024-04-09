import os
import io
import random
import uuid
import json
import urllib.request
import urllib.parse
from PIL import Image
import asyncio
import requests
import aiohttp
import anthropic

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


class ComfyUIClient:

    def __init__(self, server, prompt_file):
        self.PROMPT_FILE = prompt_file
        self.SERVER_ADDRESS = server
        self.CLIENT_ID = str(uuid.uuid4())
        self.ws = None
        self.session = None

        with open(self.PROMPT_FILE, 'r', encoding='utf8') as f:
            self.comfyui_prompt = json.loads(f.read())

    async def connect(self):
        self.session = aiohttp.ClientSession()
        self.ws = await self.session.ws_connect(f"ws://{self.SERVER_ADDRESS}/ws?clientId={self.CLIENT_ID}")

    async def close(self):
        await self.ws.close()
        await self.session.close()

    async def queue_prompt(self, prompt):
        payload = {"prompt": prompt, "client_id": self.CLIENT_ID}
        data = json.dumps(payload).encode('utf-8')
        async with self.session.post(f"http://{self.SERVER_ADDRESS}/prompt", data=data) as response:
            return await response.json()

    async def get_image(self, filename, subfolder, folder_type):
        params = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(params)
        async with self.session.get(f"http://{self.SERVER_ADDRESS}/view?{url_values}") as response:
            return await response.read()

    async def get_history(self, prompt_id):
        async with self.session.get(f"http://{self.SERVER_ADDRESS}/history/{prompt_id}") as response:
            return await response.json()

    async def get_images(self, prompt):
        prompt_id = (await self.queue_prompt(prompt))['prompt_id']
        output_images = {}
        while True:
            message = await self.ws.receive()
            if message.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(message.data)
                if data['type'] == 'executing' and data['data']['node'] is None and data['data']['prompt_id'] == prompt_id:
                    break
        
        history = (await self.get_history(prompt_id))[prompt_id]
        for node_id, node_output in history['outputs'].items():
            images_output = []
            if 'images' in node_output:
                for image in node_output['images']:
                    image_data = await self.get_image(image['filename'], image['subfolder'], image['type'])
                    images_output.append(image_data)
            output_images[node_id] = images_output
        
        return output_images
    
    def set_data(self, key, text:str=None, seed:int=None, image:Image.Image=None):
        key_id = self.find_key_by_title(key)
        if text is not None:
            self.comfyui_prompt[key_id]['inputs']['text'] = text
        if seed is not None:
            self.comfyui_prompt[key_id]['inputs']['seed'] = int(seed)
        if image is not None:
            # Upload image to comfyui server
            folder_name = "temp"
            
            # Save image to byte data
            byte_data = io.BytesIO()
            image.save(byte_data, format="PNG")
            byte_data.seek(0)

            # Upload image
            resp = requests.post(
                f"http://{self.SERVER_ADDRESS}/upload/image", 
                files={'image': ("temp.png", byte_data)}, 
                data={"subfolder": folder_name})
            
            # Set image path
            resp_json = json.loads(resp.content.decode('utf-8'))
            self.comfyui_prompt[key_id]['inputs']['image'] = resp_json.get('subfolder') + '/' + resp_json.get('name')

    def find_key_by_title(self, target_title):
        target_title = target_title.strip()
        for key, value in self.comfyui_prompt.items():
            title = value.get('_meta', {}).get('title', '').strip()
            if title == target_title:
                return key
        print(f"Key not found: {target_title}")
        return None

    async def generate(self, node_names=None) -> dict:
        node_ids = {}
        if node_names is not None:
            for node_name in node_names:
                node_id = self.find_key_by_title(node_name)
                if node_id is not None:
                    node_ids[node_id] = node_name

        images = await self.get_images(self.comfyui_prompt)
        results = {}
        for node_id, node_images in images.items():
            if node_id in node_ids:
                for image_data in node_images:
                    image = Image.open(io.BytesIO(image_data))
                    results[node_ids[node_id]] = image

        return results


async def gen_background(text, file_name=None) -> Image.Image:
    print("-----------------------------------------")
    background = get_background(text)
    print(background)
    
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
