import base64
import os
import time
import uuid
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


def go_to(page_number: int):
    st.session_state.page = page_number
    st.rerun()


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
    <div style="max-width:760px;margin:0 auto;text-align:center;">
        <div style="margin-top:8px;margin-bottom:14px;font-size:17px;font-weight:600;line-height:1.5;">
            Bấm nút phát để nghe giọng đọc số liên tục, sau đó dùng hai biểu tượng loa để chỉnh mức nghe vừa tai.
        </div>

        <audio id="player"></audio>

        <div style="display:flex;align-items:center;justify-content:center;gap:12px;margin-top:10px;">
            <button onclick="decreaseVolume()" style="
                width:54px;height:54px;border:none;border-radius:50%;
                background:#e8f1ff;font-size:24px;cursor:pointer;">
                🔉
            </button>

            <button onclick="startPlayback()" style="
                min-width:140px;height:40px;border:none;border-radius:10px;
                background:#0b63ce;color:white;font-size:16px;font-weight:700;cursor:pointer;">
                Phát nghe thử
            </button>

            <button onclick="increaseVolume()" style="
                width:54px;height:54px;border:none;border-radius:50%;
                background:#e8f1ff;font-size:24px;cursor:pointer;">
                🔊
            </button>
        </div>

        <div id="volumeText" style="margin-top:10px;font-size:16px;font-weight:600;">
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
    components.html(html, height=200)


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
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    if LOGO_FILE.exists():
        c1, c2, c3 = st.columns([1, 3, 1])
        with c2:
            st.image(str(LOGO_FILE), width=620)
    else:
        st.error(f"Không tìm thấy logo tại: {LOGO_FILE}")

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1.4, 1.2, 1.4])
    with c2:
        if st.button("Bắt đầu", use_container_width=True):
            go_to(2)


def page_2_environment():
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

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
    <div style="
        width:100%;
        max-width:360px;
        margin:0 auto;
        text-align:center;
        font-family:Arial, sans-serif;
        background:transparent;
        padding:0 8px 4px 8px;
        box-sizing:border-box;
    ">
        <canvas id="gauge" width="330" height="180"
            style="width:100%;max-width:330px;height:auto;display:block;margin:0 auto;background:transparent;">
        </canvas>

        <div id="dbValue" style="
            font-size:32px;
            font-weight:900;
            color:#64748b;
            margin-top:-22px;">
            -- dB
        </div>

        <div id="status" style="
            font-size:15px;
            font-weight:700;
            color:#64748b;
            margin-top:0;">
            Nhấn để kiểm tra tiếng ồn
        </div>

        <button id="startBtn" style="
            margin-top:8px;
            background:#0b63ce;
            color:white;
            border:none;
            border-radius:12px;
            padding:9px 18px;
            font-size:15px;
            font-weight:800;
            cursor:pointer;
            box-shadow:0 4px 10px rgba(11,99,206,0.22);">
            🎤 Kiểm tra tiếng ồn
        </button>

        <div style="
            margin-top:6px;
            font-size:12px;
            color:#777;
            line-height:1.3;">
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
        const rOuter = 98;
        const rLabel = 72;

        for(let i = 0; i <= 80; i += 2){
            const a = Math.PI + (i / 80) * Math.PI;
            const x = cx + rOuter * Math.cos(a);
            const y = cy + rOuter * Math.sin(a);

            let col = "#22c55e";
            if(i > 35) col = "#facc15";
            if(i > 50) col = "#ef4444";

            ctx.beginPath();
            ctx.arc(x, y, i % 10 === 0 ? 4.4 : 3.0, 0, 2 * Math.PI);
            ctx.fillStyle = col;
            ctx.fill();
        }

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
        ctx.lineWidth = 5;
        ctx.strokeStyle = "#0f172a";
        ctx.lineCap = "round";
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(cx, cy, 13, 0, 2 * Math.PI);
        ctx.fillStyle = "#0f172a";
        ctx.fill();

        ctx.beginPath();
        ctx.arc(cx, cy, 5, 0, 2 * Math.PI);
        ctx.fillStyle = "#ffffff";
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
            status.innerText = "Môi trường yên tĩnh";
        }else if(val <= 50){
            dbText.style.color = "#d97706";
            status.style.color = "#d97706";
            status.innerText = "Có tiếng ồn nhẹ";
        }else{
            dbText.style.color = "#dc2626";
            status.style.color = "#dc2626";
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

    components.html(gauge_html, height=300)

    c1, c2, c3 = st.columns([1.2, 0.4, 1.2])
    with c1:
        if st.button("Quay lại", use_container_width=True):
            go_to(1)
    with c3:
        if st.button("Tiếp tục", use_container_width=True):
            go_to(3)


def page_3_headphone_confirm():
    st.markdown("<div style='height:120px'></div>", unsafe_allow_html=True)

    checked = st.checkbox(
        "Đã đeo tai nghe",
        value=st.session_state.get("headphone_confirmed", False)
    )
    st.session_state["headphone_confirmed"] = checked

    st.markdown("<div style='height:55px'></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1.2, 0.4, 1.2])
    with c1:
        if st.button("Quay lại", use_container_width=True):
            go_to(2)
    with c3:
        if st.button("Xác nhận", use_container_width=True):
            if checked:
                go_to(4)
            else:
                st.warning("Vui lòng xác nhận đã đeo tai nghe.")


def page_4_volume_setup():
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="
            text-align:center;
            font-size:22px;
            line-height:1.7;
            font-weight:600;
            max-width:980px;
            margin:0 auto 18px auto;">
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

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1.2, 0.4, 1.2])
    with c1:
        if st.button("Quay lại", use_container_width=True):
            go_to(3)
    with c3:
        if st.button("Tiếp tục", use_container_width=True):
            go_to(5)


def page_5_choose_voice():
    st.markdown("<div style='height:70px'></div>", unsafe_allow_html=True)

    voice = st.radio(
        "",
        ["Giọng Miền Bắc", "Giọng Miền Trung", "Giọng Miền Nam"],
        index=["Giọng Miền Bắc", "Giọng Miền Trung", "Giọng Miền Nam"].index(
            st.session_state.get("selected_voice", "Giọng Miền Bắc")
        )
    )
    st.session_state["selected_voice"] = voice

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1.2, 0.3, 1.2])
    with c1:
        if st.button("Quay lại", use_container_width=True):
            go_to(4)
    with c3:
        if st.button("Tiếp tục", use_container_width=True):
            cleanup_old_trial_audio()
            reset_test_state(st)
            st.session_state["voice"] = voice
            st.session_state["selected_voice"] = voice
            st.session_state["test_run_id"] = uuid.uuid4().hex
            st.session_state["trial1_started"] = False
            go_to(6)


def page_6_instruction():
    # Tăng khoảng cách phía trên để không bị mất dòng hướng dẫn
    st.markdown("<div style='height:42px'></div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div style="
            max-width:900px;
            margin:0 auto;
            text-align:center;
            font-size:22px;
            line-height:1.55;
            font-weight:600;">
            Hệ thống sẽ đọc các số từ 0–9, bạn nghe và bấm vào các phím số tương ứng. Sau khi nhập xong, bấm vào nút "Kế tiếp" để tiếp tục kiểm tra.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    demo_html = """
    <div style="display:flex;justify-content:center;">
        <div style="position:relative;width:300px;">

            <div style="
                border:1.2px solid #d9e2f1;
                border-radius:8px;
                height:34px;
                display:flex;
                align-items:center;
                justify-content:center;
                font-size:19px;
                font-weight:700;
                color:#0b63ce;
                background:#f8fbff;
                margin-bottom:5px;">
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
        .grid{
            display:grid;
            grid-template-columns:repeat(3, 1fr);
            gap:5px;
        }

        .key{
            height:30px;
            border-radius:8px;
            background:white;
            border:1px solid #d9e2f1;
            color:#1f2937;
            display:flex;
            align-items:center;
            justify-content:center;
            font-size:16px;
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
            gap:34px;
            margin-top:10px;
        }

        .demoBtn{
            height:30px;
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

        .demoBtn.active{
            background:#dbeafe;
            border:2px solid #0b63ce;
            color:#0b63ce;
            transform:scale(0.96);
        }

        #finger{
            position:absolute;
            font-size:40px;
            left:122px;
            top:50px;
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
            {key:"k2", text:"2", x:122, y:50},
            {key:"k5", text:"2  5", x:122, y:85},
            {key:"k9", text:"2  5  9", x:222, y:120},
            {key:"nextBtn", text:"2  5  9", x:205, y:180}
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

    components.html(demo_html, height=245)

    st.markdown("<div style='margin-top:-18px'></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1.2, 0.4, 1.2])
    with c1:
        if st.button("Quay lại", use_container_width=True):
            go_to(5)
    with c3:
        if st.button("Bắt đầu lượt đo", use_container_width=True):
            st.session_state["trial1_started"] = False
            go_to(7)


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

    c_left, c_mid, c_right = st.columns([1.8, 2.4, 1.8])

    with c_mid:
        progress_percent = int((st.session_state["trial_index"] / TOTAL_TRIALS) * 100)
        st.progress(progress_percent, text=f"Lượt {st.session_state['trial_index']} / {TOTAL_TRIALS}")

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

        st.markdown(
            f"""
            <div style="
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

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    if trial == 1 and not st.session_state.get("trial1_started", False):
        overlay = st.empty()

        for sec in [5, 4, 3, 2, 1]:
            overlay.markdown(
                f"""
                <div style="
                    position:fixed;
                    z-index:999999;
                    inset:0;
                    background:white;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    flex-direction:column;">
                    <div style="
                        font-size:72px;
                        font-weight:900;
                        color:#004aad;
                        line-height:1;">
                        {sec}
                    </div>
                    <div style="
                        margin-top:12px;
                        font-size:20px;
                        font-weight:700;
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

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    render_keypad()
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    c_outer_l, c_main, c_outer_r = st.columns([1.8, 2.4, 1.8])

    with c_main:
        c1, c2, c3 = st.columns([1, 0.15, 1])

        with c1:
            if st.button("Quay lại", use_container_width=True):
                cleanup_old_trial_audio()
                go_to(6)

        with c3:
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
                    st.session_state["page"] = 8
                    st.session_state["current_digits"] = []
                    st.session_state["typed_digits"] = ""
                    st.rerun()
                else:
                    st.session_state["trial_index"] = trial + 1
                    st.session_state["current_digits"] = []
                    st.session_state["typed_digits"] = ""
                    st.rerun()



def page_8_result():
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="font-size:30px; font-weight:800; text-align:center; margin-bottom:4px;">
            Kết quả
        </div>
        """,
        unsafe_allow_html=True
    )

    final_snr = st.session_state.get("final_snr", None)

    if final_snr is None:
        st.warning("Chưa đủ dữ liệu để tính SRT theo điểm đảo chiều.")
    else:
        st.markdown(
            f"""
            <div style="
                text-align:center;
                font-size:24px;
                font-weight:700;
                color:#0b63ce;
                margin:6px auto 12px auto;
                max-width:720px;
                width:100%;
                box-sizing:border-box;
                overflow-wrap:break-word;
                word-break:normal;
                white-space:normal;">
                SRT: {final_snr} dB SNR
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

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1.4, 0.9, 1.4])
    with c2:
        if st.button("Đo lại", use_container_width=True):
            cleanup_old_trial_audio()
            reset_test_state(st)
            st.session_state["test_run_id"] = uuid.uuid4().hex
            st.session_state["trial1_started"] = False
            go_to(1)
