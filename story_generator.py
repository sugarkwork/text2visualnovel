import os
import json
import uuid
import hashlib
import shutil
import requests
import io
from pydub import AudioSegment
import threading
import queue
import time
import random

from PIL import Image
import cohere
from cohere.core.request_options import RequestOptions
from pickle_memory import save_memory, load_memory
from dotenv import load_dotenv
load_dotenv()

import sound_selector
import pose_selector
import voice_selector
from comfyuiclient import ComfyUIClient


class PromptGenerator:

    def __init__(self, client):
        self.client = client    

    def get_claude(self, system, text):
        key = f"get_claude: system={system} , text={text}"
        cached = load_memory(key)
        if cached is not None:
            return cached
        
        key2 = f"response: {system} {text}"
        response = load_memory(key2)
        if not response:
            response = self.client.chat(
                chat_history=[
                    {"role": "SYSTEM", "message": str(system)},
                ],
                message=str(text),
                model="command-r-plus"
            ).text
        save_memory(key2, response)
        return response

    def get_background(self, text):
        prompt_background = """
# Order
You are a game CG background designer.
Based on the theme the customer wants, we show them what will be reflected in the background image and explain what to draw. We will supplement what should be in the background, or what will fit perfectly.
You don't need your own explanations, explanations, or emotional poetics. Please explain exactly what you are drawing and what you are drawing about the background image.
The image you create is a background image, so it should never feature a person as the main character. However, it is permissible for people to exist as part of the background, such as in cityscapes or intersections.
Please output in English."""
        return self.get_claude(prompt_background, text)

    def get_charactor(self, text):
        prompt_cast = """You are a character designer.
You can describe the character's appearance in detail according to your desired theme.
You choose your character's posture, facial expressions, character settings, and character appearance, but don't explain why or explain them. When doing so, please focus on explaining only the character design and omitting emotional expressions.
Do not express the character's age using numbers; instead, use English words that allow you to guess the approximate age, such as boy, girl, young man, beauty, middle-aged, elderly, senile, age unknown.
Don't describe things your character owns. Please explain the details of the character design (clothes, accessories, hair color, hairstyle, presence of bangs, bangs style, eye color, chest size for female characters).
Your thoughts and poetic expressions are not required. All output must be in English.
Please output in English."""
        return self.get_claude(prompt_cast, text)

    def get_face(self, text):
        prompt_face = """You are a character designer.
From the specified text, find out the characteristics of the person's face, such as the color and shape of the eyes, the presence or absence of bangs and their style, the color of the hair, the presence or absence of makeup, the color of makeup, if any, the presence or absence of glasses, etc.
Write down only information about facial features such as color and shape in an easy-to-understand manner.
Your opinions, explanations, and explanations are not necessary. Please output as English sentences without using bullet points.
Please output in English."""
        return self.get_claude(prompt_face, text)

    def get_title(self, text):
        prompt_title = """
# Order
You are a game designer.
You design an attractive game title screen according to user requests.
The designs you describe are all done in English words and explain the character's posture, pose, background, etc. Please do not explain text, logos, or captions at this time. Please do not think about the logo or text, as the logo and text will be designed by a different designer.

In the design you describe, first explain the visuals and posture of each character. After that, please explain the background, effects, etc.
Use the user's input language for input only, and be sure to output all your explanations in English.
Your thoughts, thoughts, and opinions are not needed.
"""
        return self.get_claude(prompt_title, text)


class DataSelector:
    def __init__(self, client):
        self.client = client
    
    def bgm(self, text:str) -> str:
        key = f"sound_selector result : {text}"
        result = load_memory(key)
        if result:
            return result
        
        with open("bgm_data.json") as f:
            all_data = json.load(f)

        bgm_select_prompt=f"""
# Order
You are a pro when it comes to music selection.
You can provide the hash information of the music file that is closest to the situation the user is looking for.
Since the song file name is a hash value, the user only needs the hash information to play the song.
Please output only the hash value of the selected song. Your comments and explanations are not necessary.
Be sure to output from \"hash:...\".

# Song list data
```json
{json.dumps(all_data, indent=4, ensure_ascii=False)}
```
""".strip()

        key2 = f"response: {text} {bgm_select_prompt}"
        response = load_memory(key2)
        if not result:
            response = self.client.chat(
                chat_history=[
                    {"role": "SYSTEM", "message": bgm_select_prompt},
                ],
                message=text,
                model="command-r-plus"
            ).text
        save_memory(key2, response)

        result = response.replace('hash:', '').strip()
        save_memory(key, result)

        return result
    
    def voice(self, text:str, exclude_voice_list=None, nocache=False) -> str:
        key = f"voice_selector: {text} : {exclude_voice_list}"
        result = load_memory(key)
        if nocache:
            result = None
        if result:
            return result

        voice_names = []
        voice_list = []
        with open('voice_list.txt', 'r', encoding='utf8') as f:
            for voice in f.read().splitlines():
                voice_csv = voice.split(',')
                voice_name = voice_csv[0].strip()
                voice_tags = voice_csv[1].strip().split('|')
                voice_names.append(voice_name)
                if exclude_voice_list and voice_name in exclude_voice_list:
                    continue
                voice_list.append({'name': voice_name, 'tags': voice_tags})
        
        if not voice_list:
            raise Exception("No voice list available.")

        voice_select_prompt = f"""
# Order
You are a character designer.
Based on the theme requested by the customer, you select one voice list from the character setting data, considering the best voice for the character.
Please do not output your thoughts or supplementary information, just tell us the voice name from the voice list.
Be sure to start the output with \"Voice name:...\".

# Voice list
```json
{json.dumps(voice_list, indent=4, ensure_ascii=False)}
```
""".strip()
        
        key2 = f"response: {text} {voice_select_prompt}"
        response = load_memory(key2)
        if nocache:
            response = None
        if not response:
            for _ in range(3):
                response = self.client.chat(
                    chat_history=[
                        {"role": "SYSTEM", "message": voice_select_prompt},
                    ],
                    message=text,
                    model="command-r-plus"
                ).text.replace('Voice name:', '').strip()
                if response in voice_names:
                    break
            else:
                raise Exception("Failed to select voice.")

        save_memory(key2, response)
        save_memory(key, response)
        return response

    def expression(self, expression):
        response = load_memory(expression)
        if response is not None:
            return response
            
        if not response:
            for _ in range(3):
                response = self.client.chat(
                    chat_history=[
                        {"role": "SYSTEM", "message": "You are a game character designer.\nYou can answer various character expressions according to user requests.\n\nThe following six types of images are available as game materials.\n[\"sad\", \"surprise\", \"evil smile\", \"shy\", \"angly\", \"smile\"]\n\nPlease select the one that is closest to the facial expression/emotion specified by the user and output only the answer. Your comments and explanations are not necessary."},
                    ],
                    message=expression,
                    model="command-r-plus"
                ).text.strip('"').strip().lower().replace('evil smile', 'evil')
                if response in ["sad", "surprise", "evil", "shy", "angly", "smile"]:
                    break

        save_memory(expression, response)
        return response

