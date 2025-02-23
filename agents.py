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

class StoryAgent:
    def __init__(self, name: str, role: str, client: OpenAI):
        self.name = name
        self.role = role
        self.client = client
        self.memory: List[Message] = []
        self.system_prompt = self._get_system_prompt()

    def _get_system_prompt(self) -> str:
        prompts = {
            "narrador": """Eres el Narrador Principal, encargado de entretejer los eventos de manera cronológica.
            Tu trabajo es mantener la coherencia temporal de la historia y asegurarte de que cada evento tenga
            sentido en el contexto general. Debes consultar con el geógrafo para ubicaciones y con los agentes
            de personajes para sus motivaciones.""",
            
            "geografo": """Eres el Geógrafo, experto en el mundo de la historia. Mantienes un registro detallado
            de cada ubicación, sus características, conexiones y cómo influyen en la trama. Trabajas en estrecha
            colaboración con el Narrador y los agentes de personajes para asegurar que las ubicaciones sean
            coherentes con la historia y las motivaciones de los personajes.""",
            
            "personaje": """Eres un Agente de Personaje, encargado de desarrollar y mantener la profundidad
            psicológica de tu personaje asignado. Conoces sus motivaciones más profundas, secretos y
            aspiraciones, incluso aquellas que aún no se han revelado en la historia.""",
            
            "arbitro": """Eres el Árbitro, el coordinador principal de la historia. Tu rol es facilitar la
            comunicación entre todos los agentes y tomar decisiones finales sobre el desarrollo de la trama.
            Debes consultar con cada agente relevante antes de aprobar cambios significativos en la historia."""
        }
        return prompts.get(self.role, "Eres un agente colaborativo en la creación de una historia.")

    async def generate_response(self, context: str, chat_history: List[Message]) -> str:
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Agregar historial del chat relevante
        for msg in chat_history[-5:]:  # Últimos 5 mensajes para contexto
            messages.append({
                "role": "user" if msg.agent_name != self.name else "assistant",
                "content": f"{msg.agent_name}: {msg.content}"
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
        arbitro_prompt = f"""Analiza esta idea inicial para una historia:
        Idea: {initial_idea}
        Extensión: {character_count} caracteres
        Estilo: {narration_style}
        
        Por favor, coordina con los demás agentes para desarrollar esta historia."""
        
        arbitro_response = await self.agents["arbitro"].generate_response(
            arbitro_prompt, self.chat_history
        )
        
        self.chat_history.append(Message(
            agent_name="Árbitro",
            content=arbitro_response,
            timestamp=datetime.now()
        ))
        
        # Los demás agentes responden
        responses = {}
        for name, agent in self.agents.items():
            if name != "arbitro":
                response = await agent.generate_response(
                    f"Responde a la propuesta del Árbitro: {arbitro_response}",
                    self.chat_history
                )
                self.chat_history.append(Message(
                    agent_name=agent.name,
                    content=response,
                    timestamp=datetime.now()
                ))
                responses[name] = response
        
        # El árbitro genera la versión final
        final_story = await self.agents["arbitro"].generate_response(
            "Basándote en todas las contribuciones, genera la versión final de la historia.",
            self.chat_history
        )
        
        return {
            "final_story": final_story,
            "chat_history": [
                {"agent": msg.agent_name, "content": msg.content, 
                 "timestamp": msg.timestamp.isoformat()}
                for msg in self.chat_history
            ]
        } 