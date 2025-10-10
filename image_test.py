# -----------------------------------------------------------------------------
# Filename: generate_image.py
# Purpose: Generate images using DALL·E and print returned URLs
# -----------------------------------------------------------------------------

from openai import OpenAI
from dotenv import load_dotenv
import os
import webbrowser  # optional, used to open result images directly in a browser

def load_api_key():
    load_dotenv()  # load .env from the repository root
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("Please set OPENAI_API_KEY in .env.")
    return key

def generate_image(prompt: str, n: int = 1, size: str = "512x512"):
    """
    Call the OpenAI Images API to generate images and return a list of image URLs.
    """
    # 1. Create client
    client = OpenAI(api_key=load_api_key())

    # 2. Send image generation request
    resp = client.images.generate(   # images.generate corresponds to /v1/images/generations
        prompt=prompt,
        n=n,
        size=size,
        response_format="url"        # can also be set to "b64_json"
    )

    # 3. Extract and return URLs
    urls = [item.url for item in resp.data]
    return urls

if __name__ == "__main__":

    prompt = "White-haired girl in a blue dress, standing under a cherry blossom tree, smiling and looking forward; background is a clear sky with falling cherry petals."
    urls = generate_image(prompt, n=2, size="1024x1024")
    print("Generated image URLs:")
    for idx, u in enumerate(urls, 1):
        print(f"{idx}. {u}")
    # Automatically open in the browser (optional)
        webbrowser.open(u)
