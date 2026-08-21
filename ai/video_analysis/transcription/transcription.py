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


def transcribe(audio_path: str | Path) -> Transcript:
    """Transcribe an extracted audio track.

    TODO(Developer 2):
      - `faster-whisper` with the `base` or `small` model is the pragmatic
        choice: it runs on CPU, handles Indian-accented English acceptably, and
        needs no API budget. Uncomment it in requirements.txt.
      - Keep per-segment timings. The hook analysis needs to know what was said
        in the first three seconds specifically, not just overall.
      - Return an empty `Transcript` for silence rather than raising.
    """
    raise NotImplementedError(
        f"transcribe is not implemented yet (ai/video_analysis/transcription/). "
        f"Would transcribe: {audio_path}"
    )
