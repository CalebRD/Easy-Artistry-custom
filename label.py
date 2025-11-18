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
    调 GPT-4.1，返回：
    {
        "main_body": [...],
        "background": [...],
        "foreground": [...]
    }
    """
    client = OpenAI(api_key=_get_key())

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

    resp = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ],
        temperature=0.2,
        max_tokens=512
    )
    if not resp:
        raise Exception("No GPT-4.1 response")
        # print("ERROR: NO GPT-4.1 RESPONSE")
    # else:
        # print("GPT 4.1 Sucess")

    raw = resp.choices[0].message.content.strip()
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError("GPT-4 invalid JSON:\n" + raw)

    return json.loads(match.group())


def tags_to_prompt(tags: dict) -> str:
    parts = tags.get("main_body", []) + tags.get("background", []) + tags.get("foreground", [])
    return ", ".join([p.strip() for p in parts if p.strip()])
