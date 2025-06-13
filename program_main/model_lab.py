# -----------------------------------------------
# model_lab.py  ——  统一格式 generate_image(prompt, n, size)
# -----------------------------------------------
import os, requests, json, re, webbrowser
from dotenv import load_dotenv

# ───────────────── API KEY ─────────────────────
def _get_key() -> str:
    load_dotenv()
    k = os.getenv("MODELSLAB_API_KEY")
    if not k:
        raise RuntimeError("请在 .env 中设置 MODELSLAB_API_KEY")
    return k


# ───────────────── 统一接口 ─────────────────────
def generate_image(
    prompt: str,
    n: int = 1,
    size: str = "1024x1024",
    *,
    negative_prompt: str = "bad quality",
    seed: int | None = None,
) -> list[str]:
    """
    与 image.py 同签名：
        prompt (str)       : 正向提示词
        n (int)            : 生成张数，对应 Modelslab 的 samples
        size (str)         : "宽x高"，例如 "768x1024"
    可选 keyword:
        negative_prompt (str) : 负面提示
        seed (int|None)       : 随机种子（None = 随机）
    返回：
        list[str] : 可直接访问的图片 URL 列表
    """
    # ---------- 解析 size ----------
    m = re.match(r"^\s*(\d+)[xX](\d+)\s*$", size)
    if not m:
        raise ValueError('size 应写成 "宽x高"，例如 "768x768"')
    width, height = m.groups()

    # ---------- 发送请求 ----------
    url = "https://modelslab.com/api/v6/realtime/text2img"
    payload = {
        "key": _get_key(),
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "width": width,
        "height": height,
        "samples": n,
        "seed": seed,
        "safety_checker": False,
        "base64": False,
        "webhook": None,
        "track_id": None,
    }
    data = requests.post(url, json=payload, timeout=120).json()

    # ---------- 结果处理 ----------
    if data.get("status") != "success":
        raise RuntimeError(f"Modelslab error: {json.dumps(data, ensure_ascii=False)}")

    raw_urls: list[str] = data.get("output", [])
    clean_urls = [u.replace("\\/", "/").replace("\\", "") for u in raw_urls]
    return clean_urls


# ───────────────── 自测 ────────────────────────
if __name__ == "__main__":
    demo_prompt = "(1girl:1.1), (solo), (masterpiece:1.2), (best quality:1.2), " \
                  "white hair, transparent vinyl jacket, crop top, denim shorts, " \
                  "cyberpunk city at night, neon signs, wet reflective street, " \
                  "dynamic pose, looking at viewer, cinematic rim-light, volumetric fog, " \
                  "illustration, anime style, extremely detailed, 8k, HDR"
    urls = generate_image(demo_prompt, n=1, size="512x512")
    if urls:
        print("Image URL:", urls[0])
        webbrowser.open(urls[0])
    else:
        print("No URL returned.")
