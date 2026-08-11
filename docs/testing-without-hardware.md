# Testing without hardware

CI uses fixtures, injectable providers, the simulator, and local fake HTTP servers; it never downloads large models. Tests can prove request shape, status persistence, Range behavior, checksums, atomic file placement, API errors, temporary-audio cleanup, and fail-closed robot safety. They cannot prove microphone/speaker behavior, model quality/performance, USB/network identity, daemon compatibility, SDK behavior, CM4 architecture/runtime compatibility, or physical safe-stop. Never report simulator results as hardware tests.
