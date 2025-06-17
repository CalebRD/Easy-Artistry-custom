# -----------------------------------------------------------------------------
# 文件名：classification.py（已迁移到 openai>=1.0.0）
# -----------------------------------------------------------------------------

from openai import OpenAI
import os
from dotenv import load_dotenv 
# -----------------------------------------------------------------------------


load_dotenv() # 加载 .env 文件中的环境变量

api_key = os.getenv("OPENAI_API_KEY", None)
if api_key is None:
    raise RuntimeError("无法获取 API Key，请先在 .env 文件中设置 OPENAI_API_KEY。")

client = OpenAI(api_key=api_key)

def classify_text(text: str) -> str:
    """
    调用 OpenAI API 对输入文本进行分类（例如提取图片生成关键词）。
    使用新版接口：client.completions.create(...)。
    """
    try:
        # 2. 原先的 openai.Completion.create(...) 改成 client.completions.create(...)
        response = client.completions.create(
            model="gpt-4.1",   # 用 model 替代 engine
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

        # 3. 新版返回结构依然使用 response.choices[0].text
        result = response.choices[0].text.strip()
        return result

    except Exception as e:
        # 4. 错误处理部分无需改动
        return f"调用 API 时出错: {e}"


if __name__ == "__main__":
    # 示例文本，可根据需要更换
    sample_text = "森林里一只熊在吃蜂蜜，背景是阳光透过树叶的景象，前景有飞舞的花瓣。"
    classification_result = classify_text(sample_text)
    print("文本分类结果:", classification_result)