class VoiceGenerator:
    def __init__(self, server = 'http://localhost:5000'):
        self.server = server
        self.reflesh_voice_model()

    def get_voice_model_id_by_name(self, name):
        print(f"Getting model id by name: {self.server}, {name}")
        if name is None:
            raise ValueError("Model name is required")
        name = name.strip()
        response = requests.get(f'{self.server}/models/info')
        data = response.json()
        for model_id, model_info in data.items():
            model_name = model_info.get('config_path').split("\\")[1]
            if name == model_name:
                return model_id
        raise ValueError(f"Model not found: '{name}'")
    
    def reflesh_voice_model(self):
        url = f'{self.server}/models/refresh'
        headers = {'accept': 'application/json'}
        requests.post(url, headers=headers)

    def text2mp3(self, name, text) -> io.BytesIO:
        try:
            model_id = self.get_voice_model_id_by_name(name)
            
            url = f"{self.server}/voice"
            params = {
                'text': text,
                'model_id': model_id,
                'speaker_id': '0',
                'sdp_ratio': '0.2',
                'noise': '0.6',
                'noisew': '0.8',
                'length': '1',
                'language': 'JP',
                'auto_split': 'true',
                'split_interval': '0.5',
                'assist_text_weight': '1',
                'style': 'Neutral',
                'style_weight': '10'
            }
            headers = {'accept': 'audio/wav'}
            
            response = requests.post(url, params=params, headers=headers)
            if response.status_code == 200:
                sound = AudioSegment.from_wav(io.BytesIO(response.content))
                mp3_data = io.BytesIO()
                sound.export(mp3_data, format="mp3")
                mp3_data.seek(0)
                return mp3_data
            else:
                print(f"Request failed with status code: {response.status_code}")
        except requests.exceptions.Timeout:
            print(f"Request to {self.server} timed out. Retrying...")
        except requests.exceptions.RequestException as e:
            print(f"Request to {self.server} failed: {e}. Retrying...")

    def save_voice(self, filename, name, text):
        print(f"Saving voice to {filename}, name: {name}, text: {text}")
        mp3_data = self.text2mp3(name, text)
        with open(filename, "wb") as f:
            f.write(mp3_data.read())

    

class CharactorGenerator:
    def __init__(self, client):
        self.client = client
    
               
    def generator(self, text, file_path=None, base_name=None):
        promptGenerator = PromptGenerator(self.client)
        cast = promptGenerator.get_charactor(text)
        face = promptGenerator.get_face(cast)
        
        comfyui_client = ComfyUIClient("127.0.0.1:8188", "text2cast_api.json")
        comfyui_client.connect()
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

        for key, image in comfyui_client.generate(["Result Smile", "Result Angly", "Result Shy", "Result Evil", "Result Surprise", "Result Sad"]).items():
            expression = key.replace("Result ", "").lower()
            if file_path is not None:
                image.save(f"{file_path}/{base_name}_{expression}.png")
            else:
                image.save(f"{output_dir_final}/{key}.png")

        comfyui_client.close()


