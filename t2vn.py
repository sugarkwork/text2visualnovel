import os
import json
import ast

import cohere
from cohere.core.request_options import RequestOptions
from pickle_memory import load_memory, save_memory
from dotenv import load_dotenv
load_dotenv()

import json_repair


API_TIMEOUT_SEC = 60 * 5


co = cohere.Client(os.getenv("COHERE_API_KEY"))


class JsonUtils:
    @staticmethod
    def normal_parse(text:str) -> dict:
        try:
            return json.loads(text)
        except json.decoder.JSONDecodeError:
            pass

        try:
            return ast.literal_eval(text)
        except (Exception, SyntaxError):
            pass
        
        try:
            return eval(text)
        except (Exception, SyntaxError):
            pass

        raise json.decoder.JSONDecodeError("Failed to parse JSON format", text, 0)
    
    @staticmethod
    def trim_json(text:str) -> str:
        if not text.startswith("[") and not text.startswith("{") and not text.startswith("\""):
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
                return text
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]
                return text        
        return None
    
    @staticmethod
    def fix_json(text:str) -> str:
        lines = text.split("\n")
        for i, line in enumerate(lines):
            line = line.strip()
            if (not line.startswith("\"") and (line.endswith("\"") or line.endswith("\","))) or (line.startswith("\"") and not (line.endswith("\"") or line.endswith("\","))):
                line_temp = line.strip().strip("\"").strip()
                lines[i] = f"\"{line_temp}\","
            if line.startswith("「") and (line.endswith("」，") or line.endswith("」、") or line.endswith("」,") or line.endswith("」")):
                lines[i] = line.replace("「", "\"").replace("」", "\"").replace("：", ":")
            
        return "\n".join(lines)

    @staticmethod
    def json_format(text:str) -> dict:
        # try nomal parse
        try:
            return JsonUtils.normal_parse(text)
        except json.decoder.JSONDecodeError:
            pass

        try:
            return json_repair.loads(text)
        except Exception:
            pass
        
        # try trim and parse
        trim_text = ""
        try:
            trim_text = JsonUtils.trim_json(text)
            if trim_text:
                return JsonUtils.json_format(trim_text)
        except Exception:
            pass

        if trim_text:
            try:
                return json_repair.loads(trim_text)
            except Exception:
                pass
    
        # try fix and parse
        fix_text = ""
        try:
            fix_text = JsonUtils.fix_json(text)
            if text != fix_text:
                return JsonUtils.json_format(fix_text)
        except Exception:
            pass

        if fix_text:
            try:
                return json_repair.loads(fix_text)
            except Exception:
                pass

        # raise error
        print (f"Failed to parse JSON format: {text}")
        raise ValueError("Failed to parse JSON format")


def get_text(system, text, nocache=False):
    key = f"get_text: system={system} , text={text}"
    cached = load_memory(key)
    if nocache:
        cached = None
    if cached is not None:
        return cached
    
    key2 = f"get_text response: {system} {text}"
    response = load_memory(key2)
    if not response:
        response = co.chat(
            preamble=f"## Order\n{system}",
            message=f"## User Input\n{text}",
            model="command-r-plus",
            request_options = RequestOptions(timeout_in_seconds=API_TIMEOUT_SEC)
        ).text
        save_memory(key2, response)
    
    save_memory(key, response)
    return response


def get_json(system, format_sample, text):
    key = f"get_json: system={system}, format_sample={format_sample} text={text}"
    cached = load_memory(key)
    if cached is not None:
        return cached
    
    nocache = False
    response = None
    for _ in range(3):
        try:
            response = get_text(system, f"""
{text}

## Output JSON format
```json
{format_sample}
```
""", nocache=nocache)
            response = JsonUtils.json_format(response)
            break
        except Exception as e:
            print(f"Failed to get response: {e}")
            nocache = True
    else:
        raise ValueError(f"Failed to get response: system={system}, text={text}, response={response}")
    
    save_memory(key, response)
    return response


