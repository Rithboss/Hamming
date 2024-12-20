import sys
print(sys.executable)
print(sys.path)
from flask_socketio import SocketIO, emit
from flask import Flask, render_template, jsonify, request, send_file
app = Flask(__name__)
socketio = SocketIO(app)
import llm

import networkx as nx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
from agents import TestAgent
import threading
import time
import requests
import json
from api_calls import startCall
import os
from transcribe import transcribe_audio_sync
import asyncio


previous_call_context = []

# Add this near the top of the file, after the imports
WEBHOOK_URL = " https://f4f4-96-78-229-125.ngrok-free.app/webhook"


class ConversationSimulator:
    def __init__(self, prompt, phone_number):
        self.agent = TestAgent(agent_name=prompt, socketio=socketio, phone_number=phone_number)
        self.phone_number = phone_number
        self.epoch = 0
        self.is_running = False
        self.thread = None
        self.pending_recordings = {}
        self.currentContext = ""
        self.currentGraph = {}
        

    def handle_webhook(self, data):
        """Handle webhook notifications from Hamming"""
        try:
            call_id = data.get('id')
            status = data.get('status')
            recording_available = data.get('recording_available', False)
            print(f"Handling webhook for call_id: {call_id}, status: {status}, recording: {recording_available}")
            
            if not call_id:
                print("No call_id in webhook data")
                return
            
            # Map Hamming status to user-friendly status
            status_mapping = {
                'event_phone_call_connected': 'Call connected...',
                'event_phone_call_ended': 'Call ended...',
                'event_recording': 'Recording in progress...',
                'downloading': 'Processing recording...',
                'analyzing': 'Analyzing conversation...',
                'completed': 'Completed'
            }
            
            display_status = status_mapping.get(status, status)
            
            if call_id not in self.pending_recordings:
                self.pending_recordings[call_id] = {
                    'status': display_status,
                    'phone_number': self.phone_number,
                    'start_time': time.strftime('%Y-%m-%dT%H:%M:%S.%f%z')
                }
            else:
                self.pending_recordings[call_id]['status'] = display_status
            
            # If recording is available, process it
            if recording_available:
                audio_url = f"https://app.hamming.ai/api/media/exercise?id={call_id}"
                self.process_recording(call_id, audio_url)
                
        except Exception as e:
            print(f"Error in handle_webhook: {str(e)}")
        
    def process_recording(self, call_id, audio_url):
        """Process a completed recording"""
        try:
            print(f"Processing recording for call_id: {call_id}")
            self.pending_recordings[call_id]['status'] = 'Downloading recording...'
            
            response = requests.get(
                audio_url,
                headers={"Authorization": f"Bearer {os.getenv('HAMMING_API_KEY')}"}
            )
            
            if response.status_code == 200:
                print(f"Successfully downloaded recording for {call_id}")
                self.pending_recordings[call_id]['status'] = 'Analyzing conversation...'
                
                # Use Deepgram to transcribe the audio
                transcript = asyncio.run(transcribe_audio_sync(response.content))
                print(f"Transcript for {call_id}: {transcript}")
                previous_call_context.append(transcript)   
            
                # Call digest_text with the transcript
                self.agent.digest_text(transcript)
                
                self.pending_recordings[call_id]['status'] = 'Completed'
                
            else:
                error_msg = f'Error downloading recording: {response.status_code}'
                print(error_msg)
                self.pending_recordings[call_id]['status'] = error_msg
                
        except Exception as e:
            error_msg = f"Error processing recording: {str(e)}"
            print(error_msg)
            self.pending_recordings[call_id]['status'] = error_msg

# Store active simulations
active_simulations = {}

@app.route('/')
def index():
    return render_template('index.html', simulations=active_simulations)

@app.route('/start_simulation', methods=['POST'])
def start_simulation():
    phone_number = request.form.get('phone_number')
    prompt = request.form.get('prompt')
    
    print("\n=== STARTING SIMULATION ===")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Phone: {phone_number}")
    print(f"Prompt: {prompt}")
    
    # Start the call with the webhook URL
    response = startCall(phone_number, prompt, webhook_url=WEBHOOK_URL, context= previous_call_context)
    
    if response and 'id' in response:
        if phone_number not in active_simulations:
            simulator = ConversationSimulator(prompt, phone_number)
            simulator.pending_recordings[response['id']] = {
                'status': 'Starting call...',
                'phone_number': phone_number,
                'start_time': time.strftime('%Y-%m-%dT%H:%M:%S.%f%z')
            }
            active_simulations[phone_number] = simulator
            return jsonify({'status': 'success'})
    
    return jsonify({'status': 'error', 'message': 'Failed to start simulation'})

@app.route('/stop_simulation/<phone_number>')
def stop_simulation(phone_number):
    if phone_number in active_simulations:
        active_simulations[phone_number].stop_simulation()
        del active_simulations[phone_number]
    return jsonify({'status': 'success'})



@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        print(f"Webhook received: {data}")
        call_id = data.get('id')
        status = data.get('status')
        
        for phone_number, simulator in active_simulations.items():
            if call_id in simulator.pending_recordings:
                print(f"Handling webhook for call_id: {call_id}, status: {status}")
                simulator.handle_webhook(data)
                return jsonify({'status': 'success'})
        
        print(f"No simulation found for call_id: {call_id}")
        return jsonify({'status': 'error', 'message': 'Simulation not found'}), 404
        
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@app.route('/discover_capabilities/<phone_number>', methods=['POST'])
def discover_capabilities(phone_number):
    if phone_number not in active_simulations:
        return jsonify({'status': 'error', 'message': 'Simulation not found'})
    print("hello")
    simulator = active_simulations[phone_number]
    current_graph = simulator.agent._dependency_graphs[simulator.agent.agent_name]
    print("Starting SImulation")
    # Create a new prompt for the next iteration
    iteration_prompt = (
        f"You are a customer calling about {simulator.agent.agent_name} services. "
        f"Based on the current conversation history and capabilities, "
        f"simulate a new scenario that explores different aspects of the service. "
        f"Try to uncover new paths and capabilities not yet seen in the graph. "
        f"Make sure the conversation is drastically different than the previous call and the context."
    )
   
    # Start a new call with the current graph context
    response = startCall(
        phone_number=phone_number,
        prompt= iteration_prompt,
        webhook_url=WEBHOOK_URL,
        context= previous_call_context,
    )
    
    if response and 'id' in response:
        simulator.pending_recordings[response['id']] = {
            'status': 'Starting new discovery call...',
            'phone_number': phone_number,
            'start_time': time.strftime('%Y-%m-%dT%H:%M:%S.%f%z')
        }
        simulator.epoch += 1  # Increment the epoch counter
        socketio.emit('update_epoch', {
            'phone_number': phone_number,
            'epoch': simulator.epoch
        })
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Failed to start discovery call'})

if __name__ == '__main__':
    socketio.run(app, debug=True, port=8000)