class StoryNode:
    def __init__(self, client, parent=None, user_choise:str=None, story_prompt=None):
        self.client = client
        self.parent = parent
        self.main_story = None
        self.previous_story = None
        self.synopsis = None

        self.uuid = None
        if parent:
            self.main_story = self.parent.main_story
            self.previous_story = self.parent.story
            self.uuid = hashlib.sha256(str(self.parent.uuid + user_choise).encode()).hexdigest()
        else:
            self.main_story = self.create_main_story(story_prompt)
            title = self.main_story.get("title engilsh", self.main_story.get("title japanese"))
            self.uuid = hashlib.sha256(title.encode()).hexdigest()

        self.user_choise = user_choise
        self.story = None
        self.choices = []

        # setting
        self.settings = {"used_voices":{}}
        if self.parent:
            self.settings = self.parent.settings
    

    def generate(self, elect_level=0):
        old_synopsis = None
        story_logs = []
        if self.parent:

            if self.parent.parent:
                story_data = self.parent.parent.story.get("story data")
                if story_data:
                    story_logs.extend(story_data)

            story_data = self.parent.story.get("story data")
            if story_data:
                story_logs.extend(story_data)

            if self.parent.parent:
                if self.parent.parent.synopsis:
                    old_synopsis = self.parent.parent.synopsis
        
            self.synopsis = self.create_synopsis(self.main_story, old_synopsis, story_logs)

        self.story = self.create_story(self.main_story, self.previous_story, self.synopsis, self.user_choise, elect_level=elect_level)

        self.auto_fix_tags()
        
        #print(json.dumps(self.main_story.get('charactors'), indent=4, ensure_ascii=False))

        for choice in self.story["next choices"]:
            self.choices.append(StoryNode(self.client, self, choice["select"]))
    

    def json_format(self, text:str) -> dict:
        try:
            return json.loads(text)
        except json.decoder.JSONDecodeError:
            try:
                return eval(text)
            except (Exception, SyntaxError):
                try:
                    if '```json' in text:
                        text = text.split('```json')[1].split('```')[0]
                        return self.json_format(text)
                except ValueError:
                    lines = text.split("\n")
                    for i, line in enumerate(lines):
                        line = line.strip()
                        if not line.startswith("\"") and line.endswith("\""):
                            lines[i] = f"\"{line}"
                        elif not line.startswith("\"") and line.endswith("\","):
                            lines[i] = f"\"{line}"
                        if line.startswith("\"") and not (line.endswith("\"") or line.endswith("\",")):
                            line_temp = line.strip().strip("\"")
                            if '\"' not in line_temp:
                                lines[i] = f"\"{line_temp}\","
                        if line.startswith("「") and line.endswith("」,"):
                            lines[i] = line.replace("「", "\"").replace("」", "\"").replace("：", ":")
                        
                    return self.json_format("\n".join(lines))

        print (f"Failed to parse JSON format: {text}")
        raise ValueError("Failed to parse JSON format")

    
    def create_main_story(self, prompt:str) -> dict:
        result = load_memory(prompt)
        if result:
            result["user input theme"] = prompt.strip()
            if 'uuid' not in result:
                result["uuid"] = uuid.uuid4().hex
                save_memory(prompt, result)
            return result
        
        main_story_prompt = """
# Order
You are a screenwriter. You can write characters, scenarios, and endings according to the requested theme.
The output format is JSON. Specifically, it is as follows.

# User input example
異世界探検部。古い地図を手掛かりに異世界へ旅立ち冒険する。

# Example of your output
```json
{
"user input theme": "異世界探検部。古い地図を手掛かりに異世界へ旅立ち冒険する。",
"title japanese": "異世界探検部",
"title english": "Exploration Club of Another World",
"story":"主人公は高校の探検部に所属する平凡な男子学生です。ある日、部室で見つけた古い地図を手がかりに、部員たちと共に学校の地下に眠る秘密の扉を発見します。扉の先には、不思議な異世界が広がっていました。その世界を探検するうちに、彼らは異世界の危機に巻き込まれ、世界を救うために奮闘することになります。",
"settings":[
    "異世界の起源：実は、異世界は人間の夢や想像力が具現化した世界である。扉は人の心の奥深くに存在し、強い想いを持つ者だけがそこに辿り着ける。主人公たちは無意識のうちに、自分たちの心の扉を開いてしまったのだ。",
    "異世界と現実世界の関係：異世界の出来事は、実は現実世界にも影響を及ぼしている。異世界の危機が深刻になればなるほど、現実世界でも異変が起きる。逆に、現実世界の人々の心が穏やかになれば、異世界も平和になる。",
    "主人公たちが異世界の危機を乗り越えた後、彼らは異世界と現実世界が表裏一体であることを知る。自分たちの心と向き合い、前向きに生きることが、両方の世界を守ることにつながるのだと気づくのである。"
],
"Events that occur in parallel behind the story of this world":{
    "0%": "魔王は力を貯めています。",
    "20%": "魔王が力を爆発させ、現実で校舎が揺れるなどの影響が出始めます。",
    "40%": "魔王の力が限界を突破して、異世界と現実世界が融合し始めます。",
    "80%": "魔王の力により異世界と現実が完全に融合してしまい、両方の世界が混沌としてしまいます。",
    "100%": "魔王を止める事が出来ず世界が崩壊してしまい Game Over となります。"
},
"Facility and place name":
{
    "垣岡高校": "主人公たちが通う高校。探検部の部室は地下にあり、古い地図や探検用具が置かれている。",
    "異世界の扉": "垣岡高校の地下に眠る、異世界へ続く扉。普段は見えないが、古い地図を手がかりにすることで見つけることができる。",
    "異世界：トルゥーワールド": "主人公たちが探検する異世界。現実世界とは異なる風景や生物が存在し、不思議な力が働いている。",
    "魔王の城": "異世界の中心にそびえる、魔王の住む城。魔王の力が最も強い場所であり、異世界の危機の根源となっている。",
    "神秘の祠": "異世界に点在する神秘的な祠。そこには異世界の秘密が隠されており、主人公たちの冒険の鍵となる。"
},
"ending conditions":[
    "True End: 主人公と仲間たちは平和を取り戻した異世界に別れを告げ、現実世界に戻ってきた彼らは、経験を胸に新たな冒険に旅立ちます。",
    "Bitter Sweet End: 魔王を倒し異世界の危機は去りましたが、犠牲も大きくありました。主人公は仲間を失った悲しみを乗り越え、その思い出を胸に現実世界で生きていくことを決意します。",
    "Revelation End: 異世界の探検を通して、自分の弱さと向き合い、乗り越えていく中で、真の強さを手に入れていきます。",
    "Tragic End: 主人公は異世界で出会った特別な存在と深い絆を築きますが、世界の危機を前に、その存在は犠牲となってしまいます。深く心に傷を負いながらも、主人公は前を向いて生きていくことを誓います。",
    "Bad End: 主人公たちは異世界の危機を解決できず、現実世界に戻ることができません。異世界の闇に取り込まれ、永遠に閉ざされてしまいます。",
    "Secret End: 探検を進め、隠されたヒントを集めることで、異世界の秘密を解き明かし、誰も知らない真実へとたどり着くことができるのです。",
    "Game Over: 主人公たちは異世界の危機に立ち向かいますが、その力不足を痛感し、敗北を味わいます。異世界は闇に包まれ、主人公たちはそのまま閉ざされてしまいます。",
    "Dream End: 異世界での冒険の末、主人公は目を覚まします。全ては夢だったのでしょうか。"
],
"charactors":[
    {"charactor name":"田中太郎", "display name":"太郎", "appearance":"18歳、男性、黒髪で黒い目、ショートヘア、迷彩のズボンに白いシャツ", "personality":"普通の男子", "status":"健康", "player":"True", "voice":"普通の男性の声"},
    {"charactor name":"田中詩織", "display name":"詩織","appearance":"女の子、白いワンピース、赤いヘアピン、青い髪、ロングツインテール、赤い瞳", "personality":"正義感が強い", "Relationship with players":"顔見知り", "status":"右手を怪我している", "voice":"少女らしい透き通った声"},
    {"charactor name":"岡田龍平", "display name":"龍平","appearance":"男の子、学生服、緑の髪、ショートヘア、青い瞳", "personality":"気が弱い", "Relationship with players":"初対面", "status":"元気", "voice":"声変わりした低めの男性の声"},
    {"charactor name":"魔王グランディ", "display name":"魔王グランディ", "appearance":"200歳、女性、魔王、黒いロングヘア、禍々しいドレス、黒い翼、ツノが生えている", "personality":"心を病んでおり攻撃的", "Relationship with players":"初対面、敵対", "status":"力を貯めている", "voice":"低い女性の声"}
]
}
```
"""
        
        key = f"response: {prompt} {main_story_prompt}"
        response = load_memory(key)

        if not result:
            print("Creating main story...")
            response = self.client.chat(
                chat_history=[
                    {"role": "SYSTEM", "message": main_story_prompt},
                ],
                message=prompt,
                model="command-r-plus",
                request_options = RequestOptions(timeout_in_seconds=60 * 5)
            ).text

        save_memory(key, response)

        result = self.json_format(response)
        result["uuid"] = uuid.uuid4().hex
        result["user input theme"] = prompt.strip()

        save_memory(prompt, result)

        return result


    def create_story(self, main_story:dict, previous_story:dict=None, synopsis:str=None, user_choise:str=None, nocache=False, elect_level=0) -> dict:
        for n in range(5):
            print(f"Creating story({n}): {user_choise}")
            try:        
                result = self._create_story(main_story, previous_story, synopsis, user_choise, nocache, elect_level)
                required_keys = ["charactor status", "story data", "next choices"]
                for key in required_keys:
                    if key not in result:
                        print(f"KeyError: {key}; retrying...")
                        nocache = True
                        continue
                if 'add charactors' in result:
                    main_story["charactors"].extend(result["add charactors"])
                    print("Added new charactors.")
                return result
            except Exception as e:
                print(f"Error: {e}/{type(e)}; retrying...")
                nocache = True
                continue
        
        raise Exception("Failed to create story.")


    def _create_story(self, main_story:dict, previous_story:dict=None, synopsis:str=None, user_choise:str=None, nocache=False, elect_level=0) -> dict:
        print(f"_Creating story: {user_choise}")
        key = f"create_story: {main_story}_{previous_story}_{user_choise}"
        result = load_memory(key)
        if nocache:
            result = None
        if result:
            return result

        main_story_prompt = f"""
# Order
Please use the following story settings to output the story data for your visual novel game in JSON format.

# Story Settings
{json.dumps(main_story, indent=4, ensure_ascii=False)}

""".strip()
        
        if synopsis:
            main_story_prompt += f"""
# Previous Synopsis
{synopsis}

"""
        sex_flag = ""
        if elect_level > 0:
            sex_flag = "- Please create a story and choices that will lead to sexual activity with the heroine in the next choice.\n"
        story_prompt = """
# Order
You are a game engine for visual novel games. You create the following stream from the input data and output it in JSON format.
- "story data": 30 or more are required.
- "next choices": 2 to 3 are required.
- If the atmosphere of the scene changes, please specify the BGM atmosphere with "change bgm".
""" + sex_flag + """

# Example of your output JSON format.
```json
{
"charactor status":[
    {"charactor name":"田中太郎", "inventory":["スマートフォン", "日本地図"], "mental state"="正常", "physical state"="健康", "location":"日本、屋外、住宅街", "understanding":["異世界に魔王がいるらしい","田中詩織はかわいい"]},
    {"charactor name":"田中詩織", "Relationship with player":"顔見知り、気になる", "inventory":["リュックサック","地図","コンパス","水筒","おにぎり"], "mental state"="元気", "physical state"="右手を怪我している", "location":"日本、屋外、住宅街", "understanding":["田中太郎は幼馴染"]},
    {"charactor name":"岡田龍平", "Relationship with player":"初対面", "inventory":["神秘の魔石","魔封じの剣"], "mental state"="不安", "physical state"="元気", "location":"日本、屋内、岡田龍平の自宅", "understanding":["異世界には魔王がいる"]},
    {"charactor name":"魔王グランディ", "Relationship with player":"初対面、全人類に敵対", "inventory":["魔王の剣"], "mental state"="怒り", "physical state"="力を貯めている", "location":"異世界、魔王城、玉座の間", "understanding":["人間は信用ならない","近いうちに人間が来る"]}
],
"add charactors":[
    {"charactor name":"リディア・マッカーソン", "display name":"リディア", "appearance":"180歳、女性、エルフ、金髪ロングヘア、", "personality":"優しい", "Relationship with players":"初対面", "status":"元気", "voice":"透き通った声"}
],
"story data":[
    {"mode":"change background image", "data":"日本、昼間、屋外、住宅街"},
    {"mode":"play sound effect", "data":"スズメの鳴声、ちゅんちゅん"},
    {"mode":"change bgm", "data":"快晴、明るい、楽しい、平和な音楽"},
    {"mode":"sound effect", "data":"女性の足音、ハイヒール、コツコツ"},
    {"mode":"talk", "charactor name":"田中太郎", "display name":"太郎", "talk":"こんにちは！", "expression":"Smile"},
    {"mode":"show charactor", "data":"田中詩織"},
    {"mode":"talk", "charactor name":"田中詩織", "display name":"詩織", "talk":"あら？こんにちは", "expression":"Shy"},
    {"mode":"player characters inner voice", "data":"彼女は俺の幼馴染だ"},
    {"mode":"talk", "charactor name":"田中詩織", "display name":"詩織", "talk":"あたし急いでるから", "expression":"Shy"},
    {"mode":"hide charactor", "data":"田中詩織"},
    {"mode":"player characters inner voice", "data":"行ってしまった……"},
    {"mode":"play sound effect", "data":"コケる音。ドッシン！"},
    {"mode":"show charactor", "data":"リディア・マッカーソン"},
    {"mode":"talk", "charactor name":"リディア・マッカーソン", "display name":"？？？", "talk":"いったーい！", "expression":"Sad"},
    {"mode":"talk","charactor name":"田中太郎", "display name":"主人公", "talk":"え？誰？", "expression":"Surprise"},
    {"mode":"talk", "charactor name":"リディア・マッカーソン", "display name":"リディア", "talk":"わたし？わたしはリディアよ！", "expression":"Smile"},
],
"next choices":[
    {"select":"エルフをデートに誘う", "info":"リディアをデートをデートに誘います。"},
    {"select":"家に帰る", "info":"自宅に帰ります。"},
    {"select":"UFOを見つける", "info":"UFOを探しに行きます。"}
] 
}
```
"""     
        payload = [
            {"role": "SYSTEM", "message": story_prompt},
        ]
        if previous_story:
            payload.append({"role": "USER", "message": main_story_prompt})
            payload.append({"role": "CHATBOT", "message": json.dumps(previous_story, indent=4, ensure_ascii=False)})
            message = user_choise
        else:
            message = main_story_prompt + "\n\n# Previous Story\nThe story has just begun.You need to write an introduction that draws players into the world of your work."

        key2 = f"response: {payload}_{message}"
        response = load_memory(key2)
        if nocache:
            response = None
        if not response:
            response = self.client.chat(
                chat_history=payload,
                message=str(message),
                model="command-r-plus",
                max_tokens=4000,
                request_options = RequestOptions(timeout_in_seconds=60*5),
                seed=random.randint(0, 1000000)
            ).text
            save_memory(key2, response)

        result = self.json_format(response)
        save_memory(key, result)

        return result


    def create_synopsis(self, main_story:dict, synopsis:str=None, story_data:dict=None, nocache=False) -> str:
        key = f"create_synopsis: {main_story}_{synopsis}_{story_data}"
        result = load_memory(key)
        if nocache:
            result = None
        if result:
            return result

        synopsis_prompt = f"""
# Order
You can summarize stories entered by users. You will focus on the main character and summarize what has changed and how it has changed, the psychological state of the characters, the tools, the promises between the characters, the new setting that has appeared and its state, etc.

"""
        synopsis_data = ""
        if main_story:
            synopsis_data += f"""
# Main Story
```json
{json.dumps(main_story, indent=4, ensure_ascii=False)}
```

"""

        if synopsis:
            synopsis_data += f"""
# Previous Synopsis
{synopsis}

"""
        if story_data:
            synopsis_data += f"""
# Previous Story Data
```json
{json.dumps(story_data, indent=4, ensure_ascii=False)}
```

"""
        
        payload = [
            {"role": "SYSTEM", "message": synopsis_prompt},
        ]
        key2 = f"response: {synopsis_prompt} {synopsis_data}"
        response = load_memory(key2)
        if nocache:
            response = None
        if not response:
            response = self.client.chat(
                chat_history=payload,
                message=str(synopsis_data),
                model="command-r-plus"
            ).text
            save_memory(key2, response)

        result = response
        save_memory(key, result)

        return result
    
    def get_voices(self) -> dict:
        name_voice = {}
        for charactor in self.main_story.get("charactors"):
            name = charactor.get("charactor name")
            voice = charactor.get("voice")
            #print(f"Getting voice for {name} ({voice}) - {self.settings.get('used_voices')}")
            if name not in self.settings.get("used_voices"):
                exclude_voices = []
                for chara in self.settings.get("used_voices"):
                    exclude_voices.append(self.settings.get("used_voices")[chara]["voice_name"])
                self.settings.get("used_voices")[name] = {
                    "define":voice, 
                    "voice_name": voice_selector.get_voice_name(charactor, exclude_voices)}
                print(f"New voice: {name} ({voice}) - {self.settings.get('used_voices')[name]['voice_name']}")
            name_voice[name] = self.settings.get("used_voices")[name]["voice_name"]
        
        #print(name_voice)

        result = {}
        for story in self.story.get("story data"):
            if story["mode"] == "talk":
                data = {}
                name = story["charactor name"]
                voice = name_voice.get(name)
                data["voice_name"] = voice
                data["talk"] = story["talk"]
                result[self.get_voice_key(name, story["talk"])] = data

        return result
    
    def get_backgrounds(self) -> dict:
        result = {}
        for story in self.story.get("story data"):
            if story["mode"] == "change background image":
                result[self.get_image_key(story["data"])] = "異世界ファンタジー、" + story["data"]
        return result
    
    def get_charactors(self) -> dict:
        result = {}
        for chara in self.main_story["charactors"]:
            result[self.get_image_key(chara["charactor name"])] = chara
        return result
    
    def get_bgm(self) -> dict:
        result = []
        for story in self.story.get("story data"):
            if story["mode"] == "change bgm":
                if story.get("data"):
                    #select_bgm = sound_selector.sound_selector(story['data'])
                    select_bgm = DataSelector(self.client).bgm(story['data'])
                    result.append(select_bgm)
                    print(f"Selected BGM: {story['data']} - {select_bgm}")
        return result
    
    
    def get_voice_key(self, charactor_name:str, talk:str) -> str:
        return hashlib.md5(f"{charactor_name}{talk}".encode()).hexdigest()
    
    def get_image_key(self, charactor_name:str) -> str:
        return hashlib.md5(f"{charactor_name}".encode()).hexdigest()
    
    def my_splitfunc(self, string, delimiters):
        import re
        pattern = '([' + ''.join(map(re.escape, delimiters)) + '])'
        return re.split(pattern, string)
    
    def replace_underscore_in_dict(self, data):
        if isinstance(data, dict):
            new_data = {}
            for key, value in data.items():
                new_key = key.replace("_", " ")
                new_data[new_key] = self.replace_underscore_in_dict(value)
            return new_data
        elif isinstance(data, list):
            return [self.replace_underscore_in_dict(item) for item in data]
        elif isinstance(data, str):
            return data.replace("_", " ")
        else:
            return data
        
    def auto_fix_tags(self):
        fix_data = {
            "play sound effect": ["se", "sound effect", "play sound", "play se"],
            "change background image": ["background", "bg", "change background", "change bg", "background image"],
            "change bgm": ["bgm", "change background music", "set bgm", "bgm change"],
            "player characters inner voice": ["inner voice", "player inner voice", "players inner voice", "charactor inner voice"],
            "talk": ["dialogue", "talking", "speak", "say", "dialog", "speech"],
            "show charactor": ["show", "display", "charactor"],
            "hide charactor": ["hide", "remove", "charactor"],
        }

        def is_fix_target(data, values):
            for val in values:
                if val == data:
                    return True
            return False
        
        print("Fixing tags...")
        self.story = self.replace_underscore_in_dict(self.story)
        #print(self.story)

        fix_storys = []

        charactor_name_table = {}
        for charactor in self.main_story.get("charactors"):
            charactor_name_table[charactor["charactor name"]] = []
            charactor_name_table[charactor["charactor name"]].append(charactor["display name"])

        bg_image_cache = None
        bgm_found = False
        for story in self.story.get("story data"):
            clone_story = story.copy()

            for key, values in fix_data.items():
                if is_fix_target(clone_story["mode"], values):
                    clone_story["mode"] = key
                    print(f"Fixed: {story['mode']} -> {key}")
                    break

            if clone_story["mode"] == "talk":
                exp = clone_story.get("expression", "smile")
                if not exp:
                    exp = "smile"
                exp = exp.strip().lower().replace("evil smile", "evil")
                if exp not in ["sad", "surprise", "evil", "shy", "angly", "smile"]:
                    exp = DataSelector(self.client).expression(exp) #pose_selector.get_expression(exp)
                if clone_story["charactor name"] not in charactor_name_table:
                    for charactor_name, val_names in charactor_name_table.items():
                        for val_name in val_names:
                            if clone_story["charactor name"] == val_name:
                                clone_story["charactor name"] = charactor_name
                            break
                clone_story["expression"] = exp
            
            if clone_story["mode"] == "change bgm":
                bgm_found = True
            
            if clone_story["mode"] == "change background image" and not bg_image_cache:
                bg_image_cache = clone_story["data"]
                self.settings["temp bgm"] = DataSelector(self.client).bgm(bg_image_cache)#sound_selector.sound_selector(bg_image_cache)
        
            fix_storys.append(clone_story)
        
        if not bgm_found:
            fix_storys.insert(0, {"mode":"change bgm", "data": bg_image_cache})
        
        self.story["story data"] = fix_storys


    def save(self, save_dir:str) -> None:
        with open(f"{save_dir}/{self.uuid}.txt", "w", encoding="utf8") as f:
            f.write(f"changeFigure:none -left -next;\n")
            f.write(f"changeFigure:none -right -next;\n")
            f.write(f"changeFigure:none -next;\n")

            if self.settings.get("temp bgm"):
                f.write(f"bgm:{self.settings.get('temp bgm')}.mp3 -enter=3000 -next;\n")

            for story in self.story.get("story data"):
                if story["mode"] == "talk":
                    
                    exp = story.get('expression',"smile").lower().replace("evil smile", "evil")
                    if exp not in ["sad", "surprise", "evil", "shy", "angly", "smile"]:
                        exp = "smile"
                    #print(story)
                    image_key = self.get_image_key(story["charactor name"])
                    voice_key = self.get_voice_key(story["charactor name"], story["talk"])
                    f.write(f"changeFigure:{image_key}_{exp}.png -next;\n")
                    f.write(f"{story['display name']}:{story['talk']} -{voice_key}.mp3;\n")
                
                
                if story["mode"] == "player characters inner voice":
                    data = story.get("data", None)
                    if data:
                        f.write(f":{data};\n")
                
                if story["mode"] == "change background image":
                    image_key = self.get_image_key(story["data"])
                    f.write(f"changeBg:{image_key}.jpg -next;\n")
                
                if story["mode"] == "change bgm":
                    bgm_data = story.get("data")
                    if bgm_data:
                        #result = sound_selector.sound_selector(story['data'])
                        result = DataSelector(self.client).bgm(bgm_data)
                        f.write(f"bgm:{result}.mp3 -next;\n")
            
            choice_list = []
            for choice in self.choices:
                choice_list.append(f"{choice.user_choise}:{choice.uuid}.txt")
            f.write(f"choose:{'|'.join(choice_list)};\n")


