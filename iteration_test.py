from pathlib import Path
from google import genai
from google.genai import types
import os, sys
from dotenv import load_dotenv

#get key
load_dotenv()
apiKey = os.getenv("GOOGLE_API_KEY")
if not apiKey:
    raise RuntimeError("Please set GOOGLE_API_KEY in .env") 

if len(sys.argv) > 2:
    imagePath = sys.argv[1]
    iterationPrompt = sys.argv[2]
else:
    KeyError(f"Missing Arguments")

#get image
image_path = Path(__file__).parent / imagePath
if not image_path.exists():
    raise FileNotFoundError(f"Image not found: {image_path.resolve()}")

with image_path.open('rb') as f:
    image_bytes = f.read()

client = genai.Client(api_key=apiKey)
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=[
        types.Part.from_bytes(
            data=image_bytes,
            mime_type='image/jpeg',
        ),
        'Edit this image.'
    ]
)

print(response)