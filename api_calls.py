from dotenv import load_dotenv
import requests
import os
import json

load_dotenv()  # Load environment variables from .env
API_KEY = os.getenv("HAMMING_API_KEY")

agents = {}

CALL_URL = "https://app.hamming.ai/api/rest/exercise/start-call"
AUDIO_URL = "https://app.hamming.ai/api/media/exercise?id={id}" 

def startCall(phone_number: str, prompt: str, webhook_url: str = None, context: [] = None, graph=None):
    """
    Start a new call with the AI agent
    
    Args:
        phone_number: The phone number to call
        prompt: The business/agent name
        webhook_url: URL for webhook notifications
        context: Additional context for the conversation
        graph: Current conversation graph structure
        previous_call_context: Previous call context
    """
    print(f"Making API call with phone: {phone_number}, prompt: {prompt}")  
    print(f"Using webhook URL: {webhook_url}")
    
    # Format the graph structure for the prompt
    graph_context = ""
    if graph:
        graph_context = "\nPrevious conversation paths:\n" + json.dumps(graph, indent=2)
    
    # Convert context list to string if it exists
    context_str = "\n".join(context) if context else "Standard customer service call"
    
    # Updated prompt to instruct the model to act as a client
    updated_prompt = (
        f"You are a client calling {prompt}. Simulate a realistic customer conversation "
        f"based on the following guidelines:\n\n"
        f"1. Act as a genuine customer with a specific need or issue\n"
        f"2. Stay in character throughout the conversation\n"
        f"3. Use natural, conversational language\n"
        f"4. If previous conversation paths exist, try to explore new scenarios\n"
        f"5. Respond to questions naturally and provide relevant information\n\n"
        f"Business Context: {prompt}\n"
        f"Additional Context: {context_str}"
        f"{graph_context}"
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
            json=payload,
            timeout=30  # Add timeout to prevent hanging
        )
        print(f"API Response: {response.text}")
        
        if response.status_code != 200:
            print(f"Error: API returned status code {response.status_code}")
            return None
            
        response_data = response.json()
        print(f"Parsed response: {response_data}")
        return response_data
        
    except requests.exceptions.Timeout:
        print("Request timed out")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error making API call: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
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
