from openai import OpenAI
from dotenv import load_dotenv
import os

def init_openai():
    # Specifically load setup.env instead of .env
    load_dotenv('setup.env')
    api_key = os.getenv('OPENAI_API_KEY')
    
    # Detailed debug prints
    print("\nDEBUG INFO:")
    print(f"1. API Key found: {'Yes' if api_key else 'No'}")
    print(f"2. API Key length: {len(api_key) if api_key else 'N/A'}")
    print(f"3. API Key prefix: {api_key[:20]}... (truncated)")
    print(f"4. Working directory: {os.getcwd()}")
    print(f"5. setup.env file exists: {os.path.exists('setup.env')}")
    
    client = OpenAI(api_key=api_key)
    
    # Test connection
    try:
        test_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5
        )
        print("6. API Connection test: Success")
    except Exception as e:
        print(f"6. API Connection test: Failed - {str(e)}")
    
    return client

client = init_openai()

def chat_with_gpt4(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error in chat_with_gpt4: {e}")
        return "none"