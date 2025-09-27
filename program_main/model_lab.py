# -----------------------------------------------
# model_lab.py  ——  Unified format generate_image(prompt, n, size)
# -----------------------------------------------
import os, requests, json, re, webbrowser
from dotenv import load_dotenv

# ───────────────── API KEY ─────────────────────
def _get_key() -> str:
    load_dotenv()
    k = os.getenv("MODELSLAB_API_KEY")
    if not k:
        raise RuntimeError("Please set MODELSLAB_API_KEY in .env")  
    return k
    
def generate_image(
    prompt: str,
    n: int = 1,
    size: str = "1024x1024",
    *,
    negative_prompt: str = "bad quality",
    seed: int | None = None,
) -> list[str]:
    """
        Same signature as image.py:
        prompt (str)       : Positive prompt
        n (int)            : Number of images to generate, corresponds to Modelslab's samples
        size (str)         : "widthxheight", e.g., "768x1024"
        Optional keyword:
            negative_prompt (str) : Negative prompt
            seed (int|None)       : Random seed (None = random)
        Returns:
            list[str] : List of image URLs that can be directly accessed
    """
    # ----------  size ----------
    m = re.match(r"^\s*(\d+)[xX](\d+)\s*$", size) # Matches "widthxheight" format
    if not m:
        raise ValueError('size should be written as "widthxheight", e.g., "768x768"')
    width, height = m.groups()

    # ---------- request ----------
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

    # ---------- result ----------
    if data.get("status") != "success":
        raise RuntimeError(f"Modelslab error: {json.dumps(data, ensure_ascii=False)}")

    raw_urls: list[str] = data.get("output", [])
    clean_urls = [u.replace("\\/", "/").replace("\\", "") for u in raw_urls]
    return clean_urls



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