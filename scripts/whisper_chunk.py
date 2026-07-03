import os, sys
from faster_whisper import WhisperModel

chunk_path = sys.argv[1]
model = WhisperModel("tiny", device="cpu", compute_type="int8")
segments, info = model.transcribe(chunk_path, language="zh", beam_size=5)
print(f"LANG: {info.language}")
for s in segments:
    print(f"[{s.start:.1f}-{s.end:.1f}] {s.text}")
