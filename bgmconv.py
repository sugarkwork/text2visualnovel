import os
import hashlib
import shutil
import json
import re
from pickle_memory import load_memory, save_memory
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(api_key=os.getenv('API_KEY'))


input_directory = "BGM_nsfw"  # Replace with the path to your directory
dest_directory = "BGM"

if not os.path.exists(dest_directory):
    os.makedirs(dest_directory)

all_data = []
all_hash = []
hash_key = {}

for file in os.listdir(input_directory):
    if file.endswith(".mp3"):
        file_name = os.path.splitext(file)[0]  # Get the file name without extension
        print(file_name)
        file_parts = file_name.split("-")  # Split the file name by hyphen

        title = file_parts[1].strip()  # Get the title

        sub_parts = file_parts[0].split("_")  # Split each part by underscore
        tags = []
        for sub_part in sub_parts:
            tag = sub_part.strip()
            if tag:
                tags.append(tag)  # Remove leading and trailing whitespaces
        
        file_path = os.path.join(input_directory, file)  # Get the full file path
        with open(file_path, 'rb') as f:
            file_data = f.read()  # Read the file data

        hash_object = hashlib.md5(file_data)  # Create a SHA256 hash object
        file_hash = hash_object.hexdigest()  # Get the hexadecimal representation of the hash

        all_hash.append(file_hash)

        print("File Hash:", file_hash)
        
        new_file_path = os.path.join(dest_directory, file_hash + ".mp3")  # Create the new file path
        shutil.copy(file_path, new_file_path)  # Copy the file to the destination directory

        new_json_file_path = os.path.join(dest_directory, file_hash + ".json")  # Create the new file path

        json_data = {"title": title, "tags": tags, "hash": file_hash}

        all_data.append(json_data)
        hash_key[file_hash] = json_data


def convert(input_data:list) -> list:
    cache_key = f'convert {input_data}'
    result = load_memory(cache_key)
    if not result:
        response = client.chat.completions.create(
            model="gpt-4-0125-preview",
            messages=[
                {"role": "system", "content": "You are a json data translator. You can interpret the user's json data appropriately. Please translate to English. lease output in the same JSON format as the input source format."},
                {"role": "user", "content": str(input_data)},
            ],
        )
        message = response.choices[0].message
        result = message.content
        save_memory(cache_key, result)
    print("----")
    print(result)
    try:
        result_data = json.loads(result)
    except (json.JSONDecodeError, json.decoder.JSONDecodeError) as e:
        # Use regular expressions to fix the JSON format
        result = re.sub(r'```json(.*?)```', r'\1', result, flags=re.DOTALL)
        result = re.sub(r'[\n\t]', '', result)
        result_data = json.loads(result)
    print("----")
    print(result)
    print("----")
    result_data = json.loads(result)
    return result_data

def convert_all(input_json:list) -> dict:
    key = 'convert_all_cache_data'
    cache = load_memory(key, {})
    input_data = []
    input_hash = {}
    for data in input_json:
        if data['hash'] not in cache:
            input_data.append(data)
            input_hash[data['hash']] = data
    print("Input Data:", input_data)
    work_data = convert(input_data)
    for data in work_data:
        cache[data['hash']] = data
    rework_data = []
    for hash in input_hash:
        if hash not in cache:
            rework_data.append(input_hash[hash])
    save_memory(key, cache)
    print("Rework Data:", rework_data)
    rework_result = {}
    if len(rework_data) > 1:
        rework_result = convert_all(rework_data)
    if isinstance(rework_result, dict):
        cache.update(rework_result)
    return cache

# Define all_data appropriately
all_data = convert_all(all_data)
print(all_data)

new_json_file_path = os.path.join("./", "bgm_data.json")  # Create the new file path

with open(new_json_file_path, 'w') as json_file:
    json.dump(all_data, json_file, sort_keys=True, ensure_ascii=False) 

print(all_data)
