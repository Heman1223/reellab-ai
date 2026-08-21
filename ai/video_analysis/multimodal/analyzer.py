"""Multimodal reel understanding — Content DNA.

    analyze_video(video_path) -> ContentDNA

This is where frames, audio and transcript become something a persona can react
to. The output is not a score. It is a description: what the hook is and how
long it runs, what happens in each scene, what the tone and emotional register
are, whether there is a CTA and where it lands.

Simulation quality is capped by the quality of this step. A persona reasoning
over a vague Content DNA will produce vague, useless reactions.

OWNER: Developer 2.
"""

from __future__ import annotations

from pathlib import Path

from llm import llm, with_fixture_fallback
from logging_utils import get_logger, log_event
from schemas import ContentDNA

import fixtures

logger = get_logger("video_analysis.multimodal")

PROMPT_VERSION = "content-dna-v0"

#: Short-form viewers decide inside roughly this window. Everything about hook
#: analysis is calibrated against it.
HOOK_WINDOW_SECONDS = 3.0


from video_analysis.preprocessing.preprocessing import extract_media
from video_analysis.transcription.transcription import transcribe, Transcript
from errors import TranscriptionFailedError, MalformedModelOutputError

def _build_prompt(transcript: str, duration_seconds: float) -> str:
    return f"""You are analysing a short-form vertical video for a creator tool.

Duration: {duration_seconds:.1f}s
Transcript: {transcript or "(no speech detected)"}

The attached frames are sampled in chronological order across the video. Use this sequence and the transcript to understand scene progression. Do not fabricate precision beyond what the available sampled timestamps support.

Describe this reel as structured data. Follow these strict rules:

1. Topic, Tone, & Emotion: Infer these holistically from the transcript and visual cues.
2. The Hook: Focus on the first {HOOK_WINDOW_SECONDS:.0f} seconds (early frames + start of transcript).
   - Determine what the attention mechanism is.
   - Set 'type' to a clear category (e.g. "question", "statement", "visual_surprise", "negative_hook", "story_start").
   - Set 'strength' (0-1). Be harsh if the hook just states a category without stakes.
3. Scenes: Identify meaningful scene boundaries.
   - Start and end times must be chronological, within 0 and {duration_seconds:.1f}.
   - Connect descriptions to the transcript where possible.
   - Do not hallucinate timestamps.
4. Visual Features:
   - Estimate cuts per second.
   - Note if there is readable on-screen text.
   - Estimate the proportion of runtime showing a human face (0-1).
5. The CTA (Call to Action): Use the tail of the transcript and final frames.
   - explicit CTA: directly asking for something.
   - implicit CTA: hinting or directing without a direct ask.
   - no CTA: 'present' is false.
   - If present, 'type' MUST be one of: "follow", "comment", "share", "save", "link", "other".
6. Audio Features:
   - Note whether music is present. Rate the energy (0-1).
   - (Speech presence and WPM are computed deterministically and will override your output, but provide sensible defaults).

Describe what is there. Do not rate the video or predict its performance.
Return JSON matching the ContentDNA schema."""


async def _analyze_with_model(video_path: str, video_id: str) -> ContentDNA:
    with extract_media(video_path) as media:
        try:
            transcript = transcribe(media.audio_path)
        except TranscriptionFailedError as e:
            logger.warning("Transcription failed, continuing with visual analysis only. Error: %s", str(e))
            transcript = Transcript(text="")
            
        result = await llm.complete_json(
            prompt=_build_prompt(transcript=transcript.text, duration_seconds=media.duration_seconds),
            prompt_version=PROMPT_VERSION,
            tier="multimodal",
            media_path=str(media.frame_paths[0].parent),
        )
        
        try:
            if isinstance(result.data, dict):
                result.data["duration_seconds"] = media.duration_seconds
                result.data["transcript"] = transcript.text
                
                audio = result.data.get("audio_features")
                if not isinstance(audio, dict):
                    audio = {}
                audio["has_speech"] = not transcript.is_empty
                audio["words_per_minute"] = transcript.words_per_minute
                if transcript.language:
                    audio["language"] = transcript.language
                result.data["audio_features"] = audio
                
            dna = ContentDNA.model_validate(result.data)
            
            for scene in dna.scenes:
                scene.end_seconds = max(0.0, min(scene.end_seconds, media.duration_seconds))
                scene.start_seconds = max(0.0, min(scene.start_seconds, media.duration_seconds))
                
            dna.scenes = sorted(dna.scenes, key=lambda s: s.start_seconds)
            
        except Exception as e:
            raise MalformedModelOutputError(f"Validation failed for ContentDNA: {str(e)}") from e
            
        return dna.model_copy(update={"video_id": video_id})


def _fixture_dna(video_id: str) -> ContentDNA:
    return fixtures.content_dna().model_copy(update={"video_id": video_id})


async def analyze_video(
    video_path: str | Path | None = None,
    video_id: str | None = None,
) -> tuple[ContentDNA, bool]:
    """Produce Content DNA for a reel. Returns `(content_dna, mock)`."""
    resolved_id = video_id or (Path(video_path).stem if video_path else "reel_unknown")

    dna, mock = await with_fixture_fallback(
        "video.analyze",
        lambda: _analyze_with_model(str(video_path), resolved_id),
        lambda: _fixture_dna(resolved_id),
    )

    log_event(
        logger,
        "content_dna_produced",
        video_id=dna.video_id,
        duration_seconds=dna.duration_seconds,
        hook_seconds=dna.hook.duration_seconds,
        scene_count=len(dna.scenes),
        mock=mock,
    )
    return dna, mock