prompt_story_generator = "You are a genius AI who comes up with stories and settings that attract people. You can come up with creative and engaging stories that cater to your users' wishes based on the themes and settings they enter. You will answer the title of the work, the world setting of the story, the background setting of the story, and the beginning of the story based on the theme and setting specified by her user."
prompt_json_converter = 'You can respond to user inquiries in perfect JSON format without errors. Your response will not include any comments and will always start with "``json\n" on the first line. Make sure to extract user input without summarizing it and preserve as much detail as possible when converting to JSON format. If information is missing, enter the estimated data so that the data does not become None.'
prompt_story_general = "You are a genius AI who comes up with stories and settings that are appealing to people. Based on the themes and settings entered by the user, you can come up with creative and engaging stories to meet the user's wishes. "
prompt_novelist = "You are a highly skilled game engine for visual novel games. Based on the themes and settings specified by the user, you can write game dialogue and scene descriptions while being mindful of the narrative structure of \"introduction, development, twist, and conclusion.\" You are exceptionally skilled at writing, allowing you to create sensual or emotionally moving descriptions of scenes and character dialogues. Always output what the protagonist saw and heard, like a recorder."


def generate_story(theme:str, lang="japanese") -> tuple[str, dict]:
    lang = lang.lower().strip()
    main_story = get_text(prompt_story_generator, theme)
    story_json_format = {
        "title": [{"title":"story title (english title)", "lang":"english"}],
        "world_setting": ["setting1", "setting2", "setting3"],
        "background_setting": ["setting1", "setting2", "setting3"],
        "introduction": "story introduction"
    }
    if lang != "english":
        story_json_format["title"].append({"title":f"story title ({lang} title)", "lang":lang})
    
    story_json_format = json.dumps(story_json_format, indent=4, ensure_ascii=False)

    main_story_json = get_json(prompt_json_converter, story_json_format, main_story)

    return main_story, main_story_json


def generate_settings(main_story:str, happy=3, normal=3, bad=3) -> tuple[str, dict]:
    prompt_settings = []
    prompt_settings.append("- ALL Character settings (name, age, appearance, personality, background)")
    prompt_settings.append("- Setting the story introduction")

    if happy:
        prompt_settings.append("- {happy} happy endings")
    if normal:
        prompt_settings.append("- {normal} normal endings")
    if bad:
        prompt_settings.append("- {bad} bad endings")
    
    tmp_settings = '\n'.join(prompt_settings)
    prompt = f"""With the following story settings,
{tmp_settings}

Please think about it.

## Story settings
{main_story}"""

    story_settings = get_text(prompt_story_general, prompt)

    story_settings_json_format = {
    "all_character_settings": [
        {"name": "character name1", "age": "character", "appearance": "character appearance", "personality": "character personality", "background": "character background"},
        {"name": "character name2", "age": "character", "appearance": "character appearance", "personality": "character personality", "background": "character background"},
        {"name": "character name3", "age": "character", "appearance": "character appearance", "personality": "character personality", "background": "character background"},
    ],
    "story_introduction": "story introduction"
}

    if happy:
        story_settings_json_format["happy_endings"] = [f"ending{n+1}" for n in range(happy)]
    if normal:
        story_settings_json_format["normal_endings"] = [f"ending{n+1}" for n in range(normal)]
    if bad:
        story_settings_json_format["bad_endings"] = [f"ending{n+1}" for n in range(bad)]
    
    story_settings_json_format = json.dumps(story_settings_json_format, indent=4, ensure_ascii=False)

    story_settings_json = get_json(prompt_json_converter, story_settings_json_format, story_settings)
    
    return story_settings, story_settings_json


def generate_chapter(story:str, settings:str, ending:str, chapter_count=5):
    if chapter_count < 3:
        chapter_count = 3

    chapter_dict = {
        1: "one chapter",
        2: "two chapters",
        3: "three chapters",
        4: "four chapters",
        5: "five chapters",
        6: "six chapters",
        7: "seven chapters",
        8: "eight chapters",
        9: "nine chapters",
        10: "ten chapters",
    }
    
    prompt = f"""
Divide the following story information into {chapter_dict.get(chapter_count, 'more than 10 chapters')}, and come up with chapter titles, chapter contents, and a list of scenes within each chapter.

## Story
{story}

## Settings
{settings}

## Ending
{ending}
"""
    
    chapter = get_text(prompt_story_general, prompt)
    
    chapter_json_format = """
{
"chapters":[
    {
        "title": "chapter title 1",
        "summary": "chapter summary",
        "scenes": [
            "scene1: scene description",
            "scene2: scene description",
            "scene3: scene description"
        ]
    },
    {
        "title": "chapter title 2",
        "summary": "chapter summary",
        "scenes": [
            "scene1: scene description",
            "scene2: scene description",
            "scene3: scene description"
        ]
    }
]
}
"""    
    chapter_json = get_json(prompt_json_converter, chapter_json_format, chapter)

    return chapter, chapter_json


