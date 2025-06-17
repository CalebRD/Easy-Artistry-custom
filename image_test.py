# -----------------------------------------------------------------------------
# 文件名：generate_image.py
# 功能：使用 DALL·E 生成图像，并把返回的 URL 打印出来
# -----------------------------------------------------------------------------

from openai import OpenAI
from dotenv import load_dotenv
import os
import webbrowser  # 可选，用于直接在浏览器打开结果图

def load_api_key():
    load_dotenv()  # 加载根目录下的 .env
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("请在 .env 中设置 OPENAI_API_KEY。")
    return key

def generate_image(prompt: str, n: int = 1, size: str = "512x512"):
    """
    调用 OpenAI Images API 生成图像，返回一个图像 URL 列表。
    """
    # 1. 创建客户端
    client = OpenAI(api_key=load_api_key())

    # 2. 发起图像生成请求
    resp = client.images.generate(   # images.generate 即对应 /v1/images/generations
        prompt=prompt,
        n=n,
        size=size,
        response_format="url"        # 也可以设为 "b64_json"
    )

    # 3. 提取并返回 URL
    urls = [item.url for item in resp.data]
    return urls

if __name__ == "__main__":

    prompt = "白发女孩，穿着蓝色连衣裙，站在樱花树下，微笑着看向前方，背景是晴朗的天空和飘落的樱花花瓣。"
    urls = generate_image(prompt, n=2, size="1024x1024")
    print("生成的图像 URL：")
    for idx, u in enumerate(urls, 1):
        print(f"{idx}. {u}")
        # 自动在浏览器打开（可选）
        webbrowser.open(u)
