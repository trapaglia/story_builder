from openai import OpenAI
import os
from typing import List, Dict
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Message:
    agent_name: str
    content: str
    timestamp: datetime
    speaking_to: str = "todos"  # Nuevo campo para indicar a quién habla

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
            "arbitro": "⚖️"
        }
        return emojis.get(self.role, "🎭")

    def _get_system_prompt(self) -> str:
        prompts = {
            "narrador": """Eres el Narrador Principal 📚, encargado de entretejer los eventos de manera cronológica.
            Tu trabajo es mantener la coherencia temporal de la historia y asegurarte de que cada evento tenga
            sentido en el contexto general. Cuando te dirijas a otro agente, especifica su nombre.""",
            
            "geografo": """Eres el Geógrafo 🗺️, experto en el mundo de la historia. Mantienes un registro detallado
            de cada ubicación, sus características, conexiones y cómo influyen en la trama. Cuando te dirijas a 
            otro agente, especifica su nombre.""",
            
            "personaje": """Eres un Agente de Personaje 👤, encargado de desarrollar y mantener la profundidad
            psicológica de tu personaje asignado. Conoces sus motivaciones más profundas, secretos y
            aspiraciones. Cuando te dirijas a otro agente, especifica su nombre.""",
            
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
        self.agents["narrador"] = StoryAgent("Narrador", "narrador", self.client)
        self.agents["geografo"] = StoryAgent("Geógrafo", "geografo", self.client)
        self.agents["arbitro"] = StoryAgent("Árbitro", "arbitro", self.client)

    def add_character_agent(self, character_name: str):
        agent_name = f"Personaje_{character_name}"
        self.agents[agent_name.lower()] = StoryAgent(agent_name, "personaje", self.client)

    async def generate_story(self, initial_idea: str, character_count: int, 
                           narration_style: str) -> Dict:
        # Primero, el árbitro analiza la idea
        arbitro_prompt = f"""Analiza esta idea inicial y coordina con los demás agentes:
        Idea: {initial_idea}
        Extensión: {character_count} caracteres
        Estilo: {narration_style}"""
        
        arbitro_response = await self.agents["arbitro"].generate_response(
            arbitro_prompt, self.chat_history
        )
        
        self.chat_history.append(Message(
            agent_name=f"{self.agents['arbitro'].emoji} Árbitro",
            content=arbitro_response,
            timestamp=datetime.now(),
            speaking_to="todos"
        ))
        
        # Los demás agentes responden
        responses = {}
        for name, agent in self.agents.items():
            if name != "arbitro":
                response = await agent.generate_response(
                    f"Responde a la propuesta del Árbitro: {arbitro_response}",
                    self.chat_history,
                    speaking_to="Árbitro"
                )
                self.chat_history.append(Message(
                    agent_name=f"{agent.emoji} {agent.name}",
                    content=response,
                    timestamp=datetime.now(),
                    speaking_to="→ Árbitro"
                ))
                responses[name] = response
        
        # El árbitro genera la versión final
        final_story = await self.agents["arbitro"].generate_response(
            "Basándote en todas las contribuciones, genera la versión final de la historia. IMPORTANTE: Comienza directamente con la narrativa, sin introducción ni explicaciones.",
            self.chat_history
        )
        
        return {
            "final_story": final_story,
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