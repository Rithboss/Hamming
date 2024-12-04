from deepgram import (
    DeepgramClient,
    PrerecordedOptions,
)
import os
import asyncio
from typing import Union

# Initialize client directly with API key
DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')
if not DEEPGRAM_API_KEY:
    raise ValueError("DEEPGRAM_API_KEY not found in environment variables")

deepgram = DeepgramClient(DEEPGRAM_API_KEY)

async def transcribe_audio(audio_data: Union[bytes, bytearray]):
    try:
        if not isinstance(audio_data, (bytes, bytearray)):
            raise ValueError(f"Expected bytes or bytearray, got {type(audio_data)}")

        # Create source object
        source = {
            "buffer": audio_data,
            "mimetype": "audio/wav"
        }
        
        # Configure transcription options
        options = PrerecordedOptions(
            smart_format=True,
            model="general",
            language="en-US",
            punctuate=True,
            utterances=True
        )
        
        # Get the transcript using the correct v3 method
        # The transcribe_file method returns a PrerecordedResponse directly, no need to await
        response = deepgram.listen.prerecorded.v("1").transcribe_file(source, options)
        
        # Extract transcript from response
        if not response or not hasattr(response, 'results'):
            raise ValueError("Invalid response format from Deepgram")
            
        if not response.results.channels:
            raise ValueError("No channels found in transcription results")
            
        if not response.results.channels[0].alternatives:
            raise ValueError("No alternatives found in transcription results")
            
        transcript = response.results.channels[0].alternatives[0].transcript
        
        if not transcript:
            raise ValueError("Empty transcript received")
            
        return transcript

    except Exception as e:
        print(f"Error in transcription: {str(e)}")
        print(f"Error type: {type(e)}")
        if hasattr(e, '__traceback__'):
            import traceback
            print(f"Traceback: {traceback.format_tb(e.__traceback__)}")
        raise

def transcribe_audio_sync(audio_data: Union[bytes, bytearray]) -> str:
    """Synchronous wrapper for async transcription"""
    try:
        # Since the v3 API doesn't require awaiting, we can call it directly
        return transcribe_audio(audio_data)
    except Exception as e:
        print(f"Error in synchronous transcription: {str(e)}")
        raise

def validate_audio_data(audio_data: Union[bytes, bytearray]) -> bool:
    """Validate audio data before processing"""
    if not audio_data:
        return False
    if not isinstance(audio_data, (bytes, bytearray)):
        return False
    if len(audio_data) < 100:  # Arbitrary minimum size for valid audio
        return False
    return True