from dotenv import load_dotenv
import requests
import os

load_dotenv()  # Load environment variables from .env
API_KEY = os.getenv("HAMMING_API_KEY")

agents = {}

CALL_URL = "https://app.hamming.ai/api/rest/exercise/start-call"
AUDIO_URL = "https://app.hamming.ai/api/media/exercise?id={id}" 

def startCall(phone_number: str, prompt: str, webhook_url: str = None):
    """
    Start a new call with the AI agent
    """
    print(f"Making API call with phone: {phone_number}, prompt: {prompt}")
    print(f"Using webhook URL: {webhook_url}")
    
    # Updated prompt to instruct the model to act as a client
    updated_prompt = (
        f"You are a client calling {prompt}. Use the scenario provided to simulate a conversation. "
        f"Do not reveal that you are an AI. Use the context of {prompt} to guide the interaction."
    )
    
    payload = {
        "phone_number": phone_number,
        "prompt": updated_prompt,
        "webhook_url": webhook_url
    }
    
    try:
        response = requests.post(
            CALL_URL, 
            headers={"Authorization": f"Bearer {API_KEY}"}, 
            json=payload
        )
        print(f"API Response: {response.text}")  # Print full response
        
        if response.status_code != 200:
            print(f"Error: API returned status code {response.status_code}")
            return None
            
        response_data = response.json()
        print(f"Parsed response: {response_data}")
        return response_data
        
    except Exception as e:
        print(f"Error making API call: {str(e)}")
        return None

def getAudio(call_id: str):
    """
    Retrieve the audio recording for a specific call
    
    Args:
        call_id (str): The ID of the call to retrieve
    
    Returns:
        bytes: Audio data in WAV format
    """
    response = requests.get(
        AUDIO_URL.format(id=call_id), 
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    
    # Check if the response is audio data
    if response.headers.get('content-type') == 'audio/wav':
        return response.content
    return response.json()  # Fallback to JSON if not audio data
