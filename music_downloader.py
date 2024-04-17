import os
import re
from pickle_memory import save_memory, load_memory
from selenium import webdriver
import time
import bs4
import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import json

url="""\
https://musmus.main.jp/music_img5.html

"""

urls = url.split("\n")

driver = None

def get_page(url):
    global driver
    result = load_memory(url)
    if result:
        return result
    
    if not driver:
        driver = webdriver.Chrome()
    driver.get(urls[0])
    page_source = driver.page_source
    save_memory(url, page_source)
    return page_source

page = get_page(urls[0])
#page = page.replace('fas fa-tag', 'fas_fa_tag')


soup = bs4.BeautifulSoup(page, "html.parser")
results = []

# class="music-card clearfix"の要素を取得
music_cards = soup.select('.music-card.clearfix')

for card in music_cards:
    title = card.find('h3', class_='music-title').text
    
    tag_items = card.find_all('div', class_='d-item')
    tags = []
    for item in tag_items:
        if item.find('div', class_='d1').find('i', class_='fas fa-tag'):
            tags = [li.text.strip() for li in item.find('div', class_='d2').find_all('li')]
            tags = [tag for tag in tags if tag]  # 空の要素を削除
            break
    
    result = {"title": title, "tags": tags}
    results.append(result)

#print(results)

for result in results:
    print("_".join(result["tags"]) + " - " + result["title"])
    print("")


def sanitize_filename(filename):
    # Windows のファイル名に使用できない文字列のパターン
    invalid_chars = r'[<>:"/\\|?*]'
    
    # 無効な文字列を削除または置換
    sanitized_filename = re.sub(invalid_chars, '', filename)
    
    return sanitized_filename


# 監視対象のフォルダパス
folder_path = "C:/Users/shise/Downloads"

old_files = set(os.listdir(folder_path))

index = 0
while True:
    time.sleep(1)

    # フォルダ内のファイル一覧を取得
    files = set(os.listdir(folder_path))
    # 追加されたファイルを取得
    new_files = list(files - old_files)

    if not new_files:
        continue
    
    files = set(os.listdir(folder_path))
    new_files = list(files - old_files)
    
    select_file = ""

    for new_file in new_files:
        # ファイルが追加された場合
        file_name = new_files[0]
        file_ext = os.path.splitext(file_name)[1]

        if file_ext.lower().endswith("mp3"):
            select_file = new_file
            break
    else:
        old_files = files
        continue
    
    file_name = select_file
    file_ext = os.path.splitext(file_name)[1]

    result = results[index]
    new_file_name = sanitize_filename("_".join(result["tags"]) + " - " + result["title"] + file_ext)

    print(f"Rename {file_name} to {new_file_name}")
    try:
        os.rename(f"{folder_path}/{file_name}", f"{folder_path}/{new_file_name}")
    except:
        print("Error")

    old_files = set(os.listdir(folder_path))

    index += 1
    if index >= len(results):
        break


    time.sleep(1)
