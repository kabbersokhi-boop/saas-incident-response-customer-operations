# Narrated RelayCart demo

The October 20, 2026 edit adds a male synthetic voiceover, English captions,
animated chapter labels, and a progress indicator to the October 3 recording.
The 3:25 timeline and original recorded actions are preserved. The source UI
is uniformly scaled into a frame with a dedicated subtitle area; headings and
labels are editorial overlays. Source application data is not reconstructed.

The published MP4 includes captions in the picture for GitHub viewing, an
additional English subtitle track, AAC narration, and all 24 original chapters.
The standalone SRT and transcript accompany the video.

## Reproduce

Use Python 3.12 with `kokoro-onnx==0.6.0`, `onnxruntime`, `numpy`, and `soundfile`,
and FFmpeg with libx264 and libass. DejaVu Sans must be installed.
The renderer uses the [Kokoro model release](https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.1):

| File | SHA-256 |
| --- | --- |
| `kokoro-v1.0.onnx` | `beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a` |
| `voices-v1.0.bin` | `bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d` |

Voice: Kokoro `am_michael`, American English male, speed 1.0. Short scenes use
bounded pitch-preserving tempo adjustment, recorded in the timing report.
Sentence captions use the exact generated audio boundaries. `story.json`
contains every spoken sentence and the chapter schedule.

```bash
python docs/demo-production/render.py \
  --source /path/to/original/RelayCart-End-to-End-Demo.mp4 \
  --tools /path/to/kokoro-assets \
  --work /tmp/relaycart-narration \
  --output /tmp/RelayCart-End-to-End-Demo.mp4
```

The original silent input SHA-256 is
`99ec636c121a993e5da3b2a3fe23c5643243874641774066f745b4623e5c1b2c`.
It remains available in repository history at commit `981a2ec`. Keep temporary
WAV files and model assets outside the repository. Render into a new output
path, review it, then replace the published video.

Narration uses the [Apache-2.0 Kokoro model](https://huggingface.co/hexgrad/Kokoro-82M)
and [MIT-licensed Kokoro ONNX wrapper](https://github.com/thewh1teagle/kokoro-onnx/blob/main/LICENSE).
Model weights and font files are not redistributed.

## Final review

[Review measurements](review.json) record the published file hash and checks.
All 24 chapter starts, middles, and ends were visually inspected. The complete
video decoded without errors. Chromium played and decoded audio, sought to
four review points, and reached the end without a media error.

Local speech recognition matched approximately 93% of the script words before
normalizing proper names and spoken numbers. Its transcript was checked against
the script; this is an automated speech check, not a human listening review.
The encoded narration correlates with the mastered audio above 0.9999 in each
chapter, and no decoded samples clip. The final spoken sentence ends before
the video ends. Original screenshots continue to document the recorded run.
