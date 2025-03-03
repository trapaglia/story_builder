from flask import Flask, render_template, request, jsonify, Response
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from queue import Queue
from threading import Event
import time
from asgiref.sync import async_to_sync

from core import StoryOrchestrator

# Cargar variables de entorno
load_dotenv()

# Inicializar Flask y OpenAI
app = Flask(__name__)
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
orchestrator = StoryOrchestrator(client)

# Cola para mensajes del chat
chat_updates = Queue()
chat_event = Event()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat_updates')
def chat_updates_stream():
    def generate():
        while True:
            # Esperar hasta que haya nuevos mensajes o timeout después de 1 segundo
            if chat_event.wait(timeout=1.0):
                chat_event.clear()
                while not chat_updates.empty():
                    update = chat_updates.get()
                    yield f"data: {json.dumps(update)}\n\n"
            else:
                # Enviar un heartbeat para mantener la conexión viva
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
            time.sleep(0.1)  # Pequeña pausa para no sobrecargar el CPU
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/next_chapter', methods=['POST'])
def next_chapter():
    data = request.json
    feedback = data.get('feedback', '')
    
    if feedback:
        # Procesar el feedback a través de los agentes de manera síncrona
        feedback_analysis = async_to_sync(orchestrator.process_chapter_feedback)(feedback)
        
        # Notificar a los clientes sobre la actualización del chat
        chat_updates.put({"chat_history": feedback_analysis["chat_history"]})
        chat_event.set()
    
    # Obtener el siguiente capítulo
    next_chapter_data = orchestrator.get_next_chapter(feedback)
    return jsonify(next_chapter_data)

@app.route('/generate_story', methods=['POST'])
def generate_story():
    data = request.json
    initial_idea = data.get('initial_idea')
    character_count = data.get('character_count')
    narration_style = data.get('narration_style')
    character_names = data.get('character_names', [])
    
    # Limpiar el estado anterior
    orchestrator.reset_state()
    
    # Agregar agentes de personaje para cada nombre proporcionado
    for name in character_names:
        orchestrator.add_character_agent(name)
    
    try:
        # Configurar un callback para manejar las actualizaciones del chat en tiempo real
        def chat_update_callback(message):
            chat_updates.put({"chat_history": [message]})
            chat_event.set()
        
        # Asignar el callback al orquestador
        orchestrator.set_chat_callback(chat_update_callback)
        
        # Generar la historia de manera síncrona
        result = async_to_sync(orchestrator.generate_story)(
            initial_idea, character_count, narration_style, character_names
        )
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 