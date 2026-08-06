# Voice adapters

Mock ASR/TTS and console input/output are dependency-free. Optional local adapters must sit behind protocols and extras. Candidate investigations include whisper.cpp/faster-whisper tiny-class ASR, Piper, and Kokoro, but OS/ARM64 wheel, model license, memory, microphone format, latency and Reachy media integration must be verified before selection. No voice model is downloaded at startup or required in tests. Raw audio is not persisted.
