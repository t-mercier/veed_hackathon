from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel


class Mode(str, Enum):
    concept = "concept"
    code = "code"


class Level(str, Enum):
    beginner = "beginner"
    advanced = "advanced"
    expert = "expert"


class Mood(str, Enum):
    friendly = "friendly"
    technical = "technical"
    energetic = "energetic"
    calm = "calm"


class JobType(str, Enum):
    repo = "repo"
    code = "code"
    prompt = "prompt"
    concept_algo = "concept_algo"


class GenerateRequest(BaseModel):
    prompt: str
    url: Optional[str] = None
    mode: Mode = Mode.concept
    level: Level = Level.beginner
    mood: Mood = Mood.friendly
    avatar: Optional[str] = None          # avatar ID (maps to preset image + voice)
    avatar_image_url: Optional[str] = None  # direct image URL override
    voice: Optional[str] = None           # TTS voice override
    robotic: bool = False                 # apply pitch/speed robotic effect
    request_id: Optional[str] = None      # Supabase video_requests row ID


class TTSScriptResponse(BaseModel):
    """3-part narration for Bote's TTS pipeline."""
    intro: str
    info: str
    outro: str


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: Optional[str] = None
    job_type: Optional[JobType] = None
    # Code path (legacy Manim — deprecated)
    animation_url: Optional[str] = None
    final_url: Optional[str] = None
    # Repo path (React Flow)
    architecture: Optional[dict[str, Any]] = None
    storyboard: Optional[dict[str, Any]] = None
    narration: Optional[dict[str, Any]] = None
    # Prompt path (scene-based explanation)
    explanation: Optional[dict[str, Any]] = None
    # Shared
    tts_script: Optional[TTSScriptResponse] = None
    error: Optional[str] = None
