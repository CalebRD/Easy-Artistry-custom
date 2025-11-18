# -----------------------------------------------------------------------------
# Filename: chat_gpt4.py
# Function: Single-turn conversational call to GPT-4.1 model and print the model's reply
# -----------------------------------------------------------------------------

from openai import OpenAI
from dotenv import load_dotenv
import os

def load_api_key_from_env():
    """
    1. Load the .env file in the project root directory and inject the environment variables into os.environ.
    2. Read OPENAI_API_KEY, if empty, raise an error to remind the user to check .env.
    """
    # Find the .env file in the execution directory and load all key=value into os.environ
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY", None)
    if api_key is None:
        raise RuntimeError("Unable to get API Key. Please set OPENAI_API_KEY in the .env file first.")
    return api_key

def chat_once_with_gpt4(user_input: str) -> str:
    """
    For the given user_input, this function only sends one request to GPT-4.1,
    does not retain any conversation history, and returns the reply string (plain text).

    Args:
        user_input (str): The content (text) the user wants the model to answer in this round

    Returns:
        str: The model's reply content (text)
    """
    # 1. Read OPENAI_API_KEY from .env
    api_key = load_api_key_from_env()
    
    # 2. Create OpenAI client and explicitly pass the api_key to it
    client = OpenAI(api_key=api_key)
    prompt ="""**Role Description**  
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
    # 3. Make a single-turn conversation call: model="gpt-4.1", only pass in this user's message, do not retain history
    #    Note: The messages list below contains only two items—system (optional) and user.
    #    If you don't need the system description, you can just pass user. Here is an example with a system role.
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {
                "role": "system",
                "content": prompt
            },
            {
                "role": "user",
                "content": user_input
            }
        ],
        # The following parameters can be adjusted as needed
        max_tokens=1024,       # Maximum number of tokens for this answer, depending on question complexity
        temperature=0.3,       # Sampling temperature: 0.0 means most "conservative"/deterministic output, 1.0 is more "random"
        top_p=1.0,             # nucleus sampling parameter
        frequency_penalty=0.0, # Frequency penalty: >0 will make the model reduce repetition; 0 means no penalty
        presence_penalty=0.0   # Topic penalty: >0 will encourage the model to introduce new topics; 0 means no penalty
        
    )
    
    # 4. Extract the model's reply from the response
    # For chat completion, GPT-4 series puts the returned text in choices[0].message.content
    result_text = response.choices[0].message.content.strip()
    return result_text

if __name__ == "__main__":
    # Example of interactive or batch call
    print("=== Single-turn conversation example using GPT-4.1 ===")
    user_question = input("user input:")  
    
    # 5. Call chat_once_with_gpt4 once and print the model's reply
    reply = chat_once_with_gpt4(user_question)
    print("\nGPT-4.1 reply:\n" + reply)