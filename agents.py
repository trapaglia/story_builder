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
        """Formatea la historia y la divide en capítulos basándose en el desarrollo narrativo"""
        total_chars = len(content)
        
        # Dividir en capítulos si la historia es extensa o tiene marcadores de capítulo
        if "Capítulo" in content or total_chars > 8000:
            # Si no hay marcadores de capítulo explícitos, dividir en secciones lógicas
            if "Capítulo" not in content:
                sections = content.split("\n\n")
                chapters = []
                current_chapter = []
                current_length = 0
                
                for section in sections:
                    current_length += len(section)
                    current_chapter.append(section)
                    
                    # Crear nuevo capítulo cuando hay un cambio significativo de escena
                    # o la longitud es apropiada para un capítulo
                    if current_length > 4000 and any(marker in section.lower() 
                        for marker in ["mientras tanto", "más tarde", "al día siguiente", 
                                     "en otro lugar", "posteriormente", "horas después"]):
                        chapter_content = "\n\n".join(current_chapter)
                        chapters.append(f"Capítulo {len(chapters) + 1}\n{chapter_content}")
                        current_chapter = []
                        current_length = 0
                
                # Agregar el último capítulo si hay contenido pendiente
                if current_chapter:
                    chapter_content = "\n\n".join(current_chapter)
                    chapters.append(f"Capítulo {len(chapters) + 1}\n{chapter_content}")
                
                content = "\n\n".join(chapters)
            
            chapters = content.split("Capítulo")
            self.story_state.total_chapters = len(chapters) - 1
            
            for i, chapter in enumerate(chapters[1:], 1):
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
        # Ajustar el prompt del planeador para enfatizar el desarrollo completo
        characters_str = ", ".join(character_names)
        planner_prompt = f"""Desarrolla un plan narrativo rico y detallado para esta historia:
        
        Idea: {initial_idea}
        Personajes principales: {characters_str}
        Extensión mínima sugerida: {character_count} caracteres
        Estilo: {narration_style}
        
        IMPORTANTE:
        1. Usa la extensión sugerida como guía mínima, no como límite
        2. Desarrolla cada elemento de la trama completamente
        3. Asegura que cada personaje tenga un arco narrativo significativo
        4. Crea suficientes eventos y subtramas para una historia rica
        5. No limites el desarrollo por consideraciones de longitud
        
        Desarrolla un plan que permita una historia verdaderamente envolvente."""

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