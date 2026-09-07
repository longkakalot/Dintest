"""Read-only preflight tests; they do not alter audio stimuli."""
from __future__ import annotations
import sys
import tempfile
import unittest
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from preflight import validate_required_assets

def write_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b"\x00\x00" * 16)

class PreflightTests(unittest.TestCase):
    def test_reports_missing_voice_digits_noise_and_logo(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            base = Path(temp_directory)
            voice_dir = base / "bac"
            voice_dir.mkdir()
            write_wav(voice_dir / "bac_0.wav")
            errors = validate_required_assets({"Giọng Miền Bắc": voice_dir, "Giọng Miền Nam": base / "nam"}, base / "noise.wav", base / "logo.png")
        self.assertTrue(any("logo" in error for error in errors))
        self.assertTrue(any("noise" in error for error in errors))
        self.assertTrue(any("Thiếu file chữ số" in error for error in errors))
        self.assertTrue(any("Giọng Miền Nam" in error for error in errors))
    def test_accepts_complete_readable_wav_assets(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            base = Path(temp_directory)
            voice_dir = base / "bac"
            voice_dir.mkdir()
            for digit in range(10):
                write_wav(voice_dir / f"bac_{digit}.wav")
            noise = base / "noise.wav"
            logo = base / "logo.png"
            write_wav(noise)
            logo.write_bytes(b"\x89PNG\r\n\x1a\nplaceholder")
            errors = validate_required_assets({"Giọng Miền Bắc": voice_dir}, noise, logo)
        self.assertEqual(errors, [])

