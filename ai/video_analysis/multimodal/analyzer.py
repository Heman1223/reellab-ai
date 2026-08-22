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

def _build_prompt(duration_seconds: float) -> str:
    return f"""You are analysing a short-form vertical video for a creator tool.

Duration: {duration_seconds:.1f}s

The attached audio is the extracted track. Transcribe it verbatim and write it to the 'transcript' field.
The attached frames are sampled in chronological order across the video. Use this sequence and the audio to understand scene progression. Do not fabricate precision beyond what the available sampled timestamps support.

Describe this reel as structured data. Follow these strict rules:

1. Transcript: Transcribe the audio track as accurately as possible into the 'transcript' field.
2. Topic, Tone, & Emotion: Infer these holistically from the audio and visual cues.
3. The Hook: Focus on the first {HOOK_WINDOW_SECONDS:.0f} seconds (early frames + start of audio).
   - Determine what the attention mechanism is.
   - Set 'type' to a clear category (e.g. "question", "statement", "visual_surprise", "negative_hook", "story_start").
   - Set 'strength' (0-1). Be harsh if the hook just states a category without stakes.
4. Scenes: Identify meaningful scene boundaries.
   - Start and end times must be chronological, within 0 and {duration_seconds:.1f}.
   - Connect descriptions to the audio where possible.
   - Do not hallucinate timestamps.
5. Visual Features:
   - Estimate cuts per second.
   - Note if there is readable on-screen text.
   - Estimate the proportion of runtime showing a human face (0-1).
6. The CTA (Call to Action): Use the tail of the audio and final frames.
   - explicit CTA: directly asking for something.
   - implicit CTA: hinting or directing without a direct ask.
   - no CTA: 'present' is false.
   - If present, 'type' MUST be one of: "follow", "comment", "share", "save", "link", "other".
7. Audio Features:
   - Note whether music is present. Rate the energy (0-1).
   - Note whether speech is present.
   - For language, output the ISO 639-1 code if detected, else null.
   - words_per_minute can be 0.0 for now, we will compute it.

Describe what is there. Do not rate the video or predict its performance.
Return JSON matching the ContentDNA schema."""


async def _analyze_with_model(video_path: str, video_id: str) -> ContentDNA:
    with extract_media(video_path) as media:
        print("[VIDEO] provider: gemini")
        from config import settings
        print(f"[VIDEO] model: {settings.multimodal_model}")
        print("[VIDEO] Gemini request started")
        
        from llm import MediaAttachment
        attachments = []
        for path in media.frame_paths:
            att = MediaAttachment.from_path(str(path))
            if att: attachments.append(att)
            
        if media.audio_path:
            att = MediaAttachment.from_path(str(media.audio_path))
            if att: attachments.append(att)
        
        dna, metadata = await llm.complete_model(
            ContentDNA,
            prompt=_build_prompt(duration_seconds=media.duration_seconds),
            prompt_version=PROMPT_VERSION,
            tier="multimodal",
            media=attachments,
        )
        print("[VIDEO] Gemini response received")
        
        try:
            # Re-populate the deterministic fields
            dna.duration_seconds = media.duration_seconds
            dna.video_id = video_id
            
            if not dna.audio_features:
                from schemas.content import AudioFeatures
                dna.audio_features = AudioFeatures(has_speech=False, has_music=False, words_per_minute=0.0, energy=0.0)
            
            if dna.transcript:
                word_count = len(dna.transcript.split())
                mins = media.duration_seconds / 60.0
                dna.audio_features.words_per_minute = word_count / mins if mins > 0 else 0.0
                
            for scene in dna.scenes:
                scene.end_seconds = max(0.0, min(scene.end_seconds, media.duration_seconds))
                scene.start_seconds = max(0.0, min(scene.start_seconds, media.duration_seconds))
                
            dna.scenes = sorted(dna.scenes, key=lambda s: s.start_seconds)
            
        except Exception as e:
            raise MalformedModelOutputError(f"Validation failed for ContentDNA: {str(e)}") from e
            
        print("[VIDEO] ContentDNA validation passed")
        return dna


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
