# RelayCart overview production

The 1:50 overview presents the business problem, the engineering decisions, and the
observed customer outcomes. It uses original October 3 page captures, rather than
adding another layer to a previously edited video. The detailed 3:25 walkthrough
remains available for inspection of the complete workflow graphs.

The footage shows a synthetic incident using live n8n executions and GoHighLevel
records. It supports the recorded results; it does not establish production
revenue impact. First-person narration describes the project author's design.

## Source and composition

`overview-story.json` declares the raw recording filenames, source offsets, crop
rectangles, narration, and design. The renderer computes scene lengths from the
speech, retaining natural pacing. Clips hold their last frame when narration is
longer than the selected footage. No recorded action is sped up. The two customer
cases are a comparison of separate recorded views, not simultaneous activity.

The video uses original application pixels in editorial frames, enlarged details,
animated outlines, a simple architecture diagram, and one burned-in English caption
layer. It has no additional embedded subtitle track that could display a duplicate.
The SRT is available separately for accessibility and reuse.

## Reproduce

Use the local Kokoro model and tools described in [the production notes](README.md).
Pillow supplies the typography and editorial layout. The speech voice is `am_michael`.
Source recordings and speech weights stay outside the repository.

```bash
python docs/demo-production/render-overview.py \
  --raw /path/to/original/page-recordings \
  --tools /path/to/kokoro-assets \
  --work /tmp/relaycart-overview \
  --output /tmp/RelayCart-Overview.mp4
```

The renderer writes source hashes, chapter timings, the caption file, and the audio
master to the work directory. Review these and the full output before publishing.

## Final review

[Review measurements](overview-review.json) bind the checks to the published SHA-256.
All 36 sampled chapter frames were visually inspected. The complete export decoded
without errors, and Chromium decoded audio, played the video, sought to eight
review points, and reached the end without a media error.

The encoded audio matches the narration master in every chapter with correlation
above 0.9999; decoded peaks stay below full scale. Spoken narration ends before
the final frame. Automatic transcription matched approximately 94% of the script
words before normalizing proper names and numbers; the transcript was checked
against the script. This is an automated speech check, not a human listening claim.

There is one caption band, 24 non-overlapping cues, and no embedded subtitle stream.
Source recording hashes, output duration, and audio measurements are retained in
the review record. The live incident workflow was not rerun to create this edit.
