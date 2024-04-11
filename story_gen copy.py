import os
import pickle
import hashlib
import asyncio
import json
import anthropic

import comfyuitest
import sound_selector
import voice_engine
import voice_selector

from pickle_memory import load_memory, save_memory

from dotenv import load_dotenv
load_dotenv()


client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
)


output_dir = "game/game"


def fix_json(data:str) -> dict:
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        try:
            return eval(data)
        except:
            pass

    key = "fix_json:" + str(data)
    result = load_memory(key)
    if result:
        return result
    
    message = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=1000,
        temperature=0,
        system="You can fix errors in JSON data. Find and correct errors in the JSON input by the user, and output the correct data as JSON. Your own opinions, comments, and additions are not required. Please output only JSON data.",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": data
                    }
                ]
            }
        ]
    )
    result = json.loads(message.content[0].text)
    print(result)
    save_memory(key, result)
    return result


async def create_base_story(text):
    result = load_memory(text)
    if result:
        return result
    
    example_title = "異世界探検部。古い地図を手掛かりに異世界へ旅立ち冒険する。"
    
    example = """
{
"user input theme": "異世界探検部。古い地図を手掛かりに異世界へ旅立ち冒険する。",
"title_japanese": "異世界探検部",
"title_english": "Exploration Club of Another World",
"charactors":[
    {"charactor name":"田中太郎", "display name":"太郎", "appearance":"18歳、男性、黒髪で黒い目、ショートヘア、迷彩のズボンに白いシャツ", "personality":"普通の男子", "status":"健康", "player":"True", "voice":"普通の男性の声"},
    {"charactor name":"田中詩織", "display name":"詩織","appearance":"女の子、白いワンピース、赤いヘアピン、青い髪、ロングツインテール、赤い瞳", "personality":"正義感が強い", "Relationship with players":"顔見知り", "status":"右手を怪我している", "voice":"少女らしい透き通った声"},
    {"charactor name":"岡田龍平", "display name":"龍平","appearance":"男の子、学生服、緑の髪、ショートヘア、青い瞳", "personality":"気が弱い", "Relationship with players":"初対面", "status":"元気", "voice":"声変わりした低めの男性の声"},
    {"charactor name":"魔王グランディ", "display name":"魔王グランディ", "appearance":"200歳、女性、魔王、黒いロングヘア、禍々しいドレス、黒い翼、ツノが生えている", "personality":"心を病んでおり攻撃的", "Relationship with players":"初対面、敵対", "status":"力を貯めている", "voice":"低い女性の声"}
],
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
"ending conditions":[
    "True End: 主人公と仲間たちは異世界の真の脅威である魔王を突き止め、力を合わせてそれを打ち払います。平和を取り戻した異世界に別れを告げ、現実世界に戻ってきた彼らは、経験を胸に新たな冒険に旅立ちます。",
    "Bitter Sweet End: 魔王を倒し異世界の危機は去りましたが、犠牲も大きくありました。主人公は仲間を失った悲しみを乗り越え、その思い出を胸に現実世界で生きていくことを決意します。",
    "Revelation End: 異世界の探検を通して、主人公は自分自身の内面と向き合います。自分の弱さと向き合い、乗り越えていく中で、真の強さを手に入れていきます。",
    "Tragic End: 主人公は異世界で出会った特別な存在と深い絆を築きますが、世界の危機を前に、その存在は犠牲となってしまいます。深く心に傷を負いながらも、主人公は前を向いて生きていくことを誓います。",
    "Bad End: 主人公たちは異世界の危機を解決できず、現実世界に戻ることができません。異世界の闇に取り込まれ、永遠に閉ざされてしまいます。",
    "Secret End: 真のエンディングへの隠された道筋があります。探検を進め、隠されたヒントを集めることで、異世界の秘密を解き明かし、誰も知らない真実へとたどり着くことができるのです。",
    "Game Over: 主人公たちは異世界の危機に立ち向かいますが、その力不足を痛感し、敗北を味わいます。異世界は闇に包まれ、主人公たちはそのまま閉ざされてしまいます。",
    "Dream End: 異世界での冒険の末、主人公は目を覚まします。全ては夢だったのでしょうか。しかし、現実世界で仲間たちと再会した時、彼らも同じ夢を見ていたことが判明。夢と現実の狭間で、新たな謎が浮上します。"
]
}
"""

    message = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=4000,
        temperature=0,
        system=f"You are a screenwriter. You can write characters, scenarios, and endings according to the requested theme.\n\nThe output format is JSON. Specifically, it is as follows.\n\nUser input example: {example_title}\nExample of your output:\n{json.loads(example)}",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Theme: {text}"
                    }
                ]
            }
        ]
    )
    result = fix_json(message.content[0].text)

    save_memory(text, result)
    return result