def voice_worker(client, q):
    pg = VoiceGenerator()
    while True:
        item = q.get()
        print(f"Voice worker: {item}")
        if item is None:
            break
        if os.path.exists(item["file_name"]):
            q.task_done()
            print(f"Voice exists: {item['file_name']}")
            continue
        try:
            pg.save_voice(item["file_name"], item["voice_name"], item["text"])
        except Exception as e:
            print(f"Failed to save voice: {e}")
        q.task_done()

def image_worker(client, q):
    pg = PromptGenerator(client)
    while True:
        item = q.get()
        if item is None:
            break
        print(f"Image worker: {item}")
        if os.path.exists(item["file_name"]):
            q.task_done()
            print(f"Image exists: {item['file_name']}")
            continue
        bg_prompt = pg.get_background(item["image"])

        comfyui_client = None
        try:
            comfyui_client = ComfyUIClient("127.0.0.1:8188", "bgimage_api.json")
            comfyui_client.connect()
            comfyui_client.set_data(key='KSampler', seed=random.randint(0, 1000000))
            comfyui_client.set_data(key='Input Prompt', text=bg_prompt)
            for key, image in comfyui_client.generate(["Result Image"]).items():
                image.save(item["file_name"])
        finally:
            if comfyui_client is not None:
                comfyui_client.close()

        q.task_done()

