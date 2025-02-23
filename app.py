from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv
import os
from agents import StoryOrchestrator
import asyncio

# Cargar variables de entorno
load_dotenv()

# Inicializar Flask y OpenAI
app = Flask(__name__)
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
orchestrator = StoryOrchestrator(client)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_story', methods=['POST'])
def generate_story():
    data = request.json
    initial_idea = data.get('initial_idea')
    character_count = data.get('character_count')
    narration_style = data.get('narration_style')
    character_names = data.get('character_names', [])  # Lista de nombres de personajes
    
    # Agregar agentes de personaje para cada nombre proporcionado
    for name in character_names:
        orchestrator.add_character_agent(name)
    
    try:
        # Crear un nuevo evento loop para manejar la generación asíncrona
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Generar la historia y obtener el chat
        result = loop.run_until_complete(
            orchestrator.generate_story(initial_idea, character_count, narration_style)
        )
        
        loop.close()
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 