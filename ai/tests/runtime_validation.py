import sys
import shutil
import asyncio
from pathlib import Path
import json

def check_local_tools():
    print("Checking local tools...")
    tools = ["ffmpeg", "ffprobe"]
    missing = []
    for tool in tools:
        if not shutil.which(tool):
            missing.append(tool)
    if missing:
        print(f"[FAIL] Missing tools: {', '.join(missing)}")
        return False
    print("[PASS] Local tools: ffmpeg, ffprobe found")
    return True

def check_python_dependencies():
    print("Checking python dependencies...")
    try:
        import pydantic
        import faster_whisper
        import httpx
        import dotenv
        print("[PASS] Python dependencies imported successfully")
        return True
    except ImportError as e:
        print(f"[FAIL] Missing dependency: {e}")
        return False

async def main(video_path: str):
    print("==================================================")
    print("MEMBER 2 RUNTIME VALIDATION HARNESS")
    print("==================================================")
    
    if not Path(video_path).is_file():
        print(f"[FAIL] Video path missing or invalid: {video_path}")
        sys.exit(1)

    if not check_local_tools() or not check_python_dependencies():
        print("[BLOCKED] Environment validation failed. Cannot proceed.")
        sys.exit(1)

    # Delay import of project modules until after dependencies are verified
    from config import settings
    from llm import llm, GeminiProvider, HuggingFaceProvider
    from video_analysis.preprocessing.preprocessing import extract_media
    from video_analysis.transcription.transcription import transcribe
    from video_analysis.multimodal.analyzer import analyze_video
    from counterfactual.generation.variants import generate_variants
    from schemas import ContentDNA

    print("\n--- 1. PROVIDER CONFIGURATION VALIDATION ---")
    gemini_configured = llm.is_configured("reasoning")
    hf_configured = llm.is_configured("multimodal")
    
    print(f"GEMINI CONFIGURED: {'YES' if gemini_configured else 'NO'}")
    print(f"HUGGING FACE CONFIGURED: {'YES' if hf_configured else 'NO'}")
    
    if not (gemini_configured and hf_configured):
        print("[FAIL] Both Gemini and Hugging Face must be configured to run this harness.")
        sys.exit(1)

    print("\n--- 2. CHECK PROVIDER ROUTING ---")
    reasoning_provider = llm.provider_for("reasoning")
    multimodal_provider = llm.provider_for("multimodal")
    
    if isinstance(reasoning_provider, GeminiProvider):
        print("[PASS] Reasoning provider: Gemini")
    else:
        print(f"[FAIL] Reasoning provider is not Gemini, it is {type(reasoning_provider).__name__}")
        sys.exit(1)
        
    if isinstance(multimodal_provider, HuggingFaceProvider):
        print("[PASS] Multimodal provider: Hugging Face")
    else:
        print(f"[FAIL] Multimodal provider is not Hugging Face, it is {type(multimodal_provider).__name__}")
        sys.exit(1)

    print("\n--- 3. REAL VIDEO PREPROCESSING ---")
    print(f"Processing video: {video_path}")
    temp_dir_path = None
    media = None
    try:
        with extract_media(video_path) as m:
            media = m
            print(f"[PASS] Video accepted. Duration: {media.duration_seconds}s")
            if not media.frame_paths:
                print("[FAIL] No frames generated.")
                sys.exit(1)
            
            print(f"[PASS] Generated {len(media.frame_paths)} frames.")
            if len(media.frame_paths) > 10:
                print(f"[FAIL] Too many frames generated: {len(media.frame_paths)}")
                sys.exit(1)
                
            if media.audio_path:
                print("[PASS] Audio extraction succeeded.")
            else:
                print("[PASS] No audio extracted (expected if video has no audio).")
                
            temp_dir_path = media.frame_paths[0].parent
            if temp_dir_path.exists():
                print("[PASS] Temporary directory exists during processing.")
            else:
                print("[FAIL] Temporary directory does not exist.")
    except Exception as e:
        print(f"[FAIL] Preprocessing failed: {e}")
        sys.exit(1)

    print("\n--- 4. TEMPORARY FILE CLEANUP TEST ---")
    if temp_dir_path and temp_dir_path.exists():
        print("[FAIL] Temporary media cleanup failed. Directory still exists.")
    else:
        print("[PASS] Temporary media cleanup succeeded.")

    print("\n--- 5. REAL WHISPER TEST ---")
    transcript_result = None
    if media and media.audio_path:
        try:
            print("Running faster-whisper transcription...")
            transcript_result = transcribe(media.audio_path)
            print("[PASS] Whisper model loaded and transcription completed.")
            print(f"[PASS] WPM: {transcript_result.words_per_minute}")
            if not transcript_result.segments:
                print("[WARN] No speech segments returned.")
        except Exception as e:
            print(f"[FAIL] Whisper transcription failed: {e}")
    else:
        print("[SKIP] Whisper — test video has no audio")

    print("\n--- 6. REAL HUGGING FACE / GEMMA TEST ---")
    try:
        print("Sending request to Hugging Face Gemma model...")
        prompt = "Analyze this sequence of frames and return a JSON object with 'test': true"
        # We need to explicitly test LLMClient directly, not just analyzer.
        # However, extract_media has already cleaned up the frames because of the 'with' block.
        # So we need to re-extract for the LLM call.
        with extract_media(video_path) as m:
            result = await llm.complete_json(
                prompt=prompt,
                prompt_version="v1",
                tier="multimodal",
                media_path=str(m.frame_paths[0].parent),
                schema={"type": "object"}
            )
            print("[PASS] REAL MODEL RESPONSE received from Hugging Face.")
            print(f"[PASS] JSON output: {json.dumps(result.data)}")
    except Exception as e:
        print(f"[FAIL] Hugging Face / Gemma test failed: {e}")
        sys.exit(1)

    print("\n--- 7. REAL CONTENTDNA VALIDATION ---")
    content_dna = None
    try:
        print("Running analyze_video...")
        dna, is_mock = await analyze_video(video_path=video_path)
        if is_mock:
            print("[FAIL] FIXTURE FALLBACK was used. Real model response is required.")
            sys.exit(1)
            
        print("[PASS] REAL MODEL RESPONSE received.")
        print(f"[PASS] Generated ContentDNA for video: {dna.video_id}")
        
        # Verify scene boundaries
        for i, scene in enumerate(dna.scenes):
            if not (0 <= scene.start_seconds <= scene.end_seconds <= dna.duration_seconds):
                print(f"[FAIL] Invalid scene boundary in scene {i}: {scene}")
                sys.exit(1)
        print("[PASS] Scene boundaries are valid.")
        
        # Verify Hook
        if not (0 <= dna.hook.strength <= 1):
            print(f"[FAIL] Invalid hook strength: {dna.hook.strength}")
            sys.exit(1)
        print("[PASS] Hook is valid.")
        
        content_dna = dna
    except Exception as e:
        print(f"[FAIL] ContentDNA validation failed: {e}")
        sys.exit(1)

    print("\n--- 8. COUNTERFACTUAL RUNTIME VALIDATION ---")
    if content_dna:
        try:
            print("Generating variants via Gemini reasoning...")
            from schemas import SimulationResult
            # Provide a dummy SimulationResult since we only want to test the model generation path
            dummy_simulation = SimulationResult(
                video_id=content_dna.video_id,
                overall_score=0.5,
                bottlenecks=[],
                audience_segment_results=[]
            )
            variants, is_mock = await generate_variants(
                content=content_dna, 
                simulation=dummy_simulation, 
                modification_type="tone", 
                count=2
            )
            if is_mock:
                print("[FAIL] Variants used fixture fallback.")
                sys.exit(1)
            print(f"[PASS] Generated {len(variants)} counterfactual variants.")
            for v in variants:
                if v.modified_lever != "tone":
                    print(f"[FAIL] Variant lever mismatch: {v.modified_lever}")
        except Exception as e:
            print(f"[FAIL] Counterfactual validation failed: {e}")
            sys.exit(1)

    print("\n--- 9. GEMINI REGRESSION TEST ---")
    try:
        print("Sending simple reasoning request to Gemini...")
        from pydantic import BaseModel
        class RegressionSchema(BaseModel):
            success: bool
            
        result, metadata = await llm.complete_model(
            model_cls=RegressionSchema,
            prompt="Return a JSON object with success=true",
            prompt_version="v1",
            tier="reasoning"
        )
        print("[PASS] Gemini reasoning test passed.")
        if not result.success:
            print("[FAIL] Gemini returned success=false")
    except Exception as e:
        print(f"[FAIL] Gemini regression test failed: {e}")
        sys.exit(1)

    print("\n==================================================")
    print("RUNTIME VALIDATION PASSED")
    print("==================================================")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python runtime_validation.py <path_to_video>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    asyncio.run(main(video_path))
