import os
import asyncio
import aiohttp
import io
from pydub import AudioSegment


async def get_model_id_by_name(server_addr, name):
        print(f"Getting model id by name: {server_addr}, {name}")
        if name is None:
            raise ValueError("Model name is required")
        name = name.strip()
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{server_addr}/models/info') as response:
                data = await response.json()
                for model_id, model_info in data.items():
                    model_name = model_info.get('config_path').split("\\")[1]
                    if name == model_name:
                        return model_id
                    
        raise ValueError(f"Model not found: '{name}'")

async def process_text(name, text) -> io.BytesIO:
    async with aiohttp.ClientSession() as session:
        server = 'http://localhost:5000'

        try:
            model_id = await get_model_id_by_name(server, name)

            url = f"{server}/voice"
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

            async with session.post(url, params=params, headers=headers) as response:
                if response.status == 200:
                    sound = AudioSegment.from_wav(io.BytesIO(await response.read()))
                    mp3_data = io.BytesIO()
                    sound.export(mp3_data, format="mp3")
                    mp3_data.seek(0)
                    return mp3_data
                else:
                    print(f"Request failed with status code: {response.status}")
        except asyncio.TimeoutError:
            print(f"Request to {server} timed out. Retrying...")
        except aiohttp.ClientError as e:
            print(f"Request to {server} failed: {e}. Retrying...")


async def save_voice(filename, name, text):
    print(f"Saving voice to {filename}, name: {name}, text: {text}")
    mp3_data = await process_text(name, text)
    with open(filename, "wb") as f:
        f.write(mp3_data.read())

