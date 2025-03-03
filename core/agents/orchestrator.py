from typing import Dict, List, Optional
from datetime import datetime
from openai import OpenAI
from asgiref.sync import async_to_sync

from core.models.data_models import Message, Chapter, StoryState, ChapterOutline
from core.agents.base_agent import StoryAgent

class StoryOrchestrator:
    def __init__(self, client: OpenAI):
        self.client = client
        self.agents: Dict[str, StoryAgent] = {}
        self.chat_history: List[Message] = []
        self.story_state = StoryState()
        self._pending_chapters = []
        self._initialize_agents()

    def _initialize_agents(self):
        self.agents["arbitro"] = StoryAgent("Árbitro", "arbitro", self.client)
        self.agents["planeador"] = StoryAgent("Planeador", "planeador", self.client)
        self.agents["narrador"] = StoryAgent("Narrador", "narrador", self.client)
        self.agents["geografo"] = StoryAgent("Geógrafo", "geografo", self.client)

    def reset_state(self):
        """Reinicia el estado del orquestador para una nueva historia"""
        self.chat_history = []
        self.story_state = StoryState()
        self._pending_chapters = []
        # Mantener solo los agentes base, eliminar personajes
        base_agents = {name: agent for name, agent in self.agents.items() 
                      if "personaje" not in name.lower()}
        self.agents = base_agents

    def add_character_agent(self, character_name: str):
        agent_name = f"Personaje_{character_name}"
        self.agents[agent_name.lower()] = StoryAgent(agent_name, "personaje", self.client)

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
                for msg in [message]  # Solo enviamos el mensaje actual
            ]
        }

    async def generate_story(self, initial_idea: str, character_count: int, 
                           narration_style: str, character_names: List[str]) -> Dict:
        # Paso 1: El planeador crea el esquema completo de capítulos
        planner_prompt = f"""Desarrolla un esquema detallado de capítulos para esta historia siguiendo EXACTAMENTE este formato para cada capítulo:

Capítulo [número]: [título descriptivo]
Resumen: [resumen conciso del capítulo]
Eventos clave:
- [evento principal]
- [evento secundario]
- [otros eventos relevantes...]
Personajes involucrados:
- [nombre del personaje principal]
- [nombre de personaje secundario]
- [otros personajes...]
Ubicaciones:
- [ubicación principal]
- [ubicación secundaria]
- [otras ubicaciones...]

[Repetir el mismo formato para cada capítulo]

Datos de la historia:
Idea: {initial_idea}
Personajes disponibles: {", ".join(character_names)}
Extensión sugerida: {character_count} caracteres
Estilo narrativo: {narration_style}

REGLAS IMPORTANTES:
1. DEBES usar EXACTAMENTE el formato especificado arriba
2. Cada capítulo DEBE tener todas las secciones en el orden mostrado
3. Usa guiones (-) para listar eventos, personajes y ubicaciones
4. El resumen debe ser conciso y claro
5. Incluye al menos 2-3 eventos clave por capítulo
6. Asegúrate de que cada personaje tenga momentos significativos
7. Especifica ubicaciones concretas, no genéricas
8. Mantén una progresión coherente entre capítulos
9. NO agregues secciones adicionales ni modifiques los nombres de las secciones
10. NO uses otros formatos de lista que no sean guiones (-)"""

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
        
        await self.process_agent_interaction(Message(
            agent_name=f"{self.agents['narrador'].emoji} Narrador",
            content=chapter_content,
            timestamp=datetime.now(),
            speaking_to="todos"
        ))
        
        return Chapter(
            number=chapter_outline.number,
            title=chapter_outline.title,
            content=chapter_content,
            character_count=len(chapter_content)
        )

    def _parse_chapter_outline(self, outline: str) -> List[ChapterOutline]:
        """
        Parsea el esquema de capítulos generado por el planeador y lo convierte en una lista de ChapterOutline.
        El formato esperado es:

        Capítulo 1: [Título]
        Resumen: [Texto]
        Eventos clave:
        - [Evento 1]
        - [Evento 2]
        Personajes involucrados:
        - [Personaje 1]
        - [Personaje 2]
        Ubicaciones:
        - [Ubicación 1]
        - [Ubicación 2]

        [Se repite el patrón para cada capítulo]
        """
        chapters = []
        current_chapter = None
        current_section = None
        
        # Dividir por líneas y limpiar espacios
        lines = [line.strip() for line in outline.split('\n') if line.strip()]
        
        for line in lines:
            # Detectar inicio de nuevo capítulo
            if line.lower().startswith('capítulo'):
                if current_chapter:
                    chapters.append(current_chapter)
                
                # Extraer número y título
                parts = line.split(':', 1)
                number = int(''.join(filter(str.isdigit, parts[0])))
                title = parts[1].strip() if len(parts) > 1 else f"Capítulo {number}"
                
                current_chapter = ChapterOutline(
                    number=number,
                    title=title,
                    summary="",
                    key_events=[],
                    characters_involved=[],
                    locations=[]
                )
                current_section = None
                continue
            
            # Detectar secciones
            if line.lower().startswith('resumen:'):
                current_section = 'summary'
                current_chapter.summary = line.split(':', 1)[1].strip()
                continue
            
            if line.lower().startswith('eventos clave:'):
                current_section = 'events'
                continue
            
            if line.lower().startswith('personajes involucrados:'):
                current_section = 'characters'
                continue
            
            if line.lower().startswith('ubicaciones:'):
                current_section = 'locations'
                continue
            
            # Procesar contenido según la sección actual
            if current_chapter and line.startswith('-'):
                content = line[1:].strip()
                if current_section == 'events':
                    current_chapter.key_events.append(content)
                elif current_section == 'characters':
                    current_chapter.characters_involved.append(content)
                elif current_section == 'locations':
                    current_chapter.locations.append(content)
            elif current_section == 'summary':
                # Agregar líneas adicionales al resumen
                current_chapter.summary += " " + line
        
        # Agregar el último capítulo
        if current_chapter:
            chapters.append(current_chapter)
        
        # Validar y limpiar los datos
        for chapter in chapters:
            chapter.summary = chapter.summary.strip()
            chapter.key_events = [event for event in chapter.key_events if event]
            chapter.characters_involved = [char for char in chapter.characters_involved if char]
            chapter.locations = [loc for loc in chapter.locations if loc]
            
            # Asegurar que hay al menos un valor en cada lista
            if not chapter.key_events:
                chapter.key_events = ["Desarrollo de la trama principal"]
            if not chapter.characters_involved:
                chapter.characters_involved = ["Personaje principal"]
            if not chapter.locations:
                chapter.locations = ["Ubicación principal"]
        
        return chapters

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