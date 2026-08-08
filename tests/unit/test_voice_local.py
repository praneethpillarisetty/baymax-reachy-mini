from pathlib import Path
from unittest.mock import patch
import wave

from baymax.voice.local import CommandASR, CommandTTS


class FakeMicrophone:
    def record(self, destination: Path) -> None:
        with wave.open(str(destination), "wb") as output:
            output.setparams((1, 2, 16_000, 160, "NONE", "not compressed"))
            output.writeframes(b"\0\0" * 160)


class FakeSpeaker:
    def __init__(self):
        self.played = False

    def play(self, audio_file: Path) -> None:
        assert audio_file.read_bytes() == b"wave"
        self.played = True


def test_command_asr_with_fake_audio(tmp_path):
    executable, model = tmp_path / "asr", tmp_path / "model"
    executable.write_text("")
    model.write_text("model")
    adapter = CommandASR(executable, model, ("--file", "{audio}"), FakeMicrophone())
    with patch("subprocess.run") as run:
        run.return_value.stdout = "recognized text\n"
        assert adapter.listen() == "recognized text"
        assert "input.wav" in " ".join(run.call_args.args[0])


def test_command_tts_with_fake_speaker(tmp_path):
    executable, model = tmp_path / "tts", tmp_path / "model"
    executable.write_text("")
    model.write_text("model")
    speaker = FakeSpeaker()
    adapter = CommandTTS(executable, model, ("--output", "{audio}"), speaker)

    def create_audio(command, **kwargs):
        Path(command[-1]).write_bytes(b"wave")

    with patch("subprocess.run", side_effect=create_audio):
        adapter.speak("hello")
    assert speaker.played
