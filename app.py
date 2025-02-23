from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

# Inicializar Flask y OpenAI
app = Flask(__name__)
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_story', methods=['POST'])
def generate_story():
    data = request.json
    initial_idea = data.get('initial_idea')
    character_count = data.get('character_count')
    narration_style = data.get('narration_style')
    
    # Crear el prompt para OpenAI
    prompt = f"""Escribe una historia basada en la siguiente idea: {initial_idea}
    La historia debe tener aproximadamente {character_count} caracteres.
    Estilo de narración: {narration_style}
    Por favor, escribe una historia coherente y atractiva siguiendo estas pautas."""
    
    try:
        # Llamar a la API de OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un escritor creativo experto en crear historias cautivadoras. Narras de manera inmersiva y con un tono emocional."},
                {"role": "user", "content": prompt}
            ]
        )
        
        story = response.choices[0].message.content
        return jsonify({"story": story})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 