async def create_story_continue(base_story: dict, synopsis=None, old_story=None, select_story=None, endinglevel=0, nocache=False):
    error_occured = False
    for n in range(3):
        try:
            result = await _create_story_continue(base_story, synopsis, old_story, select_story, endinglevel, error_occured or nocache)
            print(f"result len : {len(result)}")
            
            print(f"#base_story\n{base_story}\n\n#synopsis\n{synopsis}\n\n#old_story\n{old_story}\n\n#select_story\n{select_story}\n\n#endinglevel\n{endinglevel}\n\n")
            print(f"@@@\n{result}\n@@@")

            last_story = result[-1]
            if "end" in last_story:
                return result
            if "select1" in last_story:
                return result
        except Exception as e:
            print(f"create_story_continue: error: {e} ({type(e)}) ")

        await asyncio.sleep(5)
        print("retrying...")
        error_occured = True
    
    raise Exception("Failed to create story")


async def _create_story_continue(base_story: dict, synopsis=None, old_story=None, select_story=None, endinglevel=0, nocache=False):
    key = f"{base_story} {synopsis} {old_story} {select_story}"
    result = load_memory(key)

    if nocache:
        result = None

    if result:
        return result

    if synopsis is None:
        synopsis = "まだストーリーは始まったばかり"
    
    payload = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"# Input data\n{base_story}\n\n# Synopsis\n{synopsis}"
                    }
                ]
            }
    ]
    if old_story:
            payload.append({
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": f"{old_story}"
                    }
                ]
            })

            if select_story:
                payload.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"{select_story}"
                        }
                    ]
                })
    
    ending_message = ""
    if endinglevel == 0:
        ending_message = ""
    elif endinglevel == 1:
        ending_message = "* Please be aware of the ending that is closest to your current progress."
    elif endinglevel == 2:
        ending_message = "* Please write the story so that it progresses towards the ending closest to the current progress."
    elif endinglevel == 3:
        ending_message = "* Create choices for your players so that the story progresses towards the closest ending to their current progress."
    elif endinglevel >= 4:
        ending_message = "* Please make sure to connect the current story to one of the endings and finish the story."

    print(ending_message)

    example = """
[
{"background image":"日本、昼間、屋外、住宅街"},
{"sound effect":"スズメの鳴声、ちゅんちゅん"},
{"bgm":"快晴、明るい、楽しい、平和"},
{"sound effect":"女性の足音、ハイヒール、コツコツ"},
{"charactor name":"田中太郎", "display name":"太郎", "talk":"こんにちは！", "expression":"Smile"},
{"show charactor":"田中詩織"},
{"charactor name":"田中詩織", "display name":"詩織", "talk":"あら？こんにちは", "expression":"Shy"},
{"inner voice":"彼女は俺の幼馴染だ"},
{"charactor name":"田中詩織", "display name":"詩織", "talk":"あたし急いでるから", "expression":"Shy"},
{"hide charactor":"田中詩織"},
{"inner voice":"行ってしまった……"},
{"add charactor":{"charactor name":"リディア・マッカーソン", "display name":"リディア", "appearance":"180歳、女性、エルフ、金髪ロングヘア、", "personality":"優しい", "Relationship with players":"初対面", "status":"元気", "voice":"透き通った声"}},
{"sound effect":"コケる音。ドッシン！"},
{"charactor name":"リディア・マッカーソン", "display name":"？？？", "talk":"いったーい！", "expression":"Sad"},
{"charactor name":"田中太郎", "display name":"主人公", "talk":"え？誰？", "expression":"Surprise"},
{"charactor name":"リディア・マッカーソン", "display name":"リディア", "talk":"わたし？わたしはリディアよ！", "expression":"Smile"},
{"select1":"エルフをデートに誘う","select2":"家に帰る","select3":"UFOを見つける"}
]
"""
    example_ending = """
[
{"background image":"日本、昼間、屋外、住宅街"},
{"sound effect":"スズメの鳴声、ちゅんちゅん"},
{"bgm":"快晴、明るい、楽しい、平和"},
{"sound effect":"女性の足音、ハイヒール、コツコツ"},
{"charactor name":"田中太郎", "display name":"太郎", "talk":"こんにちは！", "expression":"Smile"},
{"show charactor":"田中詩織"},
{"charactor name":"田中詩織", "display name":"詩織", "talk":"あら？こんにちは", "expression":"Shy"},
{"inner voice":"彼女をどこかで出会った気がする……"},
{"charactor name":"田中詩織", "display name":"詩織", "talk":"ふふっ……", "expression":"Shy"},
{"hide charactor":"田中詩織"},
{"inner voice":"行ってしまった……"},
{"inner voice":"それ以降彼女とは二度と会う事はなかった……"},
{"end":"True End"}
]
"""
    additional_info = """
* inner voice is the main character's inner voice.
* Choose the facial expression that seems closest to character from among Sad, Surprise, Evil Smile, Shy, Angly, Normal and Smile.
* If you think the story has reached its ending, say what the player feels with {"inner voice": "Protagonist's feelings"} and add {"end": "Ending name"} at the end.
* "talk" performs the reading process as is. Never include acting instructions in the "talk" section.
* Take a close look at the output sample and remember that the output is in JSON format.
* Don't use text to explain your ethics or provide information about your story. Your output is only in JSON format and is what a direct JSON parser will read. If you provide supplementary information as text, the parser will generate an error and the game will end with an error.

""" + ending_message + "\n"

    choise_str = ", and at the end, be sure to output 3 options that are appropriate for the situation or that are unexpected"
    add_message = ""
    if endinglevel >= 4:
        example = example_ending
        choise_str = ""
        add_message = "This is a game scenario. If you need explicit sexual expression to express the story, prioritize the outcome of your choices and use soft expressions to end the game."


    system = f"""
# Order
Think of your story as a continuation of the story entered by the user.
Please output at least 40 to 50 pieces of the main character's inner voice and conversations between characters{choise_str}.
The output data is processed as JSON, so your explanation or impressions are not required.
{ending_message}

# Output format
{json.loads(example)}

# Additional infomation
{additional_info}
"""

    model = "claude-3-sonnet-20240229"
    if nocache:
        model = "claude-3-opus-20240229"
    message = client.messages.create(
        model=model,
        max_tokens=4000,
        temperature=0,
        system=system,
        messages=payload
    )

    print(f"--system---------------------------------------------------------------------")
    print(system)
    print(f"--payload---------------------------------------------------------------------")
    print(json.dumps(payload, indent=4, ensure_ascii=False))
    if nocache:
        print(f"--message--------------------------------------------------------------------")
        print(f"message: {message.content[0].text}")
    print(f"-----------------------------------------------------------------------")

    result = fix_json(message.content[0].text)
    save_memory(key, result)
    return result


