# Member 2 Runtime Validation Harness

This dedicated runtime validation harness exists to prove the complete End-to-End Member-2 Video Analysis pipeline works using a real Python environment with actual FFmpeg binaries.

Because `feature/video-analysis` integrates advanced AI models (Gemini for reasoning and Hugging Face Gemma for multimodal analysis) alongside heavy deterministic processing (FFprobe for metadata, faster-whisper for transcription, FFmpeg for frame/audio extraction), this script allows any teammate with the correct local dependencies to run the full pipeline without relying on external UI triggers or backend endpoints.

## Prerequisites

To execute this validation harness, you must have the following installed on your machine:
1. **Python 3.10+** and `pip`
2. **FFmpeg** and **FFprobe** (must be available in your system's PATH)
3. The AI dependencies installed (e.g. `pip install -r ai/requirements.txt`)

## Configuration

Your local `.env` file (at the root of the repository) must have the following configuration:

```env
# Reasoning provider
AI_PROVIDER=gemini
AI_API_KEY=your_actual_gemini_api_key
REASONING_MODEL=gemini-1.5-pro

# Multimodal provider
MULTIMODAL_PROVIDER=huggingface
HF_TOKEN=your_actual_hugging_face_token
HF_MODEL=google/gemma-4-31B-it
```

*Note: NEVER commit your actual API keys or tokens to version control.*

## Running the Validation

1. Prepare a short test video (preferably < 30 seconds). Both MP4 and MOV formats are supported.
2. From the root of the repository, execute the harness via Python:

```bash
python ai/tests/runtime_validation.py path/to/your/test_video.mp4
```

## Understanding the Output

The script runs sequentially through the following real steps:
- **Dependency Checks**: Confirms `ffmpeg` and python packages are accessible.
- **Routing Checks**: Proves `provider_for("reasoning")` and `provider_for("multimodal")` branch securely to Gemini and Hugging Face without leaking across boundaries.
- **Preprocessing**: Actually extracts base64 frames and 16kHz mono audio.
- **Transcription**: Uses `faster-whisper` on the extracted audio.
- **Model Invocation**: Sends the actual prompt and image payloads to Hugging Face Gemma to guarantee API interoperability.
- **ContentDNA Validation**: Runs the actual deterministic overrides (duration from FFprobe, speech presence from Whisper) and boundaries.
- **Counterfactuals**: Uses Gemini reasoning to generate variants off the ContentDNA.

If any stage fails, the harness will report `[FAIL]` and halt execution with a precise error message. If all stages pass, you will see a final `RUNTIME VALIDATION PASSED` message.
