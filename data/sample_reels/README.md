# `data/sample_reels/`

Drop **small** development sample videos here (a few seconds, a few MB) so
Developer 2 can work on video analysis without a running backend or a real
upload flow.

## Video files are gitignored

The root `.gitignore` excludes `data/sample_reels/*` and all common video
extensions. This is deliberate — reels are large, binary, and often not ours to
redistribute. Share them over the team chat, not over Git.

## Getting a sample quickly

Any short vertical MP4 works. To generate a synthetic one with FFmpeg:

```bash
ffmpeg -f lavfi -i testsrc=size=1080x1920:rate=30:duration=15 \
       -f lavfi -i sine=frequency=440:duration=15 \
       -c:v libx264 -pix_fmt yuv420p -c:a aac \
       data/sample_reels/sample_15s.mp4
```

Then point the AI service at it:

```bash
curl -X POST http://localhost:8000/ai/video/analyze \
  -H 'Content-Type: application/json' \
  -d '{"videoPath": "data/sample_reels/sample_15s.mp4"}'
```

Uploads that arrive through the backend land in `uploads/` at the repo root
(also gitignored), not here.
