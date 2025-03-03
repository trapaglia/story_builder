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

@dataclass
class ChapterOutline:
    number: int
    title: str
    summary: str
    key_events: List[str]
    characters_involved: List[str]
    locations: List[str]

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
        self._pending_chapters = []
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

        # Si hay capítulos pendientes, desarrollar el siguiente
        if self._pending_chapters:
            next_outline = self._pending_chapters.pop(0)
            next_chapter = async_to_sync(self._develop_chapter)(
                next_outline, 
                [agent.name.split('_')[1] for agent in self.agents.values() if 'personaje' in agent.name.lower()],
                "descriptivo"  # Esto debería venir del estado de la historia
            )
            self.story_state.chapters.append(next_chapter)
            self.story_state.current_chapter += 1
            self.story_state.total_chars += len(next_chapter.content)
            
            return {
                "chapter_number": next_chapter.number,
                "chapter_title": next_chapter.title,
                "content": next_chapter.content,
                "character_count": next_chapter.character_count,
                "is_complete": len(self._pending_chapters) == 0,
                "total_chapters": self.story_state.total_chapters
            }
        
        return {
            "is_complete": True,
            "total_chapters": len(self.story_state.chapters),
            "total_chars": self.story_state.total_chars
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
        # Paso 1: El planeador crea el esquema completo de capítulos
        planner_prompt = f"""Desarrolla un esquema detallado de capítulos para esta historia:
        
        Idea: {initial_idea}
        Personajes principales: {", ".join(character_names)}
        Extensión mínima sugerida: {character_count} caracteres
        Estilo: {narration_style}
        
        Para cada capítulo, proporciona:
        1. Título
        2. Resumen breve
        3. Eventos clave
        4. Personajes involucrados
        5. Ubicaciones principales
        
        IMPORTANTE:
        - Desarrolla una estructura coherente y progresiva
        - Asegura que cada personaje tenga momentos significativos
        - Distribuye el desarrollo de la trama de manera equilibrada"""

        chapter_outline = await self.agents["planeador"].generate_response(
            planner_prompt, self.chat_history
        )
        
        await self.process_agent_interaction(Message(
            agent_name=f"{self.agents['planeador'].emoji} Planeador",
            content=chapter_outline,
            timestamp=datetime.now(),
            speaking_to="todos"
        ))

        # Procesar el esquema y crear la estructura de capítulos
        chapters_data = self._parse_chapter_outline(chapter_outline)
        self.story_state.chapters = []
        self.story_state.total_chapters = len(chapters_data)

        # Paso 2: Desarrollar cada capítulo secuencialmente
        first_chapter = await self._develop_chapter(chapters_data[0], character_names, narration_style)
        
        # Almacenar el primer capítulo y preparar el estado para los siguientes
        self.story_state.chapters.append(first_chapter)
        self.story_state.current_chapter = 0
        self.story_state.total_chars = len(first_chapter.content)
        
        # Almacenar los esquemas restantes para desarrollo posterior
        self._pending_chapters = chapters_data[1:]

        return {
            "final_story": f"Capítulo {first_chapter.number}: {first_chapter.title}\n\n{first_chapter.content}",
            "chat_history": [
                {
                    "agent": msg.agent_name,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "speaking_to": msg.speaking_to
                }
                for msg in self.chat_history
            ],
            "has_more_chapters": len(self._pending_chapters) > 0,
            "total_chapters": self.story_state.total_chapters,
            "current_chapter": 1,
            "total_chars": self.story_state.total_chars
        }

    async def _develop_chapter(self, chapter_outline: ChapterOutline, character_names: List[str], narration_style: str) -> Chapter:
        # El geógrafo desarrolla las ubicaciones
        geography_prompt = f"""Desarrolla descripciones detalladas para las ubicaciones de este capítulo:
        Ubicaciones: {', '.join(chapter_outline.locations)}
        Contexto del capítulo: {chapter_outline.summary}"""
        
        geography_response = await self.agents["geografo"].generate_response(
            geography_prompt, self.chat_history
        )
        
        await self.process_agent_interaction(Message(
            agent_name=f"{self.agents['geografo'].emoji} Geógrafo",
            content=geography_response,
            timestamp=datetime.now(),
            speaking_to="→ Narrador"
        ))

        # Los personajes desarrollan sus motivaciones y acciones
        character_responses = []
        for name in chapter_outline.characters_involved:
            if f"personaje_{name.lower()}" in self.agents:
                character_prompt = f"""Desarrolla las acciones y motivaciones de tu personaje para este capítulo:
                Contexto: {chapter_outline.summary}
                Eventos clave: {', '.join(chapter_outline.key_events)}"""
                
                character_response = await self.agents[f"personaje_{name.lower()}"].generate_response(
                    character_prompt, self.chat_history
                )
                
                await self.process_agent_interaction(Message(
                    agent_name=f"{self.agents[f'personaje_{name.lower()}'].emoji} Personaje_{name}",
                    content=character_response,
                    timestamp=datetime.now(),
                    speaking_to="→ Narrador"
                ))
                character_responses.append(character_response)

        # El narrador integra todo en la versión final del capítulo
        narrator_prompt = f"""Desarrolla el capítulo completo integrando todos los elementos:
        
        Título: {chapter_outline.title}
        Resumen: {chapter_outline.summary}
        Eventos clave: {', '.join(chapter_outline.key_events)}
        Descripciones de ubicaciones: {geography_response}
        Desarrollo de personajes: {' | '.join(character_responses)}
        Estilo narrativo: {narration_style}
        
        IMPORTANTE: Comienza directamente con la narrativa, sin introducción ni explicaciones."""
        
        chapter_content = await self.agents["narrador"].generate_response(
            narrator_prompt, self.chat_history
        )
        
        return Chapter(
            number=chapter_outline.number,
            title=chapter_outline.title,
            content=chapter_content,
            character_count=len(chapter_content)
        )

    def _parse_chapter_outline(self, outline: str) -> List[ChapterOutline]:
        # Implementar la lógica para parsear el esquema de capítulos del planeador
        # y convertirlo en una lista de ChapterOutline
        # Esta es una implementación básica que deberías adaptar según el formato exacto
        # que genere el planeador
        chapters = []
        # ... lógica de parsing ...
        return chapters 