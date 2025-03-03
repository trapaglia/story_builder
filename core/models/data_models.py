from dataclasses import dataclass
from typing import List
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