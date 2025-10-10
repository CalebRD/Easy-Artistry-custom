# -----------------------------------------------
# label.py   ——   GPT-4.1  + prompt 
# -----------------------------------------------
from openai import OpenAI 
import requests
from dotenv import load_dotenv
import os, json, re


def _get_key():
    load_dotenv()
    k = os.getenv("OPENAI_API_KEY")
    if not k:
           raise RuntimeError("Please set OPENAI_API_KEY in .env")
    return k

def _get_cloudflare_config():
    load_dotenv()
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    api_token = os.getenv("CLOUDFLARE_API_TOKEN")
    if not account_id or not api_token:
           raise RuntimeError("Please set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN in .env")
    return account_id, api_token

def extract_tags_cloudflare(user_input: str) -> dict:
    """
    returns a dictionary with keys "main_body", "background", and "foreground"
    """
    account_id, api_token = _get_cloudflare_config()
    
    system_prompt = (
    """**Role Description**
    You are a professional prompt-engineering assistant for *Stable Diffusion*.
    Your job is to convert the user's natural-language description into an
    authoritative Stable-Diffusion prompt that follows best community practices
    (keywords, style modifiers, weighting syntax, etc.).

    ---

    ### Step-by-Step Workflow

    1. **Input Check**
    - If the user is describing an image (scene, character, object, etc.),
        proceed to the next steps.
    - Otherwise, output `null`.

    2. **Main Subject Analysis**
    - Decide whether the subject is a *person*, *creature*, or *object*.
    - Extract subject attributes (hair color, clothing, material, pose…).

    3. **Background Analysis**
    - Determine the environment (forest, city skyline, spaceship interior…).
    - Note time-of-day, lighting mood, weather, atmosphere.

    4. **Foreground / Effects Analysis**
    - Capture effects in front of or around the subject
        (rain streaks, glowing particles, magic glyphs…).

    5. **Style & Quality Modifiers**
    - Add common SD quality tags: `(masterpiece:1.3)`, `(best quality:1.2)`.
    - Choose one coherent art style (e.g. *anime illustration*, *cinematic photo*,
        *digital oil painting*); avoid mixing conflicting styles.

    6. **Prompt Assembly**
    - Concatenate elements in this order **[quality] + [subject] + [details] +
        [background] + [effects] + [style]**.
    - Separate phrases with commas; put *key* phrases in parentheses to boost
        weight; keep the whole line under 300 characters when possible.

    ---

    ### Output Format (strictly enforced)

    ```json
    {
    "sd_prompt": "Stable-Diffusion ready prompt, comma-separated, with weighting tags",
    "keywords": {
        "main_body": ["keyword1", "keyword2"],
        "background": ["keywordA", "keywordB"],
        "foreground": ["keywordX", "keywordY"]
    }
    }
    ```

    Notes
    Focus solely on building a single, coherent Stable-Diffusion prompt.
    Do NOT include LoRA syntax, negative prompt, or camera settings unless explicitly provided.
    For any unrelated user query, reply with null.
    """)
    
    api_base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/"
    headers = {"Authorization": f"Bearer {api_token}"}
    
    inputs = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]
    
    def run(model, inputs):
        input_data = { "messages": inputs }
        response = requests.post(f"{api_base_url}{model}", headers=headers, json=input_data)
        return response.json()
    
    try:
        output = run("@cf/meta/llama-3-8b-instruct", inputs)
        if "result" in output and "response" in output["result"]:
            raw = output["result"]["response"].strip()
            
            match = re.search(r"\{.*\}", raw, re.S)
            if not match:
                raise ValueError("Cloudflare invalid JSON:\n" + raw)
                
            return json.loads(match.group())
        else:
              raise RuntimeError(f"Cloudflare response format error: {output}")
            
    except requests.exceptions.RequestException as e:
           raise RuntimeError(f"Cloudflare API request failed: {e}")
    except KeyError as e:
           raise RuntimeError(f"Cloudflare response parsing failed: {e}")
    except Exception as e:
           raise RuntimeError(f"Cloudflare processing failed: {e}")



def extract_tags_openai(user_input: str) -> dict:
    """
    returns a dictionary with keys "main_body", "background", and "foreground",
    {
        "main_body": [...],
        "background": [...],
        "foreground": [...]
    }
    """
    client = OpenAI(api_key=_get_key())
    '''
    system_prompt = ("""**Role Description**  
                You are a professional keyword-extraction specialist. 
                Your task is to pull out image-generation keywords from the user's input. 
                The output **must** follow the JSON schema exactly.

                ---

                ### Step-by-Step Workflow

                1. **Input Check**  
                - If the user is describing an image, proceed to the next steps.  
                - Otherwise, output `null`.

                2. **Main Subject Analysis**  
                - Identify whether the subject is a *person* or an *object*.  
                - Extract subject details (e.g., hair color, facial features, material, etc.).  
                - List all subject attributes.

                3. **Background Analysis**  
                - Examine the background setting (e.g., meadow, forest, city skyline).  
                - List every background element.

                4. **Foreground Analysis**  
                - Examine foreground effects (e.g., flames, lightning, particles).  
                - List every foreground element.

                5. **Output**  
                - Collate all extracted keywords.  
                - Return them in the required JSON format.

                ---

                ### Output Format (strictly enforced)

                ```json
                {
                  "main_body": ["subject element 1", "subject element 2"],
                  "background": ["background element 1", "background element 2"],
                  "foreground": ["foreground element 1", "foreground element 2"]
                }
                ```

                ### Notes
                1. Focus solely on the classification task above.
                2. For any unrelated user query, output null.
                """)
    '''
    system_prompt = (
    """**Role Description**
    You are a professional prompt-engineering assistant for *Stable Diffusion*.
    Your job is to convert the user's natural-language description into an
    authoritative Stable-Diffusion prompt that follows best community practices
    (keywords, style modifiers, weighting syntax, etc.).

    ---

    ### Step-by-Step Workflow

    1. **Input Check**
    - If the user is describing an image (scene, character, object, etc.),
        proceed to the next steps.
    - Otherwise, output `null`.

    2. **Main Subject Analysis**
    - Decide whether the subject is a *person*, *creature*, or *object*.
    - Extract subject attributes (hair color, clothing, material, pose…).

    3. **Background Analysis**
    - Determine the environment (forest, city skyline, spaceship interior…).
    - Note time-of-day, lighting mood, weather, atmosphere.

    4. **Foreground / Effects Analysis**
    - Capture effects in front of or around the subject
        (rain streaks, glowing particles, magic glyphs…).

    5. **Style & Quality Modifiers**
    - Add common SD quality tags: `(masterpiece:1.3)`, `(best quality:1.2)`.
    - Choose one coherent art style (e.g. *anime illustration*, *cinematic photo*,
        *digital oil painting*); avoid mixing conflicting styles.
    - Pick a suitable sampler tag if mentioned (e.g. *artstation*, *8k*).

    6. **Prompt Assembly**
    - Concatenate elements in this order **[quality] + [subject] + [details] +
        [background] + [effects] + [style]**.
    - Separate phrases with commas; put *key* phrases in parentheses to boost
        weight; keep the whole line under 300 characters when possible.

    ---

    ### Output Format (strictly enforced)

    ```json
    {
    "sd_prompt": "Stable-Diffusion ready prompt, comma-separated, with weighting tags",
    "keywords": {
        "main_body": ["keyword1", "keyword2"],
        "background": ["keywordA", "keywordB"],
        "foreground": ["keywordX", "keywordY"]
    }
    }
    sd_prompt is what the front-end will send directly to the txt2img API.
    keywords is optional diagnostic data; if you need only the prompt, you can
    ignore this field.

    Notes
    Focus solely on building a single, coherent Stable-Diffusion prompt.

    Do NOT include LoRA syntax, negative prompt, or camera settings unless
    explicitly provided by the user.

    For any unrelated user query, reply with null.
    """)
    
    resp = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ],
        temperature=0.2,
        max_tokens=512
    )

    raw = resp.choices[0].message.content.strip()
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError("GPT-4 invalid JSON:\n" + raw)

    return json.loads(match.group())


def tags_to_prompt(tags: dict) -> str:
    """
    Merge Stable Diffusion style prompt.
    
    Expected input format:
    {
      "sd_prompt": "(masterpiece:1.3), (best quality:1.2), Hitori Gotoh from Bocchi the Rock, playing piano, wearing white sailor uniform, on stage, (bright smile), background of red curtain, anime illustration",
      "keywords": {
        "main_body": ["Hitori Gotoh", "playing piano", "white sailor uniform", "bright smile"],
        "background": ["stage", "red curtain"],
        "foreground": []
      }
    }
    
    Output: combined SD-style prompt string.
    """
    # Original sd_prompt (may include weights and modifiers)
    sd_prompt = tags.get("sd_prompt", "").strip()

    # Parts from keywords
    keywords = []
    for key in ["main_body", "background", "foreground"]:
        keywords.extend(tags.get("keywords", {}).get(key, []))

    # Clean whitespace and deduplicate while preserving order
    keywords_cleaned = []
    seen = set()
    for kw in keywords:
        kw_stripped = kw.strip()
        if kw_stripped and kw_stripped not in seen:
            keywords_cleaned.append(kw_stripped)
            seen.add(kw_stripped)

    # Merge: keep sd_prompt first, then append keywords (avoid duplicates)
    if sd_prompt:
        prompt_parts = [sd_prompt] + keywords_cleaned
    else:
        prompt_parts = keywords_cleaned

    return ", ".join(prompt_parts)

def extract_tags(user_input: str, provider: str = "cloudflare") -> dict:
    """
    Unified Interface
    
    Args:
        user_input: description
        provider: "openai" or "cloudflare"
    
    Returns:
        dict with sd_prompt and keywords
    """
    if provider.lower() == "openai":
        return extract_tags_openai(user_input)
    elif provider.lower() == "cloudflare":
        return extract_tags_cloudflare(user_input)
    else:
        raise ValueError(f"Unsupported provider: {provider}, please select 'openai' or 'cloudflare'")


if __name__ == "__main__":
    print("Please enter a description of the image (or type exit to quit):")
    while True:
        text = input("> ").strip()
        if text.lower() in ("exit", "quit"):
            break
        try:
            data = extract_tags(text, provider="cloudflare")
            if not data:
                print("Input not recognized as an image description, please try again.\n")
                continue
            print("\nExtracted keywords:")
            print(json.dumps(data, ensure_ascii=False, indent=2))
            prompt = tags_to_prompt(data)
            print("\nGenerated Prompt:")
            print(prompt)
            print("\n---\nPlease enter a description of the image (or type exit to quit):")
        except Exception as e:
            print("Error:", e)
            print("\n---\nPlease enter a description of the image (or type exit to quit):")

