import os
import re
import anthropic
import copy


client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
)

poses_dir = 'poses'

def get_pose_image(theme, exclude_pose_list=None):
    # Get the list of files in the poses directory
    file_list = os.listdir(poses_dir)

    key_id = {}
    tag_files = []

    # Iterate over each file
    for file_name_org in file_list:
        # Remove the file extension
        file_name = os.path.splitext(file_name_org)[0]
        
        # Remove the characters enclosed in parentheses
        file_name = re.sub(r'\([^()]*\)', '', file_name)
        
        # Split the file name using underscores
        tags = file_name.replace('、', '_').replace(' ', '').split('_')
        sorted(tags)
        
        key = str(tags)
        if key not in key_id:
            key_id[key] = {'files':[], 'tags':tags}
        
        key_id[key]['files'].append(poses_dir + '/' + file_name_org)

    
    # Deep clone the key_id dictionary
    key_id_clone = copy.deepcopy(key_id)

    if exclude_pose_list:
        for exclude_pose in exclude_pose_list:
            file_name = os.path.basename(exclude_pose)
            file_name = os.path.splitext(file_name)[0]
            file_name = re.sub(r'\([^()]*\)', '', file_name)
            tags = file_name.replace('、', '_').replace(' ', '').split('_')
            sorted(tags)
            key = str(tags)
            if key in key_id:
                del key_id_clone[key]
        key_id = key_id_clone

    for key, value in key_id.items():
        tag_files.append(value)
   
    lines = []

    for index, value in enumerate(tag_files):
        lines.append(f"ID: {index}, Tags: {value['tags']}")
    
    line_data = '\n'.join(lines)
    #print(line_data)

    message = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=100,
        temperature=0,
        system=f"# Order\nYou are a character designer.\nBased on the theme requested by the customer, consider the pose the character should take based on the character's personality and appearance, and select one from the pose list. Please do not output your thoughts or supplementary information, just tell us the pose ID number. Be sure to start the output with \"Pose ID:...\".\n\n# Pose List\n{line_data}",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Theme:\n{theme}"
                    }
                ]
            }
        ]
    )
    result = message.content[0].text
    if "\n" in result:
        result = result.split("\n")[0]
    pose_num = int(result.replace('Pose ID:', '').strip())

    return tag_files[pose_num]['files']


if __name__ == "__main__":
    pose_files = get_pose_image('{"charactor name":"田中詩織", "display name":"詩織","appearance":"女の子、白いワンピース、赤いヘアピン、青い髪、ロングツインテール、赤い瞳", "personality":"正義感が強い", "Relationship with players":"顔見知り", "status":"右手を怪我している", "voice":"少女らしい透き通った声"}')
    print(pose_files)

