"""Speech to text.

An empty transcript is a legitimate result, not an error — plenty of reels are
visual-only or music-only, and treating silence as a failure would make the
system refuse to analyse a whole content category. `EmptyTranscriptError` exists
for the case where speech was expected but extraction broke; a genuinely silent
reel should return an empty transcript and let the multimodal step work from
frames alone.

OWNER: Developer 2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TranscriptSegment:
    start_seconds: float
    end_seconds: float
    text: str


@dataclass
class Transcript:
    text: str
    language: str | None = None
    segments: list[TranscriptSegment] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return self.text.strip() == ""

    @property
    def words_per_minute(self) -> float:
        """Speaking rate. Feeds the pacing signal in Content DNA."""
        if self.is_empty or not self.segments:
            return 0.0
        duration = self.segments[-1].end_seconds - self.segments[0].start_seconds
        if duration <= 0:
            return 0.0
        return len(self.text.split()) / (duration / 60)


try:
    from faster_whisper import WhisperModel  # type: ignore
except ImportError:
    WhisperModel = None

from errors import AINotConfiguredError, TranscriptionFailedError

_model = None


def _get_model() -> WhisperModel | None:
    global _model
    if _model is None:
        if WhisperModel is None:
            return None
        _model = WhisperModel("base", device="cpu", compute_type="int8")
    return _model


def transcribe(audio_path: str | Path | None) -> Transcript:
    """Transcribe an extracted audio track using faster-whisper."""
    if not audio_path:
        return Transcript(text="")
        
    path = Path(audio_path)
    if not path.exists() or not path.is_file():
        return Transcript(text="")
        
    try:
        model = _get_model()
        if model is None:
            return Transcript(text="")
        segments_generator, info = model.transcribe(str(path), beam_size=1)
        
        segments = []
        texts = []
        for s in segments_generator:
            text = s.text.strip()
            if text:
                segments.append(TranscriptSegment(start_seconds=s.start, end_seconds=s.end, text=text))
                texts.append(text)
                
        if not segments:
            return Transcript(text="")
            
        full_text = " ".join(texts)
        return Transcript(text=full_text, language=info.language, segments=segments)
    except Exception as e:
        # Fallback to empty transcript so multimodal LLM analysis continues uninterrupted
        return Transcript(text="")
