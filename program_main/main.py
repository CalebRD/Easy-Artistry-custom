# -----------------------------------------------
# main.py
# -----------------------------------------------
import webbrowser
from label import extract_tags, tags_to_prompt
from image import generate_image

def run_once():
    print("=== Enter a scene description (in Chinese or English) ===")
    user_text = input("> ").strip()
    if not user_text:
        print("⚠️  Input is empty, exiting.")
        return

    # ① Tag extraction
    tags = extract_tags(user_text)
    print("📝 GPT-4 Tags:", tags)

    # ② Prompt assembly
    prompt = tags_to_prompt(tags)
    print("🎨 Prompt for generation:", prompt)

    # ③ Generate image
    urls = generate_image(prompt, n=1, size="1024x1024")
    print("✅ Image URL:", urls[0])

    # ④ Open browser
    webbrowser.open(urls[0])
    # -----------------------------------------------

def back_end_main(user_input: str):
    print("=== Enter a scene description (in Chinese or English) ===")

    if not user_input:
        print("⚠️  Input is empty, exiting.")
        return

    # ① Tag extraction
    tags = extract_tags(user_input)
    print("📝 GPT-4 Tags:", tags)

    # ② Prompt assembly
    prompt = tags_to_prompt(tags)
    print("🎨 Prompt for generation:", prompt)

    # ③ Generate image
    urls = generate_image(prompt, n=1, size="1024x1024")
    print("✅ Image URL:", urls[0])

    return urls[0]  # return the picture URL

if __name__ == "__main__":
    run_once()
