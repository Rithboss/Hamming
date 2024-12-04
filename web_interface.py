import llm
from flask import Flask, render_template, jsonify, request, send_file
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

app = Flask(__name__)

# Add this near the top of the file, after the imports
WEBHOOK_URL = "https://43d3-96-78-229-125.ngrok-free.app/webhook"


class ConversationSimulator:
    def __init__(self, prompt, phone_number):
        self.agent = TestAgent(prompt)
        self.phone_number = phone_number
        self.epoch = 0
        self.is_running = False
        self.thread = None
        self.pending_recordings = {}
        self.graph_needs_update = False

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
                
                # Call digest_text with the transcript
                self.agent.digest_text(transcript)
                
                self.pending_recordings[call_id]['status'] = 'Completed'
                self.graph_needs_update = True
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
    response = startCall(phone_number, prompt, webhook_url=WEBHOOK_URL)
    
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

@app.route('/get_graph/<phone_number>')
def get_graph(phone_number):
    if phone_number not in active_simulations:
        return jsonify({'status': 'error', 'message': 'Simulation not found'})
    
    simulator = active_simulations[phone_number]
    graph_data = TestAgent._dependency_graphs[simulator.agent.agent_name]
    
    # Convert the graph to a visualization
    plt.figure(figsize=(12, 8))
    G = nx.DiGraph()
    
    def add_nodes(graph, parent=None):
        for question, responses in graph.items():
            if isinstance(responses, dict):
                G.add_node(question, type='question')
                if parent:
                    G.add_edge(parent, question)
                for response, next_level in responses.items():
                    response_node = f"{question}_{response}"
                    G.add_node(response_node, type='response')
                    G.add_edge(question, response_node)
                    add_nodes(next_level, response_node)

    add_nodes(graph_data.get('conversation_paths', {}))
    
    # Generate the plot
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True, node_color='lightblue', 
            node_size=2000, font_size=8, font_weight='bold')
    
    # Convert plot to base64 string
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    graph_url = base64.b64encode(img.getvalue()).decode()
    plt.close()
    
    return jsonify({
        'status': 'success',
        'graph': graph_url,
        'epoch': simulator.epoch
    })

@app.route('/status/<phone_number>')
def status(phone_number):
    if phone_number not in active_simulations:
        return jsonify({'status': 'error', 'message': 'Simulation not found'}), 404
        
    simulator = active_simulations[phone_number]
    latest_status = None
    latest_time = None
    
    for call_id, status_data in simulator.pending_recordings.items():
        if status_data['phone_number'] == phone_number:
            if not latest_time or status_data.get('start_time', '') > latest_time:
                latest_status = status_data['status']
                latest_time = status_data.get('start_time')
    
    # Include graph_needs_update in status response
    return jsonify({
        'status': 'success',
        'message': latest_status or 'No status available',
        'graph_needs_update': simulator.graph_needs_update
    })

@app.route('/graph/<phone_number>')
def graph(phone_number):
    if phone_number not in active_simulations:
        return jsonify({'status': 'error', 'message': 'Simulation not found'}), 404
        
    simulator = active_simulations[phone_number]
    if not simulator.agent:
        return jsonify({'status': 'error', 'message': 'No agent found'}), 404
        
    # Use a sample graph for testing
    if phone_number == "+14153580761":
        graph_data = {
            'nodes': ['A', 'B', 'C'],
            'edges': [('A', 'B'), ('B', 'C')]
        }
    else:
        # Create a new directed graph
        G = nx.DiGraph()
        dep_graph = simulator.agent._dependency_graphs[simulator.agent.agent_name]
        
        def add_nodes_edges(graph, parent=None):
            for q in graph:
                G.add_node(q)
                if parent:
                    G.add_edge(parent, q)
                for r in graph[q]:
                    G.add_node(r)
                    G.add_edge(q, r)
                    add_nodes_edges(graph[q][r], r)
        
        add_nodes_edges(dep_graph)
        
        graph_data = {
            'nodes': list(G.nodes()),
            'edges': list(G.edges())
        }
    
    return jsonify({
        'status': 'success',
        'graph': graph_data
    })

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
                if status == 'event_recording' and data.get('recording_available'):
                    simulator.graph_needs_update = True
                    print(f"Graph needs update set to True for phone number: {phone_number}")
                return jsonify({'status': 'success'})
        
        print(f"No simulation found for call_id: {call_id}")
        return jsonify({'status': 'error', 'message': 'Simulation not found'}), 404
        
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/graph_status/<phone_number>')
def graph_status(phone_number):
    if phone_number not in active_simulations:
        return jsonify({'status': 'error', 'message': 'Simulation not found'}), 404
        
    simulator = active_simulations[phone_number]
    needs_update = simulator.graph_needs_update
    simulator.graph_needs_update = False  # Reset flag after checking
    print(f"Graph status for phone number {phone_number}: needs_update = {needs_update}")
    return jsonify({
        'status': 'success',
        'needs_update': needs_update
    })

if __name__ == '__main__':
    app.run(debug=True, port=8000) 