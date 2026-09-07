"""Read-only startup checks for the documented ``app/app.py`` application."""

from __future__ import annotations

import importlib.util
import wave
from pathlib import Path
from typing import Mapping

REQUIRED_DIGITS = frozenset(str(digit) for digit in range(10))
REQUIRED_RUNTIME_MODULES = ("pydub",)


def validate_runtime_dependencies() -> list[str]:
    """Return missing Python dependencies without installing or changing anything."""
    return [
        f"Thiếu Python dependency bắt buộc: {module}."
        for module in REQUIRED_RUNTIME_MODULES
        if importlib.util.find_spec(module) is None
    ]


def _validate_wav_file(path: Path, label: str) -> list[str]:
    if not path.is_file():
        return [f"Không tìm thấy {label}: {path}"]
    if path.stat().st_size == 0:
        return [f"{label} rỗng: {path}"]
    try:
        with wave.open(str(path), "rb") as wav_file:
            if wav_file.getnframes() == 0:
                return [f"{label} không có audio frames: {path}"]
    except (EOFError, wave.Error) as error:
        return [f"Không đọc được WAV {label}: {path} ({error})"]
    return []


def validate_required_assets(
    voice_map: Mapping[str, Path], noise_file: Path, logo_file: Path
) -> list[str]:
    """Validate files needed to begin a DIN session; never alter assets."""
    errors: list[str] = []
    if not logo_file.is_file() or logo_file.stat().st_size == 0:
        errors.append(f"Không tìm thấy hoặc logo rỗng: {logo_file}")
    elif logo_file.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
        errors.append(f"Logo PNG không hợp lệ: {logo_file}")
    errors.extend(_validate_wav_file(noise_file, "noise file"))
    for voice_label, voice_dir in voice_map.items():
        if not voice_dir.is_dir():
            errors.append(f"Không tìm thấy thư mục audio cho {voice_label}: {voice_dir}")
            continue
        wav_files = {path.stem.rsplit("_", 1)[-1]: path for path in voice_dir.glob("*.wav")}
        missing_digits = sorted(REQUIRED_DIGITS - set(wav_files))
        if missing_digits:
            errors.append(f"Thiếu file chữ số cho {voice_label}: {', '.join(missing_digits)}.")
        for digit in sorted(REQUIRED_DIGITS & set(wav_files)):
            errors.extend(_validate_wav_file(wav_files[digit], f"chữ số {digit} ({voice_label})"))
    return errors

