# -----------------------------------------------
# backend_main.py  ——  后端统一入口
# -----------------------------------------------
import re, webbrowser
from typing import List, Dict, Any

from label import extract_tags, tags_to_prompt
from model_lab import generate_image as sd_generate
from image import generate_image as dalle_generate


# ───────────────────────────────────────────────
# ① 聊天阶段：GPT 标签抽取 & Prompt 拼装
# ───────────────────────────────────────────────
def chat_generate_prompt(user_input: str) -> Dict[str, Any]:
    """
    前端第一次调用：用户输入需求 → 返回 {
        "tags": {...},
        "prompt": "最终拼装 Prompt"
    }
    """
    user_input = user_input.strip()
    if not user_input:
        raise ValueError("user_input 不能为空")

    tags = extract_tags(user_input)
    prompt = tags_to_prompt(tags)

    return {"tags": tags, "prompt": prompt}


# ───────────────────────────────────────────────
# ② 生成阶段：根据 prompt + 参数调用图像模型
# ───────────────────────────────────────────────
def generate_image_from_prompt(
    prompt: str,
    *,
    size: str = "1024x1024",
    model: str = "stable-diffusion",
    n: int = 1,
    negative_prompt: str = "bad quality",
) -> List[str]:
    """
    第二次调用（用户点击“生成”按钮）：
        prompt : chat_generate_prompt 返回的 prompt
        size   : "宽x高" 形式
        model  : "stable-diffusion" | "dalle"
        n      : 生成张数
    返回  : 图片 URL 列表
    """
    # —— 解析与校验 size —— 
    if not re.match(r"^\d+x\d+$", size):
        raise ValueError('size 必须形如 "1024x1024"')

    if model.lower() in ("stable-diffusion", "sd", "sdxl"):
        urls = sd_generate(
            prompt=prompt,
            n=n,
            size=size,
            negative_prompt=negative_prompt
        )
    elif model.lower() in ("dalle", "dall-e", "dalle3"):
        urls = dalle_generate(
            prompt=prompt,
            n=n,
            size=size
        )
    else:
        raise ValueError(f"不支持的模型标识: {model}")

    return urls


# ───────────────────────────────────────────────
# CLI 自测：python backend_main.py
# ───────────────────────────────────────────────
if __name__ == "__main__":
    print("输入一句场景描述：")
    user_text = input("> ").strip()
    data = chat_generate_prompt(user_text)
    print("\n📋 Prompt :", data["prompt"])

    # 预设生成 1 张 768×768 SD-XL 示例
    urls = generate_image_from_prompt(
        data["prompt"],
        size="768x768",
        model="stable-diffusion",
        n=1
    )
    print("🖼  URL   :", urls[0])
    webbrowser.open(urls[0])
