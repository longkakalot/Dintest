import random
import re
import tempfile
from pathlib import Path

from pydub import AudioSegment

# ffmpeg
AudioSegment.converter = r"D:\ffmpeg\bin\ffmpeg.exe"

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

LOGO_FILE = BASE_DIR / "images" / "logo-transparent.png"

DIGITS_DIR = PROJECT_DIR / "digits_3regions"
NOISE_DIR = PROJECT_DIR / "noise"
NOISE_FILE = NOISE_DIR / "noise.wav"

TOTAL_TRIALS = 23
START_SNR = 0
STEP_SNR = 2
MIN_SNR = -20
MAX_SNR = 4

# Mức tín hiệu số an toàn hơn.
# Lưu ý: đây KHÔNG phải dB SPL thật ở tai người nghe.
TARGET_SPEECH_DBFS = -19.3529
MAX_OUTPUT_PEAK_DBFS = -6.0

VOICE_MAP = {
    "Giọng Miền Bắc": DIGITS_DIR / "Giọng Miền Bắc",
    "Giọng Miền Trung": DIGITS_DIR / "Giọng Miền Trung",
    "Giọng Miền Nam": DIGITS_DIR / "Giọng Miền Nam",
}


def _extract_digit_from_name(filename_stem: str):
    name = filename_stem.strip().lower()

    m = re.search(r"(?:^|[_\-\s])([0-9])(?:$|[_\-\s])", name)
    if m:
        return m.group(1)

    m = re.search(r"([0-9])$", name)
    if m:
        return m.group(1)

    m = re.search(r"([0-9])", name)
    if m:
        return m.group(1)

    return None


def list_digit_files(voice_label: str):
    folder = VOICE_MAP.get(voice_label)
    if folder is None or not folder.exists():
        return {}

    files = {}
    for f in sorted(folder.iterdir()):
        if not f.is_file():
            continue
        if f.suffix.lower() not in [".wav", ".mp3"]:
            continue

        digit = _extract_digit_from_name(f.stem)
        if digit is not None:
            files[digit] = str(f)

    return files


def get_voice_sample_playlist(voice_label: str, count: int = 3):
    files = list_digit_files(voice_label)
    playlist = []

    for d in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]:
        if d in files:
            playlist.append(files[d])
        if len(playlist) >= count:
            break

    return playlist


def generate_3_digits():
    # Không trùng nhau trong cùng một bộ 3 số
    return random.sample([str(i) for i in range(10)], 3)


def check_2_of_3(correct_digits, user_digits):
    """
    Quy tắc chấm DIN hiện dùng:
    - Đạt: đúng đủ 3/3 chữ số theo đúng thứ tự.
    - Không đạt: sai bất kỳ chữ số nào.
    """
    if len(user_digits) != 3:
        return False, 0

    correct_count = 0
    for i in range(3):
        if str(correct_digits[i]) == str(user_digits[i]):
            correct_count += 1

    return correct_count == 3, correct_count


def update_snr(current_snr, passed):
    """
    Đạt: giảm SNR 2 dB để khó hơn.
    Không đạt: tăng SNR 2 dB để dễ hơn.
    SNR phát chỉ nằm trong khoảng -20 đến +4 dB.
    """
    if passed:
        new_snr = current_snr - STEP_SNR
    else:
        new_snr = current_snr + STEP_SNR

    if new_snr > MAX_SNR:
        new_snr = MAX_SNR
    if new_snr < MIN_SNR:
        new_snr = MIN_SNR

    return new_snr


def get_reversal_points(snr_history):
    """
    Trả về danh sách các điểm đảo chiều trong khoảng lượt đo thứ 4 đến 23.
    Mỗi điểm gồm trial và snr.
    """
    reversals = []

    if len(snr_history) < 3:
        return reversals

    for i in range(1, len(snr_history) - 1):
        prev_snr = snr_history[i - 1]
        curr_snr = snr_history[i]
        next_snr = snr_history[i + 1]

        trial_number = i + 1

        is_reversal = (
            (curr_snr > prev_snr and curr_snr > next_snr) or
            (curr_snr < prev_snr and curr_snr < next_snr)
        )

        if is_reversal and 4 <= trial_number <= 23:
            reversals.append({
                "trial": trial_number,
                "snr": curr_snr,
            })

    return reversals


def calculate_final_snr(snr_history):
    """
    SRT = trung bình các điểm đảo chiều trong các lượt đo thứ 4 đến 23.
    """
    reversals = get_reversal_points(snr_history)

    if not reversals:
        return None

    values = [item["snr"] for item in reversals]
    return round(sum(values) / len(values), 2)


def normalize_audio(seg: AudioSegment, target_dbfs: float):
    if seg.dBFS == float("-inf"):
        return seg
    change = target_dbfs - seg.dBFS
    return seg.apply_gain(change)


def limit_peak(seg: AudioSegment, max_peak_dbfs: float = -6.0):
    peak = seg.max_dBFS
    if peak > max_peak_dbfs:
        seg = seg.apply_gain(max_peak_dbfs - peak)
    return seg


def build_digit_sequence_audio(voice_label: str, digits):
    """
    Khoảng lặng giữa các chữ số: 200 ms ± 50 ms
    """
    digit_files = list_digit_files(voice_label)
    clips = []
    used_files = []

    for d in digits:
        if d not in digit_files:
            raise FileNotFoundError(f"Không tìm thấy file số {d} trong giọng {voice_label}")

        file_path = digit_files[d]
        used_files.append(file_path)

        clip = AudioSegment.from_file(file_path)
        clip = clip.set_channels(1).set_frame_rate(44100)
        clip = normalize_audio(clip, TARGET_SPEECH_DBFS)
        clip = clip.fade_in(20).fade_out(20)
        clip = limit_peak(clip, MAX_OUTPUT_PEAK_DBFS)
        clips.append(clip)

    if len(clips) != 3:
        raise ValueError("Không tạo đủ 3 clip số cho lượt đo.")

    gap1 = AudioSegment.silent(duration=random.randint(220, 280))
    gap2 = AudioSegment.silent(duration=random.randint(220, 280))

    sequence = clips[0] + gap1 + clips[1] + gap2 + clips[2]
    sequence = limit_peak(sequence, MAX_OUTPUT_PEAK_DBFS)
    return sequence, used_files


def build_noise_for_length(duration_ms: int):
    if not NOISE_FILE.exists():
        raise FileNotFoundError(f"Không tìm thấy noise file: {NOISE_FILE}")

    noise = AudioSegment.from_file(NOISE_FILE)
    noise = noise.set_channels(1).set_frame_rate(44100)

    if len(noise) == 0:
        raise ValueError("Noise file rỗng.")

    repeated = AudioSegment.empty()
    while len(repeated) < duration_ms + 1000:
        repeated += noise

    return repeated[:duration_ms]


def mix_trial_audio(voice_label: str, digits, snr_db: float):
    """
    - Noise bắt đầu 500 ms trước chữ số đầu tiên
    - Noise kết thúc 500 ms sau chữ số cuối cùng

    Lưu ý:
    - Code chỉ khống chế mức tín hiệu số (dBFS), không bảo đảm dB SPL thật.
    """
    speech_core, used_files = build_digit_sequence_audio(voice_label, digits)

    pre_noise_ms = 500
    post_noise_ms = 500

    speech = (
        AudioSegment.silent(duration=pre_noise_ms)
        + speech_core
        + AudioSegment.silent(duration=post_noise_ms)
    )

    noise = build_noise_for_length(len(speech))

    # Giữ speech thấp hơn để an toàn đầu ra
    speech = normalize_audio(speech, TARGET_SPEECH_DBFS)

    # Noise thay đổi theo SNR
    noise_target_dbfs = TARGET_SPEECH_DBFS - snr_db
    noise = normalize_audio(noise, noise_target_dbfs)

    mixed = speech.overlay(noise)
    mixed = limit_peak(mixed, MAX_OUTPUT_PEAK_DBFS)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    mixed.export(tmp.name, format="wav")
    tmp.close()

    return tmp.name, used_files


def init_session_state(st):
    defaults = {
        "page": 1,
        "gender": "",
        "birth_year": None,
        "province": "",
        "health_conditions": [],
        "other_condition": "",
        "hearing_diagnosis": "Không rõ",
        "hearing_device": "Không",
        "headphone_confirmed": False,
        "voice": "Giọng Miền Bắc",
        "selected_voice": "Giọng Miền Bắc",
        "trial_index": 1,
        "current_snr": START_SNR,
        "snr_history": [],
        "current_digits": [],
        "typed_digits": "",
        "results": [],
        "final_snr": None,
        "trial_audio_path": None,
        "test_run_id": "",
        "trial1_started": False,
        "used_digit_files": [],
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_test_state(st):
    st.session_state["trial_index"] = 1
    st.session_state["current_snr"] = START_SNR
    st.session_state["snr_history"] = []
    st.session_state["current_digits"] = []
    st.session_state["typed_digits"] = ""
    st.session_state["results"] = []
    st.session_state["final_snr"] = None
    st.session_state["trial_audio_path"] = None
    st.session_state["trial1_started"] = False
    st.session_state["used_digit_files"] = []
