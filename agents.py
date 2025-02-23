from openai import OpenAI
import os
from typing import List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Message:
    agent_name: str
    content: str
    timestamp: datetime
    speaking_to: str = "todos"

@dataclass
class Chapter:
    title: str
    content: str
    character_count: int

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
            "narrador": """Eres el Narrador Principal 📚, encargado de entretejer los eventos de manera cronológica.
            Tu trabajo es mantener la coherencia temporal de la historia y asegurarte de que cada evento tenga
            sentido en el contexto general. Si la historia supera los 10000 caracteres, debes dividirla en capítulos.
            Cuando te dirijas a otro agente, especifica su nombre.""",
            
            "geografo": """Eres el Geógrafo 🗺️, experto en el mundo de la historia. Mantienes un registro detallado
            de cada ubicación, sus características, conexiones y cómo influyen en la trama. Cuando te dirijas a 
            otro agente, especifica su nombre.""",
            
            "personaje": """Eres un Agente de Personaje 👤, encargado de desarrollar y mantener la profundidad
            psicológica de tu personaje asignado. Conoces sus motivaciones más profundas, secretos y
            aspiraciones. Cuando te dirijas a otro agente, especifica su nombre.""",
            
            "planeador": """Eres el Planeador 🎯, el arquitecto maestro de la trama. Tu objetivo es crear una narrativa 
            compleja y envolvente que mantenga al lector en constante expectativa. Tus responsabilidades incluyen:

            1. Planear giros argumentales sorprendentes
            2. Crear misterios que se resolverán gradualmente
            3. Entretejer las historias personales de los personajes con la trama principal
            4. Planear la revelación gradual de las verdaderas identidades de los personajes
            5. Introducir eventos sorpresa cuando la trama se vuelva demasiado predecible
            6. Mantener múltiples hilos narrativos que se entrelazan
            7. Crear conexiones sutiles entre eventos aparentemente no relacionados

            Trabajas en estrecha colaboración con el Narrador y los personajes para asegurarte de que tus planes
            sean coherentes con sus motivaciones y características.""",
            
            "arbitro": """Eres el Árbitro ⚖️, el coordinador principal de la historia. Tu rol es facilitar la
            comunicación entre todos los agentes y tomar decisiones finales sobre el desarrollo de la trama.
            
            IMPORTANTE: Cuando generes la versión final de la historia, NO incluyas ninguna introducción o 
            explicación. Comienza directamente con la narrativa de manera atrapante y envolvente.
            
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

class StoryOrchestrator:
    def __init__(self, client: OpenAI):
        self.client = client
        self.agents: Dict[str, StoryAgent] = {}
        self.chat_history: List[Message] = []
        self._initialize_agents()

    def _initialize_agents(self):
        self.agents["arbitro"] = StoryAgent("Árbitro", "arbitro", self.client)
        self.agents["planeador"] = StoryAgent("Planeador", "planeador", self.client)
        self.agents["narrador"] = StoryAgent("Narrador", "narrador", self.client)
        self.agents["geografo"] = StoryAgent("Geógrafo", "geografo", self.client)

    def add_character_agent(self, character_name: str):
        agent_name = f"Personaje_{character_name}"
        self.agents[agent_name.lower()] = StoryAgent(agent_name, "personaje", self.client)

    def _format_story(self, content: str, character_count: int) -> Tuple[str, int]:
        total_chars = len(content)
        if total_chars > 10000:
            # Solicitar al narrador que divida en capítulos
            chapters = content.split("Capítulo")
            formatted_content = ""
            for i, chapter in enumerate(chapters):
                if i > 0:  # Saltamos el primer split que está vacío
                    formatted_content += f"\n\nCapítulo {i}\n{chapter}"
            return formatted_content, total_chars
        return content, total_chars

    async def generate_story(self, initial_idea: str, character_count: int, 
                           narration_style: str) -> Dict:
        # El planeador desarrolla la estructura inicial
        planner_prompt = f"""Analiza esta idea y desarrolla un plan narrativo complejo:
        Idea: {initial_idea}
        Extensión: {character_count} caracteres
        Estilo: {narration_style}
        
        Desarrolla un plan que incluya giros argumentales, misterios y desarrollo de personajes."""
        
        plan_response = await self.agents["planeador"].generate_response(
            planner_prompt, self.chat_history
        )
        
        self.chat_history.append(Message(
            agent_name=f"{self.agents['planeador'].emoji} Planeador",
            content=plan_response,
            timestamp=datetime.now(),
            speaking_to="todos"
        ))
        
        # El narrador recibe el plan y lo desarrolla
        narrator_prompt = f"Basándote en este plan del Planeador, desarrolla la estructura narrativa: {plan_response}"
        narrator_response = await self.agents["narrador"].generate_response(
            narrator_prompt, self.chat_history
        )
        
        self.chat_history.append(Message(
            agent_name=f"{self.agents['narrador'].emoji} Narrador",
            content=narrator_response,
            timestamp=datetime.now(),
            speaking_to="todos"
        ))
        
        # Los personajes y el geógrafo dan feedback
        responses = {}
        for name, agent in self.agents.items():
            if name not in ["arbitro", "narrador", "planeador"]:
                response = await agent.generate_response(
                    f"Analiza esta estructura narrativa y proporciona feedback desde tu perspectiva: {narrator_response}",
                    self.chat_history,
                    speaking_to="Planeador"
                )
                self.chat_history.append(Message(
                    agent_name=f"{agent.emoji} {agent.name}",
                    content=response,
                    timestamp=datetime.now(),
                    speaking_to="→ Planeador"
                ))
                responses[name] = response
        
        # El planeador ajusta basado en el feedback
        planner_adjustment = await self.agents["planeador"].generate_response(
            "Ajusta el plan basándote en todo el feedback recibido.",
            self.chat_history
        )
        
        self.chat_history.append(Message(
            agent_name=f"{self.agents['planeador'].emoji} Planeador",
            content=planner_adjustment,
            timestamp=datetime.now(),
            speaking_to="→ Narrador"
        ))
        
        # El narrador genera la versión final
        final_story = await self.agents["narrador"].generate_response(
            f"Genera la versión final de la historia basándote en el plan ajustado. Si supera los 10000 caracteres, divídela en capítulos. IMPORTANTE: Comienza directamente con la narrativa.",
            self.chat_history
        )
        
        # Formatear la historia y contar caracteres
        formatted_story, total_chars = self._format_story(final_story, character_count)
        
        # Añadir el conteo de caracteres al final
        final_content = f"{formatted_story}\n\n---\nTotal de caracteres: {total_chars}"
        
        return {
            "final_story": final_content,
            "chat_history": [
                {
                    "agent": msg.agent_name,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "speaking_to": msg.speaking_to
                }
                for msg in self.chat_history
            ]
        } 