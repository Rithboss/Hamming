import openai
import os

# Load your API key
openai.api_key = os.getenv("OPENAI_API_KEY")  

def chat_with_gpt4(prompt, model="gpt-4"):
    """
    Function to send a prompt to GPT-4 and get a response.
    """
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error: {e}")
        return None