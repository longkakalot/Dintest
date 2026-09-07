import base64
import os
import time
import uuid
from datetime import date
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from core import (
    TOTAL_TRIALS,
    LOGO_FILE,
    get_voice_sample_playlist,
    generate_3_digits,
    check_2_of_3,
    update_snr,
    calculate_final_snr,
    get_reversal_points,
    reset_test_state,
    mix_trial_audio,
)


PROVINCES = [
    "An Giang", "Bắc Ninh", "Cà Mau", "Cao Bằng", "Cần Thơ", "Đà Nẵng",
    "Đắk Lắk", "Điện Biên", "Đồng Nai", "Đồng Tháp", "Gia Lai", "Hà Nội",
    "Hà Tĩnh", "Hải Phòng", "Huế", "Hưng Yên", "Khánh Hòa", "Lai Châu",
    "Lâm Đồng", "Lạng Sơn", "Lào Cai", "Nghệ An", "Ninh Bình", "Phú Thọ",
    "Quảng Ngãi", "Quảng Ninh", "Quảng Trị", "Sơn La", "Tây Ninh",
    "Thái Nguyên", "Thanh Hóa", "TP. Hồ Chí Minh", "Tuyên Quang", "Vĩnh Long",
]


def go_to(page_number: int):
    st.session_state.page = page_number
    st.rerun()


def render_stepbar(step):
    parts = []
    for number in range(1, 10):
        state = "active" if number == step else "done" if number < step else ""
        parts.append(f'<div class="din-step-node color-{number} {state}">{number}</div>')
        if number < 9:
            line_state = "done" if number < step else ""
            parts.append(f'<div class="din-step-line {line_state}"></div>')
    st.markdown(
        f'<div class="din-stepbar">{"".join(parts)}</div>',
        unsafe_allow_html=True,
    )


def add_digit(d):
    current = st.session_state.get("typed_digits", "")
    if len(current) < 3:
        st.session_state["typed_digits"] = current + str(d)


def backspace_digit():
    current = st.session_state.get("typed_digits", "")
    st.session_state["typed_digits"] = current[:-1]


def clear_digits():
    st.session_state["typed_digits"] = ""


def cleanup_old_trial_audio():
    old_path = st.session_state.get("trial_audio_path")
    if old_path and os.path.exists(old_path):
        try:
            os.remove(old_path)
        except Exception:
            pass
    st.session_state["trial_audio_path"] = None


def file_to_data_url(file_path):
    path = Path(file_path)
    if not path.exists():
        return None

    suffix = path.suffix.lower()
    mime = "audio/mpeg" if suffix == ".mp3" else "audio/wav"
    data = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime};base64,{data}"


def render_continuous_audio_player(audio_files):
    data_urls = []
    for file_path in audio_files:
        url = file_to_data_url(file_path)
        if url:
            data_urls.append(url)

    if not data_urls:
        st.error("Không đọc được file âm thanh để nghe thử.")
        return

    js_array = "[" + ",".join([f'"{u}"' for u in data_urls]) + "]"

    html = f"""
    <div style="max-width:760px;margin:0 auto;text-align:center;font-family:Arial,sans-serif;">
        <div style="margin:0 0 5px;font-size:14px;font-weight:600;line-height:1.3;">
            Bấm nút phát để nghe giọng đọc số liên tục, sau đó dùng hai biểu tượng loa để chỉnh mức nghe vừa tai.
        </div>

        <audio id="player"></audio>

        <div style="display:flex;align-items:center;justify-content:center;gap:10px;margin-top:4px;">
            <button onclick="decreaseVolume()" style="
                width:42px;height:42px;border:none;border-radius:50%;
                background:#e8f1ff;font-size:20px;cursor:pointer;">
                🔉
            </button>

            <button onclick="startPlayback()" style="
                min-width:140px;height:38px;border:none;border-radius:10px;
                background:#0b63ce;color:white;font-size:15px;font-weight:700;cursor:pointer;">
                Phát nghe thử
            </button>

            <button onclick="increaseVolume()" style="
                width:42px;height:42px;border:none;border-radius:50%;
                background:#e8f1ff;font-size:20px;cursor:pointer;">
                🔊
            </button>
        </div>

        <div id="volumeText" style="margin-top:3px;font-size:14px;font-weight:600;">
            Âm lượng hiện tại: 50%
        </div>
    </div>

    <script>
        const playlist = {js_array};
        const player = document.getElementById("player");
        const text = document.getElementById("volumeText");
        let currentIndex = 0;
        let started = false;

        player.volume = 0.5;

        function updateDisplay() {{
            const percent = Math.round(player.volume * 100);
            text.innerText = "Âm lượng hiện tại: " + percent + "%";
        }}

        function loadTrack(index) {{
            player.src = playlist[index];
            player.load();
        }}

        function startPlayback() {{
            if (playlist.length === 0) return;
            if (!started) {{
                started = true;
                currentIndex = 0;
                loadTrack(currentIndex);
            }}
            player.play();
            updateDisplay();
        }}

        function decreaseVolume() {{
            if (!started) startPlayback();
            player.volume = Math.max(0, player.volume - 0.05);
            updateDisplay();
        }}

        function increaseVolume() {{
            if (!started) startPlayback();
            player.volume = Math.min(1, player.volume + 0.05);
            updateDisplay();
        }}

        player.addEventListener("ended", function() {{
            if (playlist.length === 0) return;
            currentIndex = (currentIndex + 1) % playlist.length;
            loadTrack(currentIndex);
            player.play();
        }});

        updateDisplay();
    </script>
    """
    components.html(html, height=110)


def render_hidden_autoplay_audio(audio_path, trial_number, run_id):
    audio_url = file_to_data_url(audio_path)
    if not audio_url:
        st.error("Không đọc được file âm thanh lượt đo.")
        return

    play_key = f"din_{run_id}_trial_{trial_number}"

    html = f"""
    <audio id="trialAudio" preload="auto" style="display:none;">
        <source src="{audio_url}" type="audio/wav">
    </audio>

    <script>
        const audio = document.getElementById("trialAudio");
        const playKey = "{play_key}";

        function playOnce() {{
            if (sessionStorage.getItem(playKey) === "1") return;
            sessionStorage.setItem(playKey, "1");
            audio.currentTime = 0;
            audio.play().catch(() => {{}});
        }}

        if (sessionStorage.getItem(playKey) !== "1") {{
            setTimeout(playOnce, 150);
        }}
    </script>
    """
    components.html(html, height=1)


def page_1_intro():
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if LOGO_FILE.exists():
        with st.container(key="intro-logo"):
            st.image(str(LOGO_FILE), width=420)
    else:
        st.error(f"Không tìm thấy logo tại: {LOGO_FILE}")

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    with st.container(key="intro-action"):
        if st.button("Bắt đầu kiểm tra", type="primary", use_container_width=True):
            go_to(2)


def page_2_profile():
    render_stepbar(1)
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    gender_options = ["Chọn giới tính", "Nam", "Nữ"]
    current_gender = st.session_state.get("gender", "")
    gender_index = gender_options.index(current_gender) if current_gender in gender_options else 0
    gender = st.selectbox("Giới tính", gender_options, index=gender_index)

    current_year = st.session_state.get("birth_year")
    # DIN tự thực hiện phù hợp từ khoảng 6 tuổi, khi trẻ đã nhận biết và nhớ được bộ ba chữ số.
    year_options = ["Chọn năm sinh"] + list(range(date.today().year - 6, 1919, -1))
    year_index = year_options.index(current_year) if current_year in year_options else 0
    birth_year = st.selectbox("Năm sinh", year_options, index=year_index)

    province_options = ["Chọn tỉnh/thành phố"] + PROVINCES
    current_province = st.session_state.get("province", "")
    province_index = province_options.index(current_province) if current_province in province_options else 0
    province = st.selectbox("Nơi ở hiện tại", province_options, index=province_index)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        if st.button("Quay lại", use_container_width=True):
            go_to(1)
    with c2:
        if st.button("Tiếp tục", type="primary", use_container_width=True):
            if gender == gender_options[0] or birth_year == year_options[0] or province == province_options[0]:
                st.warning("Vui lòng chọn đầy đủ giới tính, năm sinh và nơi ở.")
            else:
                st.session_state["gender"] = gender
                st.session_state["birth_year"] = birth_year
                st.session_state["province"] = province
                go_to(3)


def page_3_health():
    st.markdown(
        """
        <style>
        .block-container{padding-top:.55rem !important;padding-bottom:.75rem !important;}
        .din-stepbar{margin-bottom:22px !important;padding-top:8px !important;padding-bottom:8px !important;}
        .din-simple-title{font-size:22px !important;margin:0 0 14px !important;}
        div[data-testid="stMultiSelect"]{margin-bottom:7px;}
        div[data-testid="stMultiSelect"] > label,
        div[data-testid="stTextInput"] > label{font-size:13px !important;}
        div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div,
        div[data-testid="stTextInput"] input{min-height:42px !important;}
        div[data-testid="stCaptionContainer"]{margin-top:5px;margin-bottom:10px;}
        @media(max-height:700px){
            .din-stepbar{transform:scale(.94);transform-origin:top center;margin-bottom:16px !important;}
            .din-simple-title{font-size:20px !important;margin-bottom:10px !important;}
            .stButton > button{min-height:40px !important;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    render_stepbar(2)
    st.markdown('<div class="din-simple-title">Tình trạng sức khỏe</div>', unsafe_allow_html=True)

    condition_options = [
        "Không có bệnh lý kèm theo",
        "Tăng huyết áp hoặc bệnh tim mạch",
        "Đái tháo đường",
        "Bệnh thận mạn",
        "Bệnh tuyến giáp hoặc nội tiết",
        "Bệnh thần kinh",
        "Bệnh tự miễn",
        "Ung thư hoặc từng hóa trị/xạ trị",
        "Viêm tai giữa hoặc bệnh tai mạn tính",
        "Đã từng chấn thương vùng đầu/tai",
        "Đang hoặc từng dùng thuốc có nguy cơ ảnh hưởng sức nghe",
        "Bệnh lý khác",
        "Không rõ/không muốn cung cấp",
    ]

    selected = st.multiselect(
        "Bệnh lý hiện tại (có thể chọn một hoặc nhiều bệnh)",
        condition_options,
        default=[item for item in st.session_state.get("health_conditions", []) if item in condition_options],
        placeholder="Chạm để chọn một hoặc nhiều mục",
    )

    other_condition = st.session_state.get("other_condition", "")
    if "Bệnh lý khác" in selected:
        other_condition = st.text_input(
            "Nhập bệnh lý khác",
            value=other_condition,
            placeholder="Vui lòng nhập tên bệnh lý",
        )

    st.caption("Thông tin này không được dùng để chẩn đoán bệnh.")
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        if st.button("Quay lại", use_container_width=True):
            go_to(2)
    with c2:
        if st.button("Tiếp tục", type="primary", use_container_width=True):
            exclusive = {"Không có bệnh lý kèm theo", "Không rõ/không muốn cung cấp"}
            if not selected:
                st.warning("Vui lòng chọn ít nhất một mục về tình trạng sức khỏe.")
            elif len(selected) > 1 and any(item in selected for item in exclusive):
                st.warning("Mục “Không có bệnh lý” hoặc “Không rõ” không thể chọn cùng các bệnh lý khác.")
            elif "Bệnh lý khác" in selected and not other_condition.strip():
                st.warning("Vui lòng nhập tên bệnh lý khác.")
            else:
                st.session_state["health_conditions"] = selected
                st.session_state["other_condition"] = other_condition if "Bệnh lý khác" in selected else ""
                go_to(4)


def page_2_environment():
    render_stepbar(3)
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div style="
            text-align:center;
            font-size:22px;
            line-height:1.55;
            font-weight:650;
            max-width:900px;
            margin:0 auto 6px auto;
            color:#1f2937;">
            Nên thực hiện đo trong môi trường<br>
            càng yên tĩnh càng tốt.
        </div>
        """,
        unsafe_allow_html=True
    )

    gauge_html = """
    <style>
        html,body{margin:0;padding:0;background:transparent !important;overflow:visible;}
        *{box-sizing:border-box;font-family:'Segoe UI',Tahoma,Arial,sans-serif !important;}
        button{font-family:'Segoe UI',Tahoma,Arial,sans-serif !important;line-height:1.35;}
    </style>
    <div style="
        width:100%;
        max-width:330px;
        margin:0 auto;
        text-align:center;
        font-family:'Segoe UI',Tahoma,Arial,sans-serif;
        background:transparent;
        border:none;
        border-radius:24px;
        box-shadow:none;
        padding:2px 10px 2px;
        box-sizing:border-box;
    ">
        <div style="font-size:12px;font-weight:800;letter-spacing:.1em;color:#6b879d;text-transform:uppercase;">
            Đo nhanh môi trường
        </div>
        <canvas id="gauge" width="330" height="180"
            style="width:100%;max-width:260px;height:auto;display:block;margin:-4px auto 0;
            background:radial-gradient(circle at 50% 72%,rgba(45,139,204,.13),transparent 45%);">
        </canvas>

        <div id="dbValue" style="
            font-size:32px;
            font-weight:900;
            color:#64748b;
            line-height:1;
            margin-top:-22px;">
            -- dB
        </div>

        <div id="status" style="
            display:inline-block;
            font-size:14px;
            font-weight:800;
            color:#64748b;
            background:#eef4f8;
            border-radius:999px;
            padding:5px 10px;
            margin-top:5px;">
            Nhấn để kiểm tra tiếng ồn
        </div>

        <button id="startBtn" style="
            width:100%;
            margin-top:7px;
            background:linear-gradient(135deg,#075fb8,#0c86d3);
            color:white;
            border:none;
            border-radius:14px;
            padding:9px 15px;
            font-size:15px;
            font-weight:800;
            cursor:pointer;
            box-shadow:0 8px 18px rgba(11,99,206,0.22);">
            <span style="display:inline-flex;align-items:center;justify-content:center;gap:8px;">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <rect x="9" y="3" width="6" height="11" rx="3" fill="white"/>
                    <path d="M6.5 11.5a5.5 5.5 0 0 0 11 0M12 17v4M9 21h6" stroke="white" stroke-width="2" stroke-linecap="round"/>
                </svg>
                Kiểm tra tiếng ồn
            </span>
        </button>

        <div style="
            margin-top:3px;
            font-size:11px;
            color:#748596;
            line-height:1.35;">
            Kết quả chỉ mang tính tham khảo, không thay thế thiết bị đo chuyên dụng.
        </div>
    </div>

    <script>
    const canvas = document.getElementById("gauge");
    const ctx = canvas.getContext("2d");
    const dbText = document.getElementById("dbValue");
    const status = document.getElementById("status");
    const btn = document.getElementById("startBtn");

    let analyser, dataArray, audioContext;
    let smoothDb = 35;
    let running = false;
    const OFFSET = 88;

    function clamp(v, min, max){
        return Math.max(min, Math.min(max, v));
    }

    function draw(db){
        ctx.clearRect(0, 0, 330, 180);

        const cx = 165;
        const cy = 145;
        const rOuter = 101;
        const rLabel = 72;

        function arc(from, to, color, width){
            ctx.beginPath();
            ctx.arc(cx, cy, rOuter, Math.PI + (from / 80) * Math.PI, Math.PI + (to / 80) * Math.PI);
            ctx.strokeStyle = color;
            ctx.lineWidth = width;
            ctx.lineCap = "round";
            ctx.stroke();
        }

        ctx.save();
        ctx.shadowColor = "rgba(25,56,78,.22)";
        ctx.shadowBlur = 12;
        ctx.shadowOffsetY = 7;
        arc(0, 80, "#e5edf3", 18);
        ctx.restore();

        arc(0, 34, "#36b978", 14);
        arc(36, 49, "#f2b83f", 14);
        arc(51, 80, "#ed6570", 14);

        ctx.save();
        ctx.globalAlpha = .48;
        arc(1, 33, "#8be0b2", 4);
        arc(37, 48, "#ffe49a", 4);
        arc(52, 79, "#ffadb3", 4);
        ctx.restore();

        const safeA = Math.PI + (35 / 80) * Math.PI;
        ctx.beginPath();
        ctx.moveTo(cx + (rOuter - 12) * Math.cos(safeA), cy + (rOuter - 12) * Math.sin(safeA));
        ctx.lineTo(cx + (rOuter + 9) * Math.cos(safeA), cy + (rOuter + 9) * Math.sin(safeA));
        ctx.lineWidth = 3;
        ctx.strokeStyle = "#0b63ce";
        ctx.lineCap = "round";
        ctx.stroke();

        const labels = [
            {v: 0, text: "0"},
            {v: 35, text: "35"},
            {v: 50, text: "50"},
            {v: 80, text: "80"}
        ];

        labels.forEach(item => {
            const a = Math.PI + (item.v / 80) * Math.PI;
            const tx = cx + rLabel * Math.cos(a);
            const ty = cy + rLabel * Math.sin(a);
            ctx.font = "bold 12px Arial";
            ctx.fillStyle = item.v === 35 ? "#0b63ce" : "#475569";
            ctx.textAlign = "center";
            ctx.fillText(item.text, tx, ty + 4);
        });

        ctx.font = "bold 13px Arial";
        ctx.fillStyle = "#64748b";
        ctx.textAlign = "center";
        ctx.fillText("dB", cx, 34);

        const val = clamp(db, 0, 80);
        const a = Math.PI + (val / 80) * Math.PI;
        const nx = cx + 70 * Math.cos(a);
        const ny = cy + 70 * Math.sin(a);

        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(nx, ny);
        ctx.lineWidth = 6;
        const needleGradient = ctx.createLinearGradient(cx, cy, nx, ny);
        needleGradient.addColorStop(0, "#071e31");
        needleGradient.addColorStop(1, "#39779e");
        ctx.strokeStyle = needleGradient;
        ctx.lineCap = "round";
        ctx.shadowColor = "rgba(15,50,75,.25)";
        ctx.shadowBlur = 6;
        ctx.stroke();
        ctx.shadowBlur = 0;

        const hub = ctx.createRadialGradient(cx - 4, cy - 5, 2, cx, cy, 15);
        hub.addColorStop(0, "#ffffff");
        hub.addColorStop(.2, "#8fb8d1");
        hub.addColorStop(.45, "#284f69");
        hub.addColorStop(1, "#071e31");
        ctx.beginPath();
        ctx.arc(cx, cy, 15, 0, 2 * Math.PI);
        ctx.fillStyle = hub;
        ctx.shadowColor = "rgba(5,25,40,.35)";
        ctx.shadowBlur = 9;
        ctx.shadowOffsetY = 4;
        ctx.fill();
        ctx.shadowBlur = 0;
        ctx.shadowOffsetY = 0;

        ctx.beginPath();
        ctx.arc(cx - 3, cy - 4, 4, 0, 2 * Math.PI);
        ctx.fillStyle = "rgba(255,255,255,.88)";
        ctx.fill();
    }

    function loop(){
        if(!running || !analyser) return;

        analyser.getByteTimeDomainData(dataArray);

        let sum = 0;
        for(let i = 0; i < dataArray.length; i++){
            let v = (dataArray[i] - 128) / 128;
            sum += v * v;
        }

        let rms = Math.sqrt(sum / dataArray.length);
        let db = 20 * Math.log10(rms + 0.00001) + OFFSET;

        db = clamp(db, 25, 80);
        smoothDb += (db - smoothDb) * 0.15;

        const val = Math.round(smoothDb);
        dbText.innerText = val + " dB";
        draw(smoothDb);

        if(val <= 35){
            dbText.style.color = "#16a34a";
            status.style.color = "#16a34a";
            status.style.background = "#eaf9f0";
            status.innerText = "Môi trường yên tĩnh";
        }else if(val <= 50){
            dbText.style.color = "#d97706";
            status.style.color = "#d97706";
            status.style.background = "#fff7df";
            status.innerText = "Có tiếng ồn nhẹ";
        }else{
            dbText.style.color = "#dc2626";
            status.style.color = "#dc2626";
            status.style.background = "#fff0f1";
            status.innerText = "Tiếng ồn cao";
        }

        requestAnimationFrame(loop);
    }

    btn.onclick = async function(){
        if(running) return;

        try{
            audioContext = new (window.AudioContext || window.webkitAudioContext)();

            let stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: false,
                    noiseSuppression: false,
                    autoGainControl: false
                }
            });

            let mic = audioContext.createMediaStreamSource(stream);
            analyser = audioContext.createAnalyser();
            analyser.fftSize = 2048;
            dataArray = new Uint8Array(analyser.fftSize);
            mic.connect(analyser);

            running = true;
            btn.innerText = "Đang đo...";
            btn.style.background = "#16a34a";
            loop();

        }catch(e){
            status.style.color = "#dc2626";
            status.innerText = "Không truy cập được micro";
        }
    };

    draw(35);
    </script>
    """

    components.html(gauge_html, height=285)

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        if st.button("Quay lại", use_container_width=True):
            go_to(3)
    with c2:
        if st.button("Tiếp tục", use_container_width=True):
            go_to(5)


def page_3_headphone_confirm():
    render_stepbar(4)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    checked = st.checkbox(
        "Đã đeo tai nghe",
        value=st.session_state.get("headphone_confirmed", False)
    )
    st.session_state["headphone_confirmed"] = checked

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        if st.button("Quay lại", use_container_width=True):
            go_to(4)
    with c2:
        if st.button("Xác nhận", use_container_width=True):
            if checked:
                go_to(6)
            else:
                st.warning("Vui lòng xác nhận đã đeo tai nghe.")


def page_4_volume_setup():
    render_stepbar(5)
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class="din-volume-instruction" style="
            text-align:center;
            font-weight:600;
            max-width:980px;
            margin:0 auto 8px auto;">
            Đặt âm lượng thiết bị khoảng 50–60% mức tối đa trước khi bắt đầu đo. Để âm lượng ở mức vừa đủ nghe, không nên mở quá to, giữ nguyên mức âm lượng này trong suốt quá trình thực hiện đo.
        </div>
        """,
        unsafe_allow_html=True
    )

    voice = st.session_state.get("selected_voice", "Giọng Miền Bắc")
    playlist = get_voice_sample_playlist(voice, count=3)

    if playlist:
        render_continuous_audio_player(playlist)
    else:
        st.error(f"Không tìm thấy file âm thanh thử cho {voice}")

    st.markdown(
        """
        <div class="din-volume-note" style="max-width:720px;margin:-5px auto 7px;padding:8px 12px;border-radius:12px;
        background:#fff7e7;border:1px solid #f3d18a;color:#7a5210;text-align:center;">
            <strong>Lưu ý:</strong> Nếu đã chỉnh âm lượng thiết bị lên mức tối đa nhưng vẫn không nghe rõ,
            có thể bạn đang gặp vấn đề về nghe. Bạn nên thực hiện kiểm tra sức nghe tại cơ sở chuyên khoa.
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        if st.button("Quay lại", use_container_width=True):
            go_to(5)
    with c2:
        if st.button("Tiếp tục", use_container_width=True):
            go_to(7)


def page_5_choose_voice():
    render_stepbar(6)
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    voice = st.radio(
        "Chọn giọng đọc",
        ["Giọng Miền Bắc", "Giọng Miền Trung", "Giọng Miền Nam"],
        index=["Giọng Miền Bắc", "Giọng Miền Trung", "Giọng Miền Nam"].index(
            st.session_state.get("selected_voice", "Giọng Miền Bắc")
        ),
        label_visibility="collapsed",
    )
    st.session_state["selected_voice"] = voice

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        if st.button("Quay lại", use_container_width=True):
            go_to(6)
    with c2:
        if st.button("Tiếp tục", use_container_width=True):
            cleanup_old_trial_audio()
            reset_test_state(st)
            st.session_state["voice"] = voice
            st.session_state["selected_voice"] = voice
            st.session_state["test_run_id"] = uuid.uuid4().hex
            st.session_state["trial1_started"] = False
            go_to(8)


def page_6_instruction():
    render_stepbar(7)
    # Tăng khoảng cách phía trên để không bị mất dòng hướng dẫn
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="din-test-instruction" style="
            max-width:900px;
            margin:0 auto;
            text-align:center;
            font-weight:600;">
            Hệ thống sẽ đọc các số từ 0–9, bạn nghe và bấm vào các phím số tương ứng. Sau khi nhập xong, bấm vào nút "Kế tiếp" để tiếp tục kiểm tra.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    demo_html = """
    <div style="display:flex;justify-content:center;">
        <div style="position:relative;width:280px;">

            <div class="din-keypad-display" style="
                border:1.2px solid #d9e2f1;
                border-radius:8px;
                height:30px;
                display:flex;
                align-items:center;
                justify-content:center;
                font-size:17px;
                font-weight:700;
                color:#0b63ce;
                background:#f8fbff;
                margin-bottom:4px;">
                <span id="typedDemo">&nbsp;</span>
            </div>

            <div class="grid">
                <div class="key" id="k1">1</div>
                <div class="key" id="k2">2</div>
                <div class="key" id="k3">3</div>
                <div class="key" id="k4">4</div>
                <div class="key" id="k5">5</div>
                <div class="key" id="k6">6</div>
                <div class="key" id="k7">7</div>
                <div class="key" id="k8">8</div>
                <div class="key" id="k9">9</div>
                <div class="key small" id="kxoa">Xóa</div>
                <div class="key" id="k0">0</div>
                <div class="key small" id="kback">←</div>
            </div>

            <div class="real-buttons">
                <div class="demoBtn">Quay lại</div>
                <div class="demoBtn" id="nextBtn">Kế tiếp</div>
            </div>

            <div id="finger">👆</div>
        </div>
    </div>

    <style>
        html,body{
            margin:0;
            padding:0;
            overflow:hidden;
            background:transparent;
        }

        .grid{
            display:grid;
            grid-template-columns:repeat(3, 1fr);
            gap:4px;
        }

        .key{
            height:26px;
            border-radius:8px;
            background:white;
            border:1px solid #d9e2f1;
            color:#1f2937;
            display:flex;
            align-items:center;
            justify-content:center;
            font-size:14px;
            font-weight:600;
            box-shadow:0 1px 3px rgba(0,0,0,0.08);
        }

        .key.small{
            font-size:13px;
            color:#334155;
        }

        .key.active{
            background:#dbeafe;
            border:2px solid #0b63ce;
            color:#0b63ce;
            transform:scale(0.96);
        }

        .real-buttons{
            display:grid;
            grid-template-columns:1fr 1fr;
            gap:24px;
            margin-top:6px;
        }

        .demoBtn{
            height:28px;
            border-radius:8px;
            background:white;
            border:1px solid #d9e2f1;
            color:#1f2937;
            display:flex;
            align-items:center;
            justify-content:center;
            font-size:13px;
            font-weight:600;
            box-shadow:0 1px 3px rgba(0,0,0,0.08);
        }

        .demoBtn.active{
            background:#dbeafe;
            border:2px solid #0b63ce;
            color:#0b63ce;
            transform:scale(0.96);
        }

        #finger{
            position:absolute;
            font-size:32px;
            left:115px;
            top:42px;
            transition:all 0.55s ease-in-out;
            z-index:10;
            transform:rotate(-18deg);
            pointer-events:none;
        }
    </style>

    <script>
        const typedDemo = document.getElementById("typedDemo");
        const finger = document.getElementById("finger");

        const steps = [
            {key:"k2", text:"2", x:115, y:42},
            {key:"k5", text:"2  5", x:115, y:72},
            {key:"k9", text:"2  5  9", x:207, y:102},
            {key:"nextBtn", text:"2  5  9", x:190, y:150}
        ];

        let index = 0;

        function clearActive(){
            document.querySelectorAll(".key").forEach(k => k.classList.remove("active"));
            document.querySelectorAll(".demoBtn").forEach(k => k.classList.remove("active"));
        }

        function runDemo(){
            clearActive();

            const step = steps[index];

            finger.style.left = step.x + "px";
            finger.style.top = step.y + "px";
            typedDemo.innerText = step.text;

            const el = document.getElementById(step.key);
            el.classList.add("active");

            index++;

            if(index >= steps.length){
                setTimeout(() => {
                    clearActive();
                    typedDemo.innerHTML = "&nbsp;";
                    index = 0;
                    runDemo();
                }, 800);
            }else{
                setTimeout(runDemo, 800);
            }
        }

        setTimeout(runDemo, 400);
    </script>
    """

    components.html(demo_html, height=200)

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        if st.button("Quay lại", use_container_width=True):
            go_to(7)
    with c2:
        if st.button("Bắt đầu lượt đo", use_container_width=True):
            st.session_state["trial1_started"] = False
            go_to(9)


def ensure_trial_generated():
    if not st.session_state.get("current_digits"):
        st.session_state["current_digits"] = generate_3_digits()
        st.session_state["typed_digits"] = ""

        cleanup_old_trial_audio()

        voice_to_use = st.session_state.get(
            "selected_voice",
            st.session_state.get("voice", "Giọng Miền Bắc")
        )
        st.session_state["voice"] = voice_to_use

        result = mix_trial_audio(
            voice_to_use,
            st.session_state["current_digits"],
            st.session_state["current_snr"]
        )

        if isinstance(result, tuple):
            audio_path = result[0]
            used_files = result[1] if len(result) > 1 else []
        else:
            audio_path = result
            used_files = []

        st.session_state["trial_audio_path"] = audio_path
        st.session_state["used_digit_files"] = used_files


def render_keypad():
    typed = st.session_state.get("typed_digits", "")
    display_value = "  ".join(list(typed)) if typed else ""

    with st.container(key="keypad-wrap"):
        progress_percent = int((st.session_state["trial_index"] / TOTAL_TRIALS) * 100)
        st.progress(progress_percent, text=f"Lượt {st.session_state['trial_index']} / {TOTAL_TRIALS}")

        st.markdown("<div style='height:1px'></div>", unsafe_allow_html=True)

        st.markdown(
            f"""
            <div class="din-keypad-display" style="
                border:1.2px solid #d9e2f1;
                border-radius:8px;
                height:38px;
                display:flex;
                align-items:center;
                justify-content:center;
                font-size:20px;
                font-weight:700;
                color:#0b63ce;
                background:#f8fbff;
                margin-bottom:6px;">
                {display_value if display_value else "&nbsp;"}
            </div>
            """,
            unsafe_allow_html=True
        )

        rows = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
            ["Xóa", "0", "←"],
        ]

        for row in rows:
            cols = st.columns(3, gap="small")
            for i, key in enumerate(row):
                with cols[i]:
                    if st.button(key, use_container_width=True):
                        if key.isdigit():
                            add_digit(key)
                        elif key == "Xóa":
                            backspace_digit()
                        elif key == "←":
                            clear_digits()
                        st.rerun()


def page_7_main_test():
    ensure_trial_generated()

    trial = st.session_state["trial_index"]
    snr = st.session_state["current_snr"]
    digits = st.session_state["current_digits"]
    audio_path = st.session_state.get("trial_audio_path")
    run_id = st.session_state.get("test_run_id", "default_run")

    render_stepbar(8)

    st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)

    if trial == 1 and not st.session_state.get("trial1_started", False):
        overlay = st.empty()
        countdown_colors = {
            5: ("#2468d8", "#76c7ff"),
            4: ("#7048c8", "#c39cff"),
            3: ("#079f91", "#64e5d2"),
            2: ("#e09118", "#ffd66a"),
            1: ("#db3d64", "#ff91aa"),
        }

        for sec in [5, 4, 3, 2, 1]:
            deep_color, light_color = countdown_colors[sec]
            overlay.markdown(
                f"""
                <style>
                    @keyframes countEnter {{
                        0% {{opacity:0;transform:translateY(20px) scale(.72);filter:blur(7px);}}
                        55% {{opacity:1;transform:translateY(-5px) scale(1.07);filter:blur(0);}}
                        100% {{opacity:1;transform:translateY(0) scale(1);}}
                    }}
                    .din-count-number {{
                        font-family:'Segoe UI',Arial,sans-serif;
                        font-size:clamp(118px,22vw,180px);
                        font-weight:1000;
                        line-height:.9;
                        letter-spacing:-.08em;
                        padding-right:.08em;
                        color:{light_color};
                        background:linear-gradient(155deg,#ffffff 0%,{light_color} 22%,{deep_color} 64%,#082a50 115%);
                        -webkit-background-clip:text;
                        background-clip:text;
                        -webkit-text-fill-color:transparent;
                        filter:drop-shadow(0 16px 13px {deep_color}4d);
                        text-shadow:
                            1px 1px 0 {deep_color},
                            2px 2px 0 {deep_color},
                            3px 3px 0 {deep_color},
                            4px 4px 0 {deep_color},
                            5px 5px 0 {deep_color},
                            8px 12px 18px {deep_color}66;
                        animation:countEnter .42s cubic-bezier(.2,.8,.2,1) both;
                    }}
                </style>
                <div style="
                    position:fixed;
                    z-index:999999;
                    inset:0;
                    background:
                        linear-gradient(125deg,{light_color}15 0%,transparent 34%),
                        linear-gradient(305deg,{deep_color}12 0%,transparent 38%),
                        linear-gradient(160deg,#f8fcff,#eef6fc);
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    flex-direction:column;">
                    <div class="din-count-number">
                        {sec}
                    </div>
                    <div style="
                        margin-top:25px;
                        font-size:20px;
                        font-weight:800;
                        color:#334155;">
                        Chuẩn bị nghe
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            time.sleep(1)

        overlay.empty()
        st.session_state["trial1_started"] = True
        st.rerun()

    if audio_path and os.path.exists(audio_path):
        render_hidden_autoplay_audio(audio_path, trial_number=trial, run_id=run_id)
    else:
        st.error("Không tạo được file âm thanh của lượt đo.")

    st.markdown("<div style='height:1px'></div>", unsafe_allow_html=True)
    render_keypad()
    st.markdown("<div style='height:1px'></div>", unsafe_allow_html=True)

    with st.container(key="test-nav"):
        c1, c2 = st.columns(2, gap="medium")

        with c1:
            if st.button("Quay lại", use_container_width=True):
                cleanup_old_trial_audio()
                go_to(8)

        with c2:
            if st.button("Kế tiếp", use_container_width=True):
                typed = st.session_state.get("typed_digits", "")
                if len(typed) != 3:
                    st.warning("Vui lòng nhập đủ 3 số.")
                    return

                user_digits = list(typed)
                passed, correct_count = check_2_of_3(digits, user_digits)

                st.session_state["snr_history"].append(snr)
                st.session_state["results"].append({
                    "trial": trial,
                    "target": "".join(digits),
                    "answer": "".join(user_digits),
                    "correct_count": correct_count,
                    "passed": passed,
                    "snr": snr,
                })

                st.session_state["current_snr"] = update_snr(snr, passed)

                cleanup_old_trial_audio()

                if trial >= TOTAL_TRIALS:
                    st.session_state["final_snr"] = calculate_final_snr(st.session_state["snr_history"])
                    st.session_state["page"] = 10
                    st.session_state["current_digits"] = []
                    st.session_state["typed_digits"] = ""
                    st.rerun()
                else:
                    st.session_state["trial_index"] = trial + 1
                    st.session_state["current_digits"] = []
                    st.session_state["typed_digits"] = ""
                    st.rerun()



def page_8_result():
    render_stepbar(9)
    st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class="din-card" style="margin-bottom:14px;">
            <div class="din-kicker">Hoàn thành bài đo</div>
            <div class="din-title">Kết quả sàng lọc</div>
            <div class="din-subtitle" style="margin-bottom:0;">Điểm đo của bạn được hiển thị bên dưới.</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    final_snr = st.session_state.get("final_snr", None)

    if final_snr is None:
        st.warning(
            "Không đủ điểm đảo chiều để tính kết quả SRT. Có thể bạn thực hiện chưa đúng hoặc đang gặp "
            "vấn đề về nghe. Bạn cần đến Bệnh viện Tai Mũi Họng TP.HCM để kiểm tra và đánh giá sức nghe."
        )
    else:
        st.markdown(
            f"""
            <div style="
                text-align:center;
                margin:8px auto 16px auto;
                max-width:370px;
                width:100%;
                padding:13px 12px;
                box-sizing:border-box;
                border-radius:18px;
                color:white;
                background:linear-gradient(135deg,#075fb8,#0b86d4);
                box-shadow:0 12px 28px rgba(7,95,184,.22);">
                <div style="font-size:13px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;opacity:.85;">
                    Điểm của bài đo
                </div>
                <div style="font-size:32px;line-height:1.15;font-weight:900;margin:4px 0 1px;">
                    {final_snr}
                </div>
                <div style="font-size:16px;font-weight:750;opacity:.92;">dB SNR (SRT)</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if final_snr <= -13.11:
            result_color = "#166534"
            result_bg = "#f0fdf4"
            result_border = "#86efac"
            result_icon = "🟢"
            result_title = "Ít gặp khó khăn khi nghe hiểu lời nói trong môi trường có tiếng ồn"
            result_note = (
                "Đây là kết quả đo sàng lọc sức nghe bằng đo thính lực lời (chữ số) trong tiếng ồn.\n\n"
                "Kết quả này không thay thế đo thính lực đơn âm, đặc biệt trong các trường hợp nghe kém một bên "
                "hoặc bệnh lý tai giữa như viêm tai giữa, xốp xơ tai...\n\n"
                "Nếu bạn vẫn nghi ngờ mình gặp khó khăn khi nghe, nên đến kiểm tra tầm soát sức nghe tại "
                "Bệnh viện Tai Mũi Họng TP.HCM."
            )
        elif final_snr <= -12.02:
            result_color = "#92400e"
            result_bg = "#fffbeb"
            result_border = "#fde68a"
            result_icon = "🟡"
            result_title = "Có thể gặp khó khăn khi nghe hiểu lời nói trong môi trường có tiếng ồn"
            result_note = "Nên kiểm tra tầm soát sức nghe tại Bệnh viện Tai Mũi Họng TP.HCM."
        else:
            result_color = "#991b1b"
            result_bg = "#fef2f2"
            result_border = "#fecaca"
            result_icon = "🔴"
            result_title = "Gặp khó khăn khi nghe hiểu lời nói trong môi trường có tiếng ồn"
            result_note = "Cần phải đo thính lực tại Bệnh viện Tai Mũi Họng TP.HCM."

        safe_note = result_note.replace("\n", "<br>")
        st.markdown(
            f"""
            <div style="
                max-width:720px;
                width:100%;
                box-sizing:border-box;
                margin:12px auto 0 auto;
                padding:18px 16px;
                border-radius:14px;
                border:1.5px solid {result_border};
                background:{result_bg};
                text-align:center;
                overflow-x:hidden;
                overflow-wrap:break-word;
                word-wrap:break-word;
                word-break:normal;
                white-space:normal;">
                <div style="font-size:34px; line-height:1; margin-bottom:10px;">
                    {result_icon}
                </div>
                <div style="
                    color:{result_color};
                    font-size:22px;
                    line-height:1.45;
                    font-weight:800;
                    margin-bottom:12px;
                    overflow-wrap:break-word;
                    word-break:normal;
                    white-space:normal;">
                    {result_title}
                </div>
                <div style="
                    color:#1f2937;
                    font-size:17px;
                    line-height:1.6;
                    font-weight:600;
                    overflow-wrap:break-word;
                    word-break:normal;
                    white-space:normal;">
                    {safe_note}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    with st.container(key="result-action"):
        if st.button("Đo lại", use_container_width=True):
            cleanup_old_trial_audio()
            reset_test_state(st)
            st.session_state["test_run_id"] = uuid.uuid4().hex
            st.session_state["trial1_started"] = False
            go_to(1)
