# -----------------------------------------------
# label.py   ——   GPT-4.1  + prompt 
# -----------------------------------------------
from openai import OpenAI
from dotenv import load_dotenv
import os, json, re


def _get_key():
    load_dotenv()
    k = os.getenv("OPENAI_API_KEY")
    if not k:
        raise RuntimeError("请在 .env 中设置 OPENAI_API_KEY")
    return k


def extract_tags(user_input: str) -> dict:
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
                Your task is to pull out image-generation keywords from the user’s input. 
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
    Your job is to convert the user’s natural-language description into an
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
    parts = tags.get("main_body", []) + tags.get("background", []) + tags.get("foreground", [])
    return ", ".join([p.strip() for p in parts if p.strip()])