async def create_synopsis(data):
    result = load_memory(data)
    if result:
        return result
    
    message = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=2000,
        temperature=0,
        system="あなたは情報の要約が得意です。ユーザーに渡されたストーリーの状態を要約してまとめます。各キャラクターごとに、持ち物、体の状態、心理状態、目的、お互いをどう思っているか、学んだ事を列挙してください。ストーリーの進行状態が分かるようにしてください。あなたの解説や感想は不要です。",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"{data}"
                    }
                ]
            }
        ]
    )
    result = message.content[0].text
    save_memory(data, result)
    return result


def search_select(story_data):
    select_values = []
    for item in story_data:
        for key, val in item.items():
            if "select" in key:
                select_values.append(val)
    return select_values


def delete_select(story_data):
    clone_story_data = story_data.copy()    
    for item in clone_story_data:
        if item is dict:
            for key, _ in item.items():
                if "select" in key:
                    clone_story_data.remove(item)
                    break
    return clone_story_data

tasks = []

class StoryNode:
    def __init__(self, base_story:dict, story_data:dict, next_synopsis:str, synopsis:str, level:int, number:int, selects: dict):
        self.base_story = base_story
        self.story_data = story_data
        self.next_synopsis = next_synopsis
        self.synopsis = synopsis
        self.level = level
        self.number = number
        self.selects = selects

    def __str__(self):
        return f"{hashlib.sha256(self.base_story.get('title_japanese', self.base_story.get('title')).encode()).hexdigest()}_{self.level:0000}_{self.number:0000}"
    
    async def save(self):
        global tasks

        if len(tasks) > 15:            
            print("Waiting for tasks to complete")
            await asyncio.gather(*tasks)
        else:
            # 他のタスクにも時間を回す
            await asyncio.sleep(0.1)

        # タスクの完了をチェック
        completed_tasks = []
        for task in tasks:
            if task.done():
                completed_tasks.append(task)

        # 完了したタスクを削除
        for task in completed_tasks:
            tasks.remove(task)
            
        
        end_flag = False
        with open(os.path.join(output_dir, "scene", f"{self}.txt"), "w", encoding='utf8') as f:
            f.write(f"changeFigure:none -left -next;\n")
            f.write(f"changeFigure:none -right -next;\n")
            f.write(f"changeFigure:none -next;\n")

            for tag in self.story_data:
                if "display name" in tag and "talk" in tag:
                    name_hash = hashlib.sha256((str(self.base_story)+tag['charactor name']).encode()).hexdigest()
                    talk_hash = hashlib.sha256((str(self.base_story)+tag['charactor name']+tag['talk']).encode()).hexdigest()

                    mp3_path = os.path.join(output_dir, "vocal", f"{talk_hash}.mp3")
                    if not os.path.exists(mp3_path) or os.path.getsize(mp3_path) == 0:
                        voice_name = load_memory(f"voice: {name_hash}")
                        print(f"voice name : {tag['charactor name']}: {voice_name}")

                        if voice_name is None or not voice_selector.exists_voice_name(voice_name):
                            used_voices = load_memory("used_voices", [])
                            voice_name = voice_selector.get_voice_name(tag['charactor name'], used_voices)
                            used_voices.append(voice_name)
                            save_memory("used_voices", used_voices)
                            save_memory(f"voice: {name_hash}", voice_name)

                        if voice_name is not None:
                            print(f"create task: voice name : {tag['charactor name']}: {voice_name}")
                            voice_task = asyncio.create_task(voice_engine.save_voice(mp3_path, voice_name, tag['talk']))
                            tasks.append(voice_task)

                    exp = tag.get('expression',"smile").lower().replace("evil smile", "evil")
                    if exp not in ["sad", "surprise", "evil", "shy", "angly", "smile"]:
                        exp = "smile"
                    f.write(f"changeFigure:{name_hash}_{exp}.png -next;\n")
                    f.write(f"{tag['display name']}:{tag['talk']} -{talk_hash}.mp3;\n")
                    continue
                if "show charactor" in tag:
                    f.write(f"changeFigure:none -next;\n")
                    continue
                if "hide charactor" in tag:
                    f.write(f"changeFigure:none -next;\n")
                    continue
                if "background image" in tag:
                    bg_hash = hashlib.sha256(tag['background image'].encode()).hexdigest()
                    bg_path = os.path.join(output_dir, "background", f"{bg_hash}.jpg")
                    if not os.path.exists(bg_path):
                        bg_image_task = asyncio.create_task(comfyuitest.gen_background(tag['background image'], bg_path))
                        tasks.append(bg_image_task)
                    f.write(f"changeBg:{bg_hash}.jpg -next;\n")
                    continue
                if "sound effect" in tag:
                    f.write(f"playEffect:{tag['sound effect']} -next;\n")
                    continue
                if "bgm" in tag:
                    result = sound_selector.sound_selector(tag['bgm'])
                    f.write(f"bgm:{result}.mp3 -next;\n")
                    continue
                if "inner voice" in tag:
                    f.write(f":{tag['inner voice']};\n")
                    continue
                if "add charactor" in tag:
                    print(f"add charactor: {tag}")
                    name_hash = hashlib.sha256((str(self.base_story)+tag.get('add charactor').get("charactor name")).encode()).hexdigest()
                    if not os.path.exists(os.path.join(output_dir, "figure", f"{name_hash}_smile.png")):
                        chara_task = asyncio.create_task(comfyuitest.gen_charactor(tag.get('add charactor').get("appearance"), os.path.join(output_dir, "figure"), name_hash))
                        tasks.append(chara_task)

                    used_voices_key = "used_voices"
                    used_voices = load_memory(used_voices_key, [])
                    voice_name = load_memory(f"voice: {name_hash}", None)
                    if voice_name is None or not voice_selector.exists_voice_name(voice_name):
                        voice_name = voice_selector.get_voice_name(tag.get('add charactor'), used_voices)
                        used_voices.append(voice_name)
                        save_memory(f"voice: {name_hash}", voice_name)
                
                    save_memory(used_voices_key, used_voices)

                    f.write(f";addCharactor:{tag['add charactor']};\n")
                    continue
                if "end" in tag:
                    f.write("end;\n")
                    f.write(f";{tag}")
                    end_flag = True
                    continue
            
            if not end_flag:
                select_data = []
                for select_key, select_value in self.selects.items():
                    select_data.append(f"{select_key}:{select_value}.txt")
                f.write(f"choose:{'|'.join(select_data)};\n")

        if end_flag:
            return None


async def recrusive_story(base_story, new_synopsis, old_synopsis, old_story, select_story, level, number) -> StoryNode:
    global tasks

    if level >= 8:
        return None

    node = None
    error_occured = False
    for n in range(3):
        try:
            story = list(await create_story_continue(base_story, old_synopsis, old_story, select_story, level - 3, error_occured))
            print(story)
            old_story2 = delete_select(old_story)
            story2 = delete_select(story)
            synopsis = f"# Setting:\n{base_story}\n\n# Synopsis:\n{old_synopsis}\n\n# Story:\n{old_story2}\n\n# Action:\n{select_story}\n\n# Story:{story2}"
            synopsis = await create_synopsis(synopsis)

            print(synopsis)

            node = StoryNode(base_story, story, new_synopsis, old_synopsis, level, number, {})
            print(node.story_data)
            if "end" in node.story_data[-1]:
                await node.save()
                return node

            select_values = search_select(story)
            num = number * 10
            for select_value in select_values:
                next_node = await recrusive_story(base_story, synopsis, new_synopsis, story, select_value, level + 1, num)
                node.selects[select_value] = next_node
                num += 1
            
            await node.save()

            break
        except AttributeError as e:
            print(f"recrusive_story: error: {e}")
            error_occured = True
            await asyncio.sleep(5)
            continue

    return node


async def story_gen(text):
    global tasks

    base_story = await create_base_story(text)

    with open(f'{base_story.get("title_japanese", base_story.get("title"))}.txt', "w", encoding="utf8") as f:
        f.write(json.dumps(base_story, ensure_ascii=False, indent=4))

    story_titles = load_memory("story_titles", [])
    story_title = base_story.get("title_japanese", base_story.get('title'))
    if story_title not in story_titles:
        story_titles.append(story_title)
    save_memory("story_titles", story_titles)
    save_memory("used_poses", [])
    used_voices_key = f"used_voices"
    save_memory(used_voices_key, [])

    print(base_story)

    used_voices = []

    for charactor in base_story.get("charactors", {}):
        print(charactor)
        
        name_hash = hashlib.sha256((str(base_story)+charactor.get("charactor name")).encode()).hexdigest()
        if os.path.exists(os.path.join(output_dir, "figure", f"{name_hash}_smile.png")):
            continue
        chara_task = asyncio.create_task(comfyuitest.gen_charactor(charactor.get("appearance"), os.path.join(output_dir, "figure"), name_hash))
        tasks.append(chara_task)

        voice_name = load_memory(f"voice: {name_hash}", None)
        if voice_name is None:
            voice_name = voice_selector.get_voice_name(charactor, used_voices)
            print(f"voice name : {charactor.get('charactor name')}: {voice_name}")
            if voice_name is None:
                raise Exception(f"Voice name is None: {charactor.get('charactor name')} / {used_voices}")

            used_voices.append(voice_name)
            save_memory(f"voice: {name_hash}", voice_name)
    
    save_memory(f"used_voices", used_voices)

    first_story = await create_story_continue(base_story, None, None, None)
    print(first_story)

    first_node = StoryNode(base_story, first_story, "まだストーリーは始まったばかり", "まだストーリーは始まったばかり", 0, 0, {})

    select_values = search_select(first_story)
    num = 0
    for select_value in select_values:
        print(f"\n\n -> {select_value}\n\n")
        node = await recrusive_story(base_story, None, None, first_story, select_value, 1, num)
        first_node.selects[select_value] = node
        num += 1

    print("Saving first node")    
    await first_node.save()

    print("Waiting for tasks to complete")
    await asyncio.gather(*tasks)

    
    print(first_node)

    with open(os.path.join(output_dir, "scene", "start.txt"), "w", encoding="utf8") as f:
        added = ["サキュバスの誘惑", "ねこの王国と魔法の地図", "ギャル達の秘密"]
        data = []
        for story_title in story_titles:
            if not story_title or story_title in added:
                continue
            added.append(story_title)
            data.append(f"{story_title}:{hashlib.sha256(story_title.encode()).hexdigest()}_0_0.txt")
        f.write("intro:このゲームは、人が入力したコンセプトをベースに AI が自動作成したものです。|AI による文字の読み間違いや、設定のブレや、画像のミスマッチなどが起こり得ます。|テスト中のため、シナリオは最後まで生成されず、ストーリは途中で停止しますので、予めご了承ください。 -hold;\n")
        f.write("choose:" + "|".join(data) + ";\n")
    
    print("Done")


async def main():
    #text = "ねこの王国と魔法の地図 - 魔法の地図を手に入れた主人公が、ねこの王国を目指して冒険の旅に出発。個性豊かなねこたちとの出会いと別れを通して、真の友情と勇気を学んでいく物語。"
    text = "サキュバスがあふれる世界に転移してしまった。この世界では彼女達によって達してしまう事と死んでしまう事を知り、あらゆる誘惑を跳ねのけて元の世界に戻らなければならない。性表現が必要な場面は即エンディングとなる。露骨な性表現は不要。"
    #text = "なぜかギャルだらけの女子高に転校が決まってしまい、ギャルの中でも特に人気のあるギャル達に囲まれることになる。主人公が男子である事をいい事にからかわれたりしつつ、ギャル達との交流を通し、主人公は彼女達の本当の姿を知ることになる。"
    await story_gen(text)


if __name__ == "__main__":
    asyncio.run(main())



