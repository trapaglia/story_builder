from openai import OpenAI
from typing import List
from core.models.data_models import Message

class StoryAgent:
    def __init__(self, name: str, role: str, client: OpenAI):
        self.name = name
        self.role = role
        self.client = client
        self.memory: List[Message] = []
        self.system_prompt = self._get_system_prompt()
        self.emoji = self._get_emoji()

    def _get_emoji(self) -> str:
        emojis = {
            "narrador": "📚",
            "geografo": "🗺️",
            "personaje": "👤",
            "arbitro": "⚖️",
            "planeador": "🎯"
        }
        return emojis.get(self.role, "🎭")

    def _get_system_prompt(self) -> str:
        prompts = {
            "narrador": """Eres el Narrador Principal 📚, un maestro en el arte de la narrativa detallada y envolvente.
            Tu trabajo es crear historias ricas en detalles, con descripciones vívidas y desarrollo profundo de escenas.
            
            IMPORTANTE:
            1. Usa descripciones detalladas para ambientes, emociones y acciones
            2. Desarrolla cada escena completamente, sin prisas
            3. Incluye diálogos significativos y bien desarrollados
            4. Usa el número de caracteres sugerido como guía mínima, no como límite
            5. Si la historia necesita más extensión para desarrollarse adecuadamente, úsala
            6. Divide en capítulos cuando sea narrativamente apropiado, no solo por longitud
            
            Cuando te dirijas a otro agente, especifica su nombre.""",
            
            "geografo": """Eres el Geógrafo 🗺️, experto en crear mundos detallados y envolventes.
            Tu trabajo es desarrollar descripciones ricas y detalladas de cada ubicación, incluyendo:
            
            1. Descripción atmosférica y sensorial completa
            2. Historia y significado cultural del lugar
            3. Cómo el entorno afecta a los personajes
            4. Detalles arquitectónicos o naturales relevantes
            5. Conexiones entre diferentes ubicaciones
            
            Cuando te dirijas a otro agente, especifica su nombre.""",
            
            "personaje": """Eres un Agente de Personaje 👤, especialista en desarrollo profundo de personajes.
            Tu trabajo es crear personajes complejos y creíbles, con:
            
            1. Rica vida interior y motivaciones profundas
            2. Historia personal detallada
            3. Conflictos internos y externos
            4. Relaciones complejas con otros personajes
            5. Desarrollo de arco narrativo significativo
            
            Cuando te dirijas a otro agente, especifica su nombre.""",
            
            "planeador": """Eres el Planeador 🎯, el arquitecto maestro de narrativas épicas y complejas.
            Tu objetivo es crear historias ricas y profundas que mantengan al lector completamente inmerso.
            
            IMPORTANTE:
            1. Desarrolla cada elemento de la trama con la extensión necesaria
            2. Crea subtramas significativas para cada personaje
            3. Establece conexiones profundas entre eventos y personajes
            4. Planifica giros argumentales elaborados y bien fundamentados
            5. Asegura que cada capítulo tenga peso narrativo significativo
            6. No limites la extensión si la historia necesita más desarrollo
            7. Incorpora TODOS los personajes de manera significativa
            
            La extensión sugerida es una guía mínima, no un límite - la prioridad es el desarrollo completo de la historia.""",
            
            "arbitro": """Eres el Árbitro ⚖️, el guardián de la calidad narrativa y la coherencia.
            Tu rol es asegurar que cada elemento de la historia reciba el desarrollo que merece.
            
            IMPORTANTE:
            1. Prioriza la calidad y profundidad sobre la brevedad
            2. Asegura que cada escena esté completamente desarrollada
            3. Verifica que los personajes reciban suficiente atención
            4. Mantén la coherencia en el desarrollo de la trama
            5. No permitas que se apresure el desarrollo narrativo
            
            Cuando generes la versión final, asegura que cada capítulo sea rico en detalles y desarrollo.
            Cuando te dirijas a otro agente, especifica su nombre."""
        }
        return prompts.get(self.role, "Eres un agente colaborativo en la creación de una historia.")

    async def generate_response(self, context: str, chat_history: List[Message], speaking_to: str = "todos") -> str:
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Agregar historial del chat relevante
        for msg in chat_history[-5:]:
            messages.append({
                "role": "user" if msg.agent_name != self.name else "assistant",
                "content": f"{msg.agent_name} {msg.speaking_to}: {msg.content}"
            })
        
        # Agregar el contexto actual
        messages.append({"role": "user", "content": context})
        
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        
        return response.choices[0].message.content 