# -*- coding: utf-8 -*-
import re, webbrowser
from typing import List, Dict, Any

from label import extract_tags, tags_to_prompt
from model_lab import generate_image as sd_generate
from image import generate_image as dalle_generate
from local_sd import generate_image as local_sd_generate


def chat_generate_prompt(user_input: str) -> Dict[str, Any]:
    """
    return {
        "tags": {...},
        "prompt": "Prompt"
    }
    """
    user_input = user_input.strip()
    if not user_input:
        raise ValueError("user_input cannot be empty")

    tags = extract_tags(user_input)
    prompt = tags_to_prompt(tags)

    return {"tags": tags, "prompt": prompt}



def generate_image_from_prompt(
    prompt: str,
    *,
    size: str = "1024x1024",
    model: str = "stable-diffusion",
    n: int = 1,
    negative_prompt: str = "bad quality",
    model_name: str | None = None,
) -> List[str]:
    
    if not re.match(r"^\d+x\d+$", size):
        raise ValueError('size: eg "1024x1024"')

    m = model.lower().strip()

    if m in ("stable-diffusion", "sd", "sdxl"):
        urls = sd_generate(
            prompt=prompt,
            n=n,
            size=size,
            negative_prompt=negative_prompt
        )
    elif m in ("dalle", "dall-e", "dalle3"):
        urls = dalle_generate(
            prompt=prompt,
            n=n,
            size=size
        )
    elif m in ("local_stable-diffusion", "local server", "local sd", "local", "local_sdxl"):
        urls = local_sd_generate(
            prompt=prompt,
            n=n,
            size=size,
            negative_prompt=negative_prompt,
            quality="balanced",
            model_name=model_name 
        )
    else:
        raise ValueError(f"unsupported model: {model}")

    return urls


if __name__ == "__main__":
    print("discribation:")
    user_text = input("> ").strip()
    data = chat_generate_prompt(user_text)
    print("\nPrompt :", data["prompt"])

    
    urls = generate_image_from_prompt(
        data["prompt"],
        size="768x768",
        model="local_stable-diffusion",
        model_name = None,
        n=1
    )
    print("URL   :", urls[0])
    webbrowser.open(urls[0])
