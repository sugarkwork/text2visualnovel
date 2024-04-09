import os
import anthropic
from pickle_memory import save_memory, load_memory

client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
)

def get_voice_name(theme, exclude_voice_list=None):
    key = f"voice_selector result : {theme}, {exclude_voice_list}"
    result = load_memory(key)
    if result:
        return result
    
    temp_voice_list = []
    with open('voice_list.txt', 'r', encoding='utf8') as f:
        for voice in f.read().splitlines():
            voice_csv = voice.split(',')
            voice_name = voice_csv[0].strip()
            voice_tags = voice_csv[1].strip().split('|')
            if exclude_voice_list and voice_name in exclude_voice_list:
                continue
            temp_voice_list.append({'name': voice_name, 'tags': voice_tags})

    print(temp_voice_list)

    message = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1000,
        temperature=0,
        system=f"# Order\nYou are a character designer.\nBased on the theme requested by the customer, you select one voice list from the character setting data, considering the best voice for the character. Please do not output your thoughts or supplementary information, just tell us the voice name from the voice list. Be sure to start the output with \"Voice name:...\".\n\n\n# Voice list\n{temp_voice_list}",
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
    result = message.content[0].text.replace('Voice name:', '').strip()
    save_memory(key, result)
    return result


if __name__ == '__main__':
    print(get_voice_name('かわいらしい女の子', exclude_voice_list=['Anneli']))
