# Reproducible demo-video build

The public demo is generated from the installed LineageProof CLI and checked-in synthetic
fixtures. It does not record a desktop, browser session, account, shell history, customer data,
credential, production DataHub response, or third-party music.

## Visual direction

- 1920x1080, 16:9, warm-neutral editorial document composition.
- A 70/30 evidence-and-decision grid creates one stable reading path.
- Blue identifies evidence; red is reserved for blocking risk.
- The video uses system fonts and generated text/geometry only. It contains no third-party logo.
- Terminal results are captured from actual CLI output rather than invented interface screens.

## Build on macOS

```bash
uv run --python 3.12 --no-project --no-cache \
  --with '.[dev]' --with pillow \
  python scripts/build_demo_frames.py

swiftc -parse-as-library scripts/render_demo.swift \
  -o dist/demo-video/render_demo

dist/demo-video/render_demo \
  dist/demo-video/scene-manifest.json \
  dist/demo-video/frames \
  dist/demo-video/audio \
  dist/demo-video/LineageProof_Demo_1080p_en.mp4 \
  dist/demo-video/timeline.json
```

The renderer refuses a timeline of three minutes or longer. It also emits
`LineageProof_Demo_en.srt` with sentence-level English subtitle cues.

## Verified local artifact

- Render date: 2026-07-18 Asia/Shanghai.
- Video: `dist/demo-video/LineageProof_Demo_1080p_en.mp4`.
- Duration: 177.832 seconds.
- Tracks: one H.264 video track and one AAC audio track.
- Canvas: 1920x1080.
- Video SHA-256: `72db7b5d61d5aa51969973571376e7e3b5d5248ba0e77ca76bceab5c20b59f83`.
- Captions: 30 cues, no line longer than 54 characters.
- SRT SHA-256: `c7c298e8dbd6f594c2ba2607e97d8ca857d3695857c63d78e68ef01b5a306bd4`.
- Quick Look decoded the final MP4 cover frame without rotation or crop errors.
- A binary-string scan found no local user path, username, or email-like string.

## Output boundary

- `dist/demo-video/` is generated and excluded from the public source archive.
- The source archive includes the Python storyboard generator and Swift renderer.
- Only the finished MP4 and SRT should be uploaded to the judge-accessible video host.
- After upload, verify duration, playback, captions, and access in a signed-out browser.
