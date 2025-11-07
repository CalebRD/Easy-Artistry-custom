# -----------------------------------------------
# image.py   ——   Calling DALL·E to generate images
# -----------------------------------------------
from openai import OpenAI
from dotenv import load_dotenv
import os, webbrowser

def _get_key():
    load_dotenv()
    k = os.getenv("OPENAI_API_KEY")
    if not k:
        raise RuntimeError("Please set the OPENAI_API_KEY environment variable.")
    return k

def generate_image(prompt: str, n: int = 1, size: str = "1024x1024") -> list[str]:
    """
    Generate images using OpenAI's DALL·E model.    
    """
    client = OpenAI(api_key=_get_key())
    resp = client.images.generate(
        prompt=prompt,
        n=n,
        size=size,
        response_format="url"
    )
    return [item.url for item in resp.data]

# Self-test
if __name__ == "__main__":
    prompt="A lone chrome cyber-samurai kneeling on an ancient moss-covered stone bridge that arches over a crystal clear stream, in a mist-filled cherry-blossom forest at dawn, golden volumetric light shafts filtering through the trees, swirling pink petals and gentle bioluminescent fireflies, ultra-realistic cinematic 8K, octane render"
    urls = generate_image(prompt,size="1024x1024") 
    print(urls[0])
    webbrowser.open(urls[0])
