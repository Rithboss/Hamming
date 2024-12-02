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
    
    Args:
        phone_number (str): The phone number to call
        prompt (str): Instructions for the AI agent
        webhook_url (str, optional): URL to receive call status updates
    
    Returns:
        dict: Response containing call ID and status
    """
    payload = {
        "phone_number": phone_number,
        "prompt": prompt
    }
    
    if webhook_url:
        payload["webhook_url"] = webhook_url
        
    response = requests.post(
        CALL_URL, 
        headers={"Authorization": f"Bearer {API_KEY}"}, 
        json=payload
    )
    return response.json()

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
