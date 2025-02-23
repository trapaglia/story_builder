from openai import OpenAI
import os
from typing import List, Dict, Tuple, Optional
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
    number: int
    title: str
    content: str
    character_count: int
    feedback: List[str] = None

@dataclass
class StoryState:
    current_chapter: int = 0
    total_chapters: int = 0
    chapters: List[Chapter] = None
    is_complete: bool = False
    total_chars: int = 0

    def __post_init__(self):
        if self.chapters is None:
            self.chapters = []

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

            IMPORTANTE: Debes incorporar TODOS los personajes proporcionados en la idea inicial y mantener
            la esencia de la idea original en todo momento.""",
            
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
        self.story_state = StoryState()
        self._initialize_agents()

    def reset_state(self):
        """Reinicia el estado del orquestador para una nueva historia"""
        self.chat_history = []
        self.story_state = StoryState()
        # Mantener solo los agentes base, eliminar personajes
        base_agents = {name: agent for name, agent in self.agents.items() 
                      if "personaje" not in name.lower()}
        self.agents = base_agents

    async def process_chapter_feedback(self, feedback: str) -> Dict:
        """Procesa el feedback del usuario sobre un capítulo"""
        # El árbitro analiza el feedback
        arbitro_prompt = f"""Analiza este feedback del lector sobre el capítulo actual:
        Feedback: {feedback}
        
        Coordina con los agentes para ajustar la narrativa si es necesario."""
        
        arbitro_response = await self.agents["arbitro"].generate_response(
            arbitro_prompt, self.chat_history
        )
        
        await self.process_agent_interaction(Message(
            agent_name=f"{self.agents['arbitro'].emoji} Árbitro",
            content=arbitro_response,
            timestamp=datetime.now(),
            speaking_to="todos"
        ))

        # El planeador considera el feedback para los siguientes capítulos
        planner_response = await self.agents["planeador"].generate_response(
            f"Considera este feedback para ajustar los próximos eventos: {arbitro_response}",
            self.chat_history
        )
        
        await self.process_agent_interaction(Message(
            agent_name=f"{self.agents['planeador'].emoji} Planeador",
            content=planner_response,
            timestamp=datetime.now(),
            speaking_to="→ Narrador"
        ))

        return {
            "chat_history": [
                {
                    "agent": msg.agent_name,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "speaking_to": msg.speaking_to
                }
                for msg in self.chat_history[-2:]  # Solo devolver los últimos 2 mensajes
            ]
        }

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
            chapters = content.split("Capítulo")
            self.story_state.total_chapters = len(chapters) - 1
            
            for i, chapter in enumerate(chapters[1:], 1):  # Empezamos desde 1 para saltar el split vacío
                title = chapter.split("\n")[0].strip()
                content = "\n".join(chapter.split("\n")[1:]).strip()
                self.story_state.chapters.append(
                    Chapter(number=i, title=title, content=content, character_count=len(content))
                )
            
            # Devolver solo el primer capítulo inicialmente
            first_chapter = self.story_state.chapters[0]
            return f"Capítulo {first_chapter.number}: {first_chapter.title}\n\n{first_chapter.content}", total_chars
        
        return content, total_chars

    def get_next_chapter(self, feedback: Optional[str] = None) -> Dict:
        if feedback and self.story_state.current_chapter < len(self.story_state.chapters):
            current_chapter = self.story_state.chapters[self.story_state.current_chapter]
            if current_chapter.feedback is None:
                current_chapter.feedback = []
            current_chapter.feedback.append(feedback)

        self.story_state.current_chapter += 1
        if self.story_state.current_chapter >= len(self.story_state.chapters):
            return {
                "is_complete": True,
                "total_chapters": len(self.story_state.chapters),
                "total_chars": self.story_state.total_chars
            }

        next_chapter = self.story_state.chapters[self.story_state.current_chapter]
        return {
            "chapter_number": next_chapter.number,
            "chapter_title": next_chapter.title,
            "content": next_chapter.content,
            "character_count": next_chapter.character_count,
            "is_complete": False,
            "total_chapters": len(self.story_state.chapters)
        }

    async def process_agent_interaction(self, message: Message) -> Dict:
        self.chat_history.append(message)
        return {
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

    async def generate_story(self, initial_idea: str, character_count: int, 
                           narration_style: str, character_names: List[str]) -> Dict:
        # El planeador desarrolla la estructura inicial
        characters_str = ", ".join(character_names)
        planner_prompt = f"""Analiza esta idea y desarrolla un plan narrativo complejo:
        Idea: {initial_idea}
        Personajes principales: {characters_str}
        Extensión: {character_count} caracteres
        Estilo: {narration_style}
        
        IMPORTANTE: Asegúrate de incluir y desarrollar TODOS los personajes mencionados.
        Desarrolla un plan que incluya giros argumentales, misterios y desarrollo de personajes."""

        # Proceso de generación paso a paso con notificaciones en vivo
        plan_response = await self.agents["planeador"].generate_response(
            planner_prompt, self.chat_history
        )
        
        await self.process_agent_interaction(Message(
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
        
        await self.process_agent_interaction(Message(
            agent_name=f"{self.agents['narrador'].emoji} Narrador",
            content=narrator_response,
            timestamp=datetime.now(),
            speaking_to="todos"
        ))

        # El geógrafo propone escenarios y conexiones
        geography_prompt = f"Analiza la estructura narrativa y propón escenarios y conexiones geográficas: {narrator_response}"
        geography_response = await self.agents["geografo"].generate_response(
            geography_prompt, self.chat_history,
            speaking_to="Planeador"
        )
        
        await self.process_agent_interaction(Message(
            agent_name=f"{self.agents['geografo'].emoji} Geógrafo",
            content=geography_response,
            timestamp=datetime.now(),
            speaking_to="→ Planeador"
        ))

        # Los personajes dan feedback y desarrollan sus motivaciones
        for name, agent in self.agents.items():
            if "personaje" in name.lower():
                character_prompt = f"""Analiza la estructura narrativa desde la perspectiva de tu personaje.
                Desarrolla tus motivaciones, secretos y conexiones con la trama: {narrator_response}
                Considera también los escenarios propuestos: {geography_response}"""
                
                character_response = await agent.generate_response(
                    character_prompt, self.chat_history,
                    speaking_to="Planeador"
                )
                
                await self.process_agent_interaction(Message(
                    agent_name=f"{agent.emoji} {agent.name}",
                    content=character_response,
                    timestamp=datetime.now(),
                    speaking_to="→ Planeador"
                ))

        # El planeador ajusta basado en todo el feedback
        planner_adjustment = await self.agents["planeador"].generate_response(
            "Ajusta el plan considerando todas las contribuciones y feedback recibidos.",
            self.chat_history
        )
        
        await self.process_agent_interaction(Message(
            agent_name=f"{self.agents['planeador'].emoji} Planeador",
            content=planner_adjustment,
            timestamp=datetime.now(),
            speaking_to="→ Narrador"
        ))

        # El narrador genera la versión final
        final_prompt = f"""Genera la versión final de la historia basándote en el plan ajustado.
        Si supera los 10000 caracteres, divídela en capítulos.
        IMPORTANTE: Comienza directamente con la narrativa, sin introducción ni explicaciones."""
        
        final_story = await self.agents["narrador"].generate_response(
            final_prompt, self.chat_history
        )

        # Formatear la historia y contar caracteres
        formatted_story, total_chars = self._format_story(final_story, character_count)
        self.story_state.total_chars = total_chars
        
        return {
            "final_story": formatted_story,
            "chat_history": [
                {
                    "agent": msg.agent_name,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "speaking_to": msg.speaking_to
                }
                for msg in self.chat_history
            ],
            "has_more_chapters": len(self.story_state.chapters) > 1,
            "total_chapters": len(self.story_state.chapters),
            "current_chapter": 1,
            "total_chars": total_chars
        } 