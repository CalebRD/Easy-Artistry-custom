# -----------------------------------------------------------------------------
# Filename: classification.py (migrated to openai>=1.0.0)
# -----------------------------------------------------------------------------

from openai import OpenAI
import os
from dotenv import load_dotenv 
# -----------------------------------------------------------------------------


load_dotenv() # load environment variables from .env

api_key = os.getenv("OPENAI_API_KEY", None)
if api_key is None:
    raise RuntimeError("Cannot obtain API Key. Please set OPENAI_API_KEY in .env.")

client = OpenAI(api_key=api_key)

def classify_text(text: str) -> str:
    """
    Call the OpenAI API to classify input text (for example, extract image-generation keywords).
    Uses the new client.completions.create(...) interface.
    """
    try:
    # 2. The previous openai.Completion.create(...) is replaced by client.completions.create(...)
        response = client.completions.create(
            model="gpt-4.1",   # use 'model' instead of 'engine'
            prompt=(
                """**Role Description**  
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
                """
            ),
            max_tokens=256,
            temperature=0.0
        )

        # 3. The new response structure still uses response.choices[0].text
        result = response.choices[0].text.strip()
        return result

    except Exception as e:
        # 4. Error handling: return a readable message
        return f"Error calling API: {e}"


if __name__ == "__main__":
    # Example text (replace as needed)
    sample_text = "A bear eating honey in a forest, with sunlight filtering through the leaves in the background and petals floating in the foreground."
    classification_result = classify_text(sample_text)
    print("Classification result:", classification_result)
