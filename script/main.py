from urllib.parse import urlparse
import requests
import os
import json

def download_images_from_json(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
        for item in json_data:
            image_url = item["subject"]["pic"]["normal"]
            image_name = os.path.basename(urlparse(image_url).path)  # 使用图片链接的最后一个路径部分作为文件名
            download_image(image_url, image_name)

def download_image(url, filename):
    response = requests.get(url)
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"Image downloaded successfully: {filename}")
    else:
        print(f"Failed to download image: {url}")

def main():
    json_file = "script/movie.json"  # 替换为你的JSON文件路径
    download_images_from_json(json_file)

if __name__ == "__main__":
    main()