def charactor_worker(client, q, server):
    pg = PromptGenerator(client)

    def _inwork(item):
        if os.path.exists(f"{item['file_name']}_smile.png"):
            q.task_done()
            print(f"Charactor exists: {item['file_name']}")
            return True
        print(f"Charactor worker: {item}")
        chara_prompt = pg.get_charactor(item["charactor"])
        face_prompt = pg.get_face(chara_prompt)
        
        comfyui_client = ComfyUIClient(server, "text2cast_api.json")
        comfyui_client.connect()
        comfyui_client.set_data(key='KSampler', seed=random.randint(0, 1000000))
        comfyui_client.set_data(key='Input Charactor Prompt', text=chara_prompt)
        comfyui_client.set_data(key='Input Face Prompt', text=face_prompt)

        used_poses = load_memory("used_poses list") or []
        while len(used_poses) > 10:
            used_poses.pop(0)
        pose_file = random.choice(pose_selector.get_pose_image(chara_prompt, used_poses))
        used_poses.append(pose_file)
        save_memory("used_poses list", used_poses)

        comfyui_client.set_data(key='Load Image', image=Image.open(pose_file))


        for key, image in comfyui_client.generate(["Result Smile", "Result Angly", "Result Shy", "Result Evil", "Result Surprise", "Result Sad"]).items():
            expression = key.replace("Result ", "").lower().strip()
            image.save(f"{item['file_name']}_{expression}.png")

        comfyui_client.close()

        return True

    while True:
        item = q.get()
        if item is None:
            break
        for _ in range(3):
            try:
                if _inwork(item):
                    q.task_done()
                    break
            except Exception as e:
                print(f"Failed to save charactor: {e}")
        else:
            print(f"Failed to save charactor: {item}")