def generate_chapter_novel(story:str, settings:str, chapters:dict, chapter_number=0, lang="japanese"):
    if chapter_number < 0:
        chapter_number = 0
    
    chapter_string = ""

    if chapter_number == 0:
        chapter_string = f"""## Chapters
{chapters[chapter_number]}"""
        
    if chapter_number >= 1:
        chapter_string = f"""## Old Chapters
{chapters[:chapter_number]}

## Chapters
{chapters[chapter_number]}
"""

    prompt = f"""
## Story
{story.replace('##', "")}

## Settings
{settings.replace('##', "")}

{chapter_string}

## Output language
{lang}

## Order
Please write the text for the visual novel game based on the content of the specified chapter.

# Format
The conversation will be written in a script-like format. The character name is followed by a colon and their dialogue. Parentheses are used for the protagonist's inner thoughts and monologues.

# Perspective
The story is told from a first-person perspective centered around the protagonist. The protagonist's inner thoughts are expressed in the first person within parentheses.

# Points to Note
As the conversation is colloquial, please use onomatopoeia such as inversion.
Use the protagonist's inner voice to reveal their motivations, doubts, and decision-making process, and use conversation to reveal the characters' personalities, relationships, and conflicts.
Instead of just explaining the results of events, express everything that happened through conversation or monologue.
Please have at least 20 over conversations per scene.

# IMPORTANT
Never forget to write from a main character's first person point of view.

# Sample (The protagonist is Kenta)
Kenta: Village Chief, please tell me more about the missing cats.
Village Chief: Well... First of all, it's only young cats that have gone missing.
Village Chief: They used to go out of the village for hunting and adventures and come back, but in the past few weeks, some of them haven't returned.
Mike: That's definitely unusual. They may have gotten involved in some kind of incident.
Village Chief: Actually, it seems that the missing cats were searching for the way to the Cat Kingdom.
Kenta: What?! The Cat Kingdom!?
Kenta: (Could it be that the missing cats were also aiming for the Cat Kingdom...!)
"""

    return prompt

    chapter_novel = get_text(prompt_novelist, prompt)

    return chapter_novel

def main():
    theme = """痴女だらけの異世界に転移してしまった主人公。その世界では結婚相手とのセックスでしか妊娠しない神の祝福がある上に、性病や怪我などは回復魔法や回復ポーション等で簡単に治療されるため、性行為に対しての敷居が低い。
その世界では女性の方が性欲が強く、男性がナンパされる事も日常的。日々、最高の相性の相手を探すため、性行為が行われる。文化の違いに戸惑う主人公だが、次第に欲望のままに性行為を楽しむ。
それと同時に、異世界に転移した原因の発見や、元の世界への戻り方の発見、異世界の女性との結婚などの選択を迫られる。"""

    happy = 1
    normal = 0
    bad = 1
    chapter_count = 3
    output_lang = "japanese"

    main_story, main_story_json = generate_story(theme, lang=output_lang)
    print(main_story)
    print(json.dumps(main_story_json, indent=4, ensure_ascii=False))

    story_settings, story_settings_json = generate_settings(main_story, happy=happy, normal=normal, bad=bad)
    print(json.dumps(story_settings_json, indent=4, ensure_ascii=False))

    chapters, chapters_json = generate_chapter(main_story, story_settings, story_settings_json["happy_endings"][0], chapter_count=chapter_count)
    print(chapters)
    print(json.dumps(chapters_json, indent=4, ensure_ascii=False))

    print("Base story generated")

    print(chapters_json["chapters"][0]["title"])

    chapter_novel = generate_chapter_novel(main_story, story_settings, chapters_json["chapters"], chapter_number=0, lang=output_lang)
    print(chapter_novel)

    print("Done")



if __name__ == "__main__":
    main()

