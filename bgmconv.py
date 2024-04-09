import os
import hashlib
import shutil
import json


input_directory = "BGM"  # Replace with the path to your directory
dest_directory = "game/game/bgm"

all_data = []

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

        hash_object = hashlib.sha256(file_data)  # Create a SHA256 hash object
        file_hash = hash_object.hexdigest()  # Get the hexadecimal representation of the hash

        print("File Hash:", file_hash)
        
        new_file_path = os.path.join(dest_directory, file_hash + ".mp3")  # Create the new file path
        shutil.copy(file_path, new_file_path)  # Copy the file to the destination directory

        new_json_file_path = os.path.join(dest_directory, file_hash + ".json")  # Create the new file path

        json_data = {"title": title, "tags": tags, "hash": file_hash}

        all_data.append(json_data)

new_json_file_path = os.path.join("./", "all_data.json")  # Create the new file path

with open(new_json_file_path, 'w') as json_file:
    json.dump(all_data, json_file) 

print(all_data)