def title_worker(client, q, server):
    pg = PromptGenerator(client)
    while True:
        item = q.get()
        print(f"Title worker")
        if item is None:
            break

        if os.path.exists(item["file_name"]):
            q.task_done()
            print(f"Title exists: {item['file_name']}")
            continue

        title_prompt = pg.get_title(item['data'])
        comfyui_client = ComfyUIClient(server, "titleimage_api.json")
        comfyui_client.connect()
        comfyui_client.set_data(key='KSampler', seed=random.randint(0, 1000000))
        comfyui_client.set_data(key='Prompt Input', text=title_prompt)

        for key, image in comfyui_client.generate(["Result Image"]).items():
            image.save(item["file_name"])
            print(f"Title saved: {item['file_name']}")
        
        comfyui_client.close()
        q.task_done()


def create_story(user_prompt):
    client = cohere.Client(os.getenv("COHERE_API_KEY"))

    root = StoryNode(client, story_prompt=user_prompt)
    root.generate()

    title = root.main_story.get('title english', root.main_story.get('title japanese')).replace(" ", "_")

    output_dir = f"output/{title}/"
    voice_dir = f"{output_dir}/game/vocal/"
    background_dir = f"{output_dir}/game/background/"
    charactor_dir = f"{output_dir}/game/figure/"
    bgm_dir = f"{output_dir}/game/bgm/"
    base_bgm_dir = f"BGM/"

    if not os.path.exists(output_dir):
        shutil.copytree("game_template", output_dir)
        shutil.copy("logo_with_ai.jpg", os.path.join(background_dir, "logo_with_ai.jpg"))
    
    scenario_dir = f"{output_dir}/game/scene/"
    print(f"Saving to {scenario_dir}")
    root.save(scenario_dir)
    print("Saved.")



    with open(os.path.join(scenario_dir, "start.txt"), "w", encoding="utf8") as f:
        f.write("intro:このゲームは、人が入力したコンセプトをベースに AI が自動作成したものです。 -hold;\n")
        f.write(f"changeScene:{root.uuid}.txt;\n")

    
    sound_queue = queue.Queue()
    image_queue = queue.Queue()
    title_queue = queue.Queue()
    chara_queue = queue.Queue()
    threads = []


    for _ in range(3):
        threads.append(threading.Thread(target=voice_worker, args=(client, sound_queue)))
    
    threads.append(threading.Thread(target=image_worker, args=(client, image_queue)))
    
    comfyui_servers = ["127.0.0.1:8188", ]
    for server in comfyui_servers:
        threads.append(threading.Thread(target=title_worker, args=(client, title_queue, server)))
        for _ in range(2):
            threads.append(threading.Thread(target=charactor_worker, args=(client, chara_queue, server)))

    for thread in threads:
        thread.start()
    

    title_queue.put({"file_name": f"{background_dir}/title.png", "data": root.main_story})

    #print(json.dumps(root.main_story, indent=4, ensure_ascii=False))
    #print(json.dumps(root.story, indent=4, ensure_ascii=False))

    def save_voices(story_node):
        for name, voice in story_node.get_voices().items():
            voice_file_path = os.path.relpath(os.path.abspath(f"{voice_dir}/{name}.mp3"))
            if os.path.exists(voice_file_path):
                continue
            if not voice.get("voice_name"):
                print(f"Voice name not found: {voice}")
                continue
            if not os.path.exists(voice_file_path) or os.path.getsize(voice_file_path) > 0:
                data = {"file_name": voice_file_path, "voice_name": voice.get("voice_name"), "text": voice.get("talk")}
                print(f"Queue Voice: {data}")
                sound_queue.put(data)
    
    def save_backgrounds(story_node):
        for name, image in story_node.get_backgrounds().items():
            image_file_path = os.path.relpath(os.path.abspath(f"{background_dir}/{name}.jpg"))
            if os.path.exists(image_file_path):
                continue
            data = {"file_name": image_file_path, "image": image}
            print(f"Queue Image: {data}")
            image_queue.put(data)
    
    def save_charactors(story_node):
        for name, val in story_node.get_charactors().items():
            charactor_file_path = f"{charactor_dir}/{name}"
            charactor_smile_file_path = os.path.relpath(os.path.abspath(f"{charactor_dir}/{name}_smile.png"))
            
            if os.path.exists(charactor_smile_file_path):
                continue
            data = {"file_name":charactor_file_path, "charactor":val}
            print(f"Queue Charactor: {data}")
            chara_queue.put(data)
        
    def save_bgm(story_node):
        print(f"Saving BGM: {story_node.get_bgm()}")
        for bgm in story_node.get_bgm():
            src_path = os.path.join(base_bgm_dir, bgm + ".mp3")
            dst_path = os.path.join(bgm_dir, bgm + ".mp3")
            if os.path.exists(dst_path) and os.path.getsize(dst_path) > 0:
                continue
            print(f"Copying BGM: {src_path} -> {dst_path}")
            if os.path.exists(src_path):
                shutil.copy(src_path, dst_path)
            else:
                print(f"File not found: {src_path}")
            
    
    save_voices(root)
    save_backgrounds(root)
    save_charactors(root)
    save_bgm(root)
    
    def recursive(node, level):
        if level == 0:
            return
        for choice in node.choices:
            choice.generate(elect_level=int(level % 2))
            choice.save(scenario_dir)
            #print(json.dumps(choice.story, indent=4, ensure_ascii=False))
            #print(json.dumps(choice.get_voices(), indent=4, ensure_ascii=False))
            recursive(choice, level-1)

            save_voices(choice)
            save_backgrounds(choice)
            save_charactors(choice)
            save_bgm(choice)
        
        time.sleep(0.1)
    
    recursive(root, 5)


    print("Waiting for threads to finish...")

    for _ in range(len(threads)):
        sound_queue.put(None)
        image_queue.put(None)
        chara_queue.put(None)
        title_queue.put(None)
    for thread in threads:
        thread.join()


def main():
    user_prompt = """
痴女だらけの異世界に転移してしまった主人公。その世界では結婚相手とのセックスでしか妊娠しない神の祝福がある上に、性病や怪我などは回復魔法や回復ポーション等で簡単に治療されるため、性行為に対しての敷居が低い。
その世界では女性の方が性欲が強く、男性がナンパされる事も日常的。日々、最高の相性の相手を探すため、性行為が行われる。文化の違いに戸惑う主人公だが、次第に欲望のままに性行為を楽しむ。
それと同時に、異世界に転移した原因の発見や、元の世界への戻り方の発見、異世界の女性との結婚などの選択も。
"""
    create_story(user_prompt)


if __name__ == "__main__":
    main()
