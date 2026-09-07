# DIN Test — Current State Review

Ngày review: 2026-09-05. Repository: `E:/Project/DIN-test-github/Dintest`.
Baseline: `71fd5afbd2068ec5cd376221a1d885f5bd48393a` (`Fix audio paths for Streamlit Cloud`).

## Phạm vi và kết luận

Đã đọc source hiện tại của cả hai bộ application, README, dependency declarations, ignore rules và CSS; kiểm kê Git, kiểm tra cấu trúc/nội dung PCM của toàn bộ 31 WAV và xác minh decode của 2 PNG. Repository có 47 tracked files, gồm 3 bytecode Python 3.13; bytecode được coi là artifact, không phải source of truth. Không có AGENTS.md trong repository hoặc các thư mục cha đã kiểm tra.

Application được README chỉ định là `app/app.py`. Flow chính chạy được trong Streamlit AppTest đến kết quả sau 23 lượt trên Python 3.11.6. Tuy nhiên chưa thể kết luận sẵn sàng cho triển khai sử dụng thực tế: có lỗi vòng đời audio khi quay lại, lỗi recovery sau generation failure, playback không có xác nhận từ browser, và clipping đã được đo trong masker trước final limiter. Các vấn đề protocol/clinical dưới đây đều **REQUIRES REVIEW**, không được tự sửa.

Chỉ tạo báo cáo này. Không sửa source, dependencies, thuật toán, constants, assets, thresholds hoặc tests; không fetch/push hay tương tác GitHub remote. Validation dùng script qua stdin, compile trong bộ nhớ và `python -B`; WAV thử được tạo trong temp rồi xóa. Server local thử nghiệm đã dừng.

**Giới hạn đối chiếu lịch sử:** `docs/PHASE_0_AUDIT.md` và `docs/PHASE_1_SUMMARY.md` không tồn tại. `git log --all -- <các đường dẫn này>` không trả commit nào trong lịch sử cục bộ (5 commit reachable). Vì không có nội dung/ID finding cũ, không thể hoàn thành phân loại từng finding cũ mà không suy đoán. Việc thiếu tài liệu không có nghĩa finding đã resolved hoặc no longer applicable.

## Current architecture

### Entry points và application flow

- `app/app.py`: cấu hình Streamlit, CSS inline, khởi tạo session, điều hướng theo số trang 1–10. Import `core` và `pages` dạng top-level; khi chạy theo README, lấy `app/core.py` và `app/pages.py`.
- `app/core.py`: constants, lựa chọn digits, scoring, adaptive SNR, reversal/SRT, audio processing, khởi tạo/reset session; chưa tách module chuyên trách.
- `app/pages.py`: toàn bộ UI, navigation, generation/submit lifecycle, HTML/JavaScript playback, microphone gauge, kết quả.
- Flow: intro → profile → health → môi trường → xác nhận tai nghe → âm lượng → chọn giọng → hướng dẫn → 23 lượt đo → kết quả. Trang hướng dẫn chỉ có demo keypad, không phải adaptive practice block.
- Bộ `app.py`, `core.py`, `pages.py` ở root là implementation khác: 8 trang, không có profile/health, UI và thông báo kết quả khác. Không phải module mà entrypoint được tài liệu hóa sử dụng. Hai bộ import tên giống nhau tạo nguy cơ import nhầm trong runner/test nếu `sys.path` hoặc cache module không đúng.
- Không có database, API backend riêng, export kết quả, authentication, CI workflow hay test suite trong checkout. Dữ liệu thu thập và kết quả nằm trong session RAM.

### Session state

`app/core.py:278–318` khởi tạo page, profile/health, headphone confirmation, voice/selected_voice, trial_index, current_snr, snr_history, current_digits, typed_digits, results, final_snr, trial_audio_path, test_run_id, trial1_started, used_digit_files. List defaults được tạo mới mỗi lần gọi, không thấy mutable global list dùng chung giữa session.

Chọn giọng rồi tiếp tục gọi cleanup/reset và tạo UUID mới. Mỗi submit ghi SNR đã phát và một result row (trial/target/answer/correct_count/passed/snr), cập nhật SNR, cleanup WAV, rồi chuyển lượt hoặc tính kết quả. Reset test không reset profile/health/headphone/voice. Đã xác minh “Đo lại” giữ gender, health_conditions và headphone_confirmed. Cần làm rõ đây là đo lại cùng người hay bắt đầu người mới. `hearing_diagnosis` và `hearing_device` chỉ có default, chưa dùng ở UI hoặc scoring. Không có phục hồi phiên sau server restart.

### DIN/adaptive/scoring/result đang thực thi

| Nội dung | Implementation hiện tại |
|---|---|
| Stimulus | 3 digits lấy bằng random.sample từ 0–9, không lặp trong cùng triplet |
| Trial count | 23 |
| Start/step/bounds | 0 dB; bước 2 dB; clamp −20 đến +4 dB |
| Scoring | Đúng đủ 3/3 và đúng thứ tự mới pass; tên check_2_of_3 không phản ánh behavior |
| Adaptation | Pass giảm 2; fail tăng 2; bounds có thể tạo plateau |
| History | Chỉ append SNR của từng trial đã submit, không append SNR sau trial 23 |
| Reversal | Cực trị chặt so với hai hàng xóm, lọc trial 4–23 |
| SRT | Mean các reversal tìm được, round 2 decimals; không có reversal trả None |
| Classification | ≤ −13.11; > −13.11 và ≤ −12.02; > −12.02 |

`get_reversal_points` duyệt các index có đủ hai hàng xóm. Với history dài 23, thực tế chỉ xét được trial 4–22; trial 23 không thể thành reversal dù docstring nói 4–23. Plateau không được tính reversal. Một reversal đã đủ để trả SRT. Đây là behavior được ghi nhận, không phải xác nhận đúng protocol.

### Audio/assets/path handling

`app/core.py` xác định path từ `__file__`: digits/noise ở repository root; logo-transparent ở app/images. VOICE_MAP trỏ bac/trung/nam và tìm được đủ 0–9 ở cả ba giọng. Không phụ thuộc working directory đối với các asset path này. Commit hiện tại đã bỏ FFmpeg path tuyệt đối trên ổ D và dùng shutil.which.

Pipeline: đọc WAV → mono/44100 Hz → normalize từng digit về −19.3529 dBFS → fade 20 ms hai đầu → peak cap −6 dBFS → ghép 3 digits với hai gap ngẫu nhiên 220–280 ms → peak cap → thêm 500 ms trước/sau → normalize lại toàn speech có cả silence → lấy noise từ đầu file, repeat khi cần → normalize noise về TARGET_SPEECH_DBFS − SNR → overlay → peak cap −6 → export WAV temp. Limiter là giảm gain toàn segment, không tái tạo tín hiệu đã clipping trước đó. Noise luôn bắt đầu cùng offset, không có random crop.

Audio trial gửi dưới dạng base64 qua components.html; player ẩn, autoplay và sessionStorage để tránh replay theo run/trial. Preview phát raw digits theo playlist 1/2/3, đặt volume 0.5 và chỉnh trong iframe; không lưu volume sang Python hay trial player. Microphone gauge chạy browser-side; không gửi phép đo/gating về session. Chưa thấy upload hoặc lưu recording microphone ở server.

## Changes since previous audit

Không có hai báo cáo cũ để xác định delta với audit. Các thay đổi có thể chứng minh độc lập:

1. `71fd5af` so với parent: chỉ đổi app/core.py để tìm FFmpeg trên PATH và đổi VOICE_MAP từ tên thư mục tiếng Việt sang bac/trung/nam. Không đổi DIN/audio math ở commit này.
2. So sánh hai bộ source hiện tồn tại: app/ có profile/health, 10 trang, stepbar, CSS responsive và countdown mới, logo-transparent, thông báo thêm ở volume setup và nhánh SRT None. Không khẳng định bộ root chính là baseline Phase 0.
3. Hai core hiện giống nhau về thuật toán và audio math; khác logo path và defaults profile/health. Source hiện tại vẫn chưa dùng architecture config/din_logic/audio/session từng được nhắc tới.
4. README gọi đây là deploy-only prototype và nêu SRT, audio homogenization, volume persistence, calibration, cutoff chưa sửa. Đây chỉ là bằng chứng về các chủ đề cũ, không cung cấp danh sách finding đầy đủ.

## Previous findings status

Quy ước khi có finding gốc: RESOLVED = nguyên nhân đã hết và có bằng chứng; STILL PRESENT = còn nguyên; CHANGED = đã thay đổi nhưng chưa hết hoặc thay scope; NO LONGER APPLICABLE = code/flow liên quan không còn áp dụng. Không dùng nhãn này để che việc thiếu bằng chứng.

**Đối chiếu từng finding trong PHASE_0_AUDIT.md: chưa thể thực hiện — thiếu tài liệu nguồn.** Cần cung cấp bản audit cũ hoặc vị trí local trước khi khẳng định bảng đối chiếu hoàn chỉnh.

Bảng sau chỉ đối chiếu những chủ đề được README và commit local chứng minh; không phải tái dựng ID finding Phase 0:

| Chủ đề tham chiếu | Trạng thái | Bằng chứng hiện tại |
|---|---|---|
| Voice folder names không khớp assets | RESOLVED trong entrypoint app/ | Commit 71fd5af; đủ 10 digits/voice; 12 mix thành công |
| FFmpeg hardcode ổ D | RESOLVED về hardcode | shutil.which; packages.txt khai báo ffmpeg; chưa chứng minh Cloud install |
| Asset path toàn repository | CHANGED / chưa đồng nhất | app/ đúng; root core vẫn trỏ assets lên repository parent và logo root/images không tồn tại |
| SRT | STILL PRESENT ở cấp chủ đề README | Endpoint/plateau/minimum reversal chưa có protocol validation |
| Audio homogenization | STILL PRESENT ở cấp chủ đề README | Raw RMS gần bằng nhau nhưng fade/peak cap theo digit và normalize sequence tiếp tục thay mức tương đối |
| Volume persistence | STILL PRESENT | iframe volume không truyền sang trial |
| Calibration | STILL PRESENT | dBFS không có SPL calibration; gauge OFFSET 88 |
| Cutoff validation | STILL PRESENT | Hai ngưỡng hardcoded, không có nghiên cứu/protocol kèm repository |

Không có bằng chứng đủ để gán NO LONGER APPLICABLE cho bất kỳ finding gốc nào.

### Review previous Phase 1 work

| File được yêu cầu kiểm tra | Tồn tại / được dùng | Kết luận |
|---|---|---|
| app/config.py | Không / không | Constants đang ở app/core.py |
| app/din_logic.py | Không / không | DIN logic đang ở app/core.py |
| app/audio.py | Không / không | Audio đang ở app/core.py |
| app/session.py | Không / không | Session helpers đang ở app/core.py |
| tests/test_din_logic.py | Không / không | Không có tests directory/test suite |

Không thấy lịch sử các đường dẫn trên trong git log --all local. Chưa thể đánh giá chất lượng nội dung module cũ khi không có file. Không phục hồi, tích hợp hoặc tạo lại các module này. Architecture app/ hiện tại là điểm xuất phát cho đề xuất Phase 1.

## New findings / findings xác lập từ current source

“New” ở đây nghĩa là được ghi nhận trong re-audit này; chưa chứng minh chúng mới phát sinh từ Phase 0.

| ID | Mức | Finding, bằng chứng và tác động |
|---|---|---|
| F01 | High | Back/return mất audio: app/pages.py:1148 cleanup rồi về hướng dẫn nhưng giữ current_digits; ensure_trial_generated:963 chỉ xét digits rỗng. AppTest tái hiện quay lại page 9 với 3 digits, audio None, error nhưng keypad vẫn hoạt động. |
| F02 | High | Generation failure để state dở dang: app/pages.py:964 gán digits trước mix, không catch/recover. Mock FileNotFoundError trong bộ nhớ: gọi ensure hai lần nhưng mix chỉ gọi một lần, 3 digits còn lại và audio None. |
| F03 | High | Playback không đáng tin cậy: app/pages.py:209–212 set played trước khi play thành công, catch rỗng; player ẩn không có recovery. Không có client ended/played acknowledgment và Next chỉ yêu cầu 3 digits. Có thể score dù audio thiếu/chưa hoàn tất. Browser impact chưa được kiểm thử thực tế. |
| F04 | High | Masker clipping trước final limiter được đo; xem clinical C03. Peak output −6 không đảm bảo SNR yêu cầu đã được giữ. |
| F05 | High nếu chạy nhầm | Root entrypoint trỏ sai assets. Root AppTest báo thiếu logo; root core PROJECT_DIR là repository parent, voice/noise đều ngoài vị trí assets thật. |
| F06 | Medium | Thiếu durable regression suite và CI. unittest discover chạy 0 tests, không được hiểu là suite pass. |
| F07 | Medium | Dependency/runtime chưa tái lập đầy đủ: chỉ pin streamlit/pydub, không chỉ định Python, chưa khai báo compatibility cho Python bỏ audioop. Máy hiện tại không có FFmpeg trên PATH. |
| F08 | Medium | Temp cleanup chỉ ở thao tác điều hướng/submit; bỏ tab hoặc server interruption có thể để file. cleanup nuốt mọi exception rồi quên path; export không có finally để close/remove khi lỗi. Không thấy retention cleanup/caching; noise dài 263 giây được decode/resample lại mỗi trial. |
| F09 | Medium | Profile/health/headphone còn sau Đo lại, đã xác minh. Dữ liệu chỉ trong RAM, không gắn vào result row/export. Cần định nghĩa rõ vòng đời người tham gia; không tự thêm lưu trữ. |
| F10 | Low | Duplication hai bộ app/core/pages; app/styles/styles.css không được load; app/images/logo.png không được app/ dùng; get_reversal_points import trong pages nhưng không gọi; hearing_diagnosis/hearing_device defaults chưa dùng. used_digit_files chỉ lưu để theo dõi, chưa có consumer UI. |
| F11 | Low | Có 3 tracked app/__pycache__/*.cpython-313.pyc mặc dù .gitignore bỏ qua bytecode. Không dùng chúng làm bằng chứng Python 3.13 hoạt động. |
| F12 | Medium | st.components.v1.html phát deprecation warning trong runtime 1.61.1 đang cài. Chưa hỏng ở test hiện tại; nâng dependency cần browser regression cho microphone/audio. Không tự migrate. |

Validation input hiện có: profile bắt buộc đủ trường; health chặn lựa chọn exclusive mâu thuẫn và mục khác rỗng; headphone phải xác nhận; keypad giới hạn 3 digits; submit thiếu 3 có warning. Những kiểm tra này không thay cho audio readiness hoặc protocol validity. Page router không có fallback cho page ngoài 1–10. Asset discovery chấp nhận cả MP3 dù repository hiện chỉ có WAV, có thể overwrite mapping nếu sau này nhiều file cùng digit; chưa kiểm tra cardinality/decoded content ở startup.

## Current test status

Environment: Windows, Python 3.11.6, Streamlit 1.61.1, pydub 0.25.1. Sandbox launcher lỗi os error 206; các lệnh audit/validation được chạy ngoài sandbox sau tool approval. Không cài hoặc nâng dependency.

| Validation | Kết quả |
|---|---|
| Compile in memory | PASS 6/6 Python source; không viết pyc |
| Import | app/core.py và app/pages.py import được với app/ ở đầu sys.path; entrypoint được thực thi qua AppTest; cả root và app/ intro chạy được, root có st.error missing logo |
| pip check | PASS: No broken requirements found |
| Dependency versions | Khớp requirements.txt; FFmpeg không có PATH, pydub cảnh báo nhưng PCM WAV vẫn decode/export thành công |
| unittest discover -v | 0 tests; không có repository unit suite |
| Ad hoc baseline assertions | PASS: 3/3 vs 2/3, step/bounds, no reversal, strict reversal trial 4, plateau không reversal, SRT một reversal, 100 triplets không lặp; chỉ khóa behavior quan sát, không chứng minh chuẩn clinical |
| Asset integrity | 31/31 WAV đủ dữ liệu PCM theo header, decode được; 30 digits mono/16-bit/16000 Hz, 600–970 ms; noise cùng format, 263317 ms. 2/2 PNG verify được, 1536×1024 RGBA |
| Audio generation | 12/12 mix: ba giọng × SNR +4, 0, −12, −20, digits 1/2/3; output khoảng 3450–3815 ms, max peak khoảng −6 dBFS. Gap ngẫu nhiên nên duration không cố định |
| Full AppTest | Intro/profile/health/environment/headphone/volume/voice/instruction → 23 trials → page 10, 23 rows/history, final_snr −1.05, không exception. Câu trả lời xen kẽ đúng và 999; không đánh giá clinical |
| Regression probes | Xác nhận F01 back/return; F02 generation failure; reset giữ profile/health/headphone |
| Streamlit server | python -B -m streamlit run app/app.py --server.headless=true --server.address=127.0.0.1 --server.port=18571 --browser.gatherUsageStats=false; /_stcore/health HTTP 200 ok; process thử đã terminate |
| Browser/Cloud | Chưa kiểm tra audio thực nghe, autoplay/sessionStorage/rerun giữa lúc phát, microphone permissions, mobile, Linux hoặc deploy Cloud thực tế |

AppTest không chạy JavaScript iframe và server health không xác nhận trải nghiệm audio. Asset integrity là kiểm tra cấu trúc/decoder, không xác nhận người nói đọc đúng tên digit, đặc tính phổ masker, hoặc psychometric equivalence. Raw RMS digits chủ yếu khoảng −19.351 dBFS; một số nam gần full scale (nam_5/nam_8 peak xấp xỉ 0), cần phân tích chuyên môn, không tự kết luận bản ghi đạt chuẩn.

## Deployment risks

1. Chọn đúng main file app/app.py và giữ layout repository. Bộ root không dùng được với path hiện tại.
2. requirements.txt ở root và packages.txt chứa ffmpeg phù hợp cơ chế khai báo dependency của Community Cloud; việc cài thành công trên Cloud vẫn chưa được thử. Tham chiếu: [Streamlit app dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies).
3. Cần chọn và kiểm thử Python rõ ràng. Python 3.13 bỏ audioop ([Python documentation](https://docs.python.org/3/library/audioop.html)); pydub 0.25.1 cục bộ import audioop rồi fallback pyaudioop, trong khi repository không khai báo fallback. Rủi ro clean runtime Python 3.13+, chưa phải kết quả chạy thất bại trên Cloud. Python 3.11.6 là runtime đã kiểm tra ở lượt này.
4. Browser audio/mic là critical path chưa được E2E; base64 gửi lại qua rerun và iframe remount cần test, không suy từ AppTest là playback pass.
5. Repeated full-noise decoding/resampling, base64 và temporary files cần đo resource usage khi nhiều session. Không có benchmark concurrency trong lượt này.
6. Dữ liệu session không bền qua restart; hồ sơ còn khi đo lại. Cần xác nhận yêu cầu sử dụng kiosk/người mới trước khi thay lifecycle.

## Clinical/protocol REQUIRES REVIEW

Không đề xuất tự chỉnh con số, algorithm, assets hoặc xử lý tín hiệu trong nhóm này. Cần protocol owner xác nhận tiêu chí và clinical reviewer đánh giá trước implementation liên quan.

- **C01 — Adaptive/scoring/stimulus:** xác nhận 23 trials, start 0, step 2, bounds −20/+4, pass 3/3 đúng vị trí, triplet không lặp, không có practice audio. Tên check_2_of_3 gây hiểu sai nhưng behavior hiện tại là 3/3.
- **C02 — Reversal/SRT:** strict neighbor extrema bỏ plateau; trial 23 không được xét với 23 phần tử; không có minimum reversal count ngoài ít nhất 1. Ví dụ [0,−2,−4,−6,−4] cho reversal trial 4/SRT −6; [0,−2,−4,−6,−6,−4] không reversal. Chuỗi toàn pass hoặc toàn fail có thể không reversal; None không tự chứng minh người nghe làm sai hoặc có bệnh. Thông báo app/pages.py:1207 cần review, khác thông báo trung tính ở root.
- **C03 — Clipping và achieved SNR:** đo 3600 ms noise đầu file sau resample, gọi đúng normalize_audio hiện tại: SNR 0 target −19.3529, actual −19.3535 dBFS, 0/158760 samples ở rails; SNR −12 target −7.3529, actual −7.5120, 3028 rail samples; SNR −20 target +0.6471, actual −2.6198, 56441 rail samples. Đây là clipping đo được ở noise trước overlay/peak cap. Hạ peak của mixed sau đó không khôi phục tín hiệu hoặc ratio đã mất. Chưa đo achieved SNR cho toàn bộ triplet space.
- **C04 — Normalization/homogenization:** raw digits gần cùng RMS nhưng fade và peak limiting từng digit tạo attenuation khác nhau; normalize lại sequence có silence thay mức active speech theo thời lượng/gap. Cần định nghĩa cửa sổ đo RMS/SNR và calibration phù hợp assets, không coi equal RMS là equal intelligibility.
- **C05 — Timing/masker:** docstring gap 200 ±50 ms khác implementation 220–280 ms; noise lead/trail 500 ms; masker lấy cùng đầu file. Cần xác nhận timing/crop/spectrum, không tự đổi gap hoặc noise.
- **C06 — Volume/calibration:** preview raw digits với player.volume=0.5, trial player không gán volume và không nhận giá trị đã chỉnh. dBFS không xác định SPL ở tai; setting thiết bị 50–60% không phải calibration. Sửa persistence/calibration tác động stimulus delivery nên cần duyệt phương án trước.
- **C07 — Cutoffs và dân số:** −13.11/−12.02 dùng chung ba giọng, không có validation dataset/protocol trong repository. Birth-year UI giới hạn từ năm hiện tại trừ 6 đến 1920 theo comment phù hợp từ khoảng 6 tuổi; không có xác minh tuổi chính xác hoặc basis clinical. Không tự đổi eligibility hay cutoff.
- **C08 — Ambient gauge:** RMS microphone cộng OFFSET 88, clamp 25–80, ngưỡng 35/50, không calibration theo thiết bị; chỉ hiển thị và không chặn tiếp tục. Có disclaimer nhưng số dB không được xác nhận là SPL chuẩn.
- **C09 — Playback validity:** xác nhận cách xử lý chưa nghe hết, lỗi autoplay, back/resume, replay và invalid trial trước khi triển khai retry/gating. Tránh tự động phát lại hoặc chấm một trial không hợp lệ theo protocol chưa được duyệt.

## Recommended Phase 1 tasks — implementation plan, chưa thực hiện

Ưu tiên architecture app/app.py + app/core.py + app/pages.py hiện có; không tự tái tạo module cũ. Mỗi task sau phải có phạm vi và tiêu chí nghiệm thu riêng. Toàn bộ plan chờ approval.

| Task | Scope nhỏ, deliverable | Nghiệm thu / dependency |
|---|---|---|
| P1-01 | Nhận/định vị PHASE_0_AUDIT và PHASE_1_SUMMARY; bổ sung bảng từng finding gốc | Mỗi ID có một nhãn RESOLVED/STILL PRESENT/CHANGED/NO LONGER APPLICABLE cùng source evidence; không giả định khi thiếu tài liệu |
| P1-02 | Tạo baseline regression suite từ implementation app/ đang chạy | Tests cho submit/history/reset, scoring/bounds/reversal endpoints/plateau; đánh dấu behavior chưa được clinical duyệt, không biến baseline thành đặc tả clinical |
| P1-03 | Làm rõ entrypoint/import và xử lý bộ root theo phương án được duyệt | Chạy đúng implementation từ root và runner; không thay DIN/audio behavior; không xóa bộ root tự động |
| P1-04 | Asset/dependency preflight và error reporting | Phát hiện thiếu/sai WAV/voice/noise với thông báo rõ trước trial; asset hashes không đổi; không auto-normalize/replace asset |
| P1-05 | Làm generation transaction an toàn | Failure không để digits ready khi chưa có WAV; retry policy phải theo C09; test missing asset/export failure, không thay random/SNR procedure |
| P1-06 | Xử lý back/return nhất quán | Thống nhất resume hoặc restart với protocol owner trước; regression cho F01, bảo toàn history/UUID/audio theo phương án duyệt |
| P1-07 | Thiết kế rồi triển khai playback lifecycle | Báo lỗi play, xác nhận trạng thái client/server, submit validity; replay policy được duyệt C09; test browser thực trên desktop/mobile |
| P1-08 | Temp lifecycle và observability | Dọn đúng file do app sở hữu, logging lỗi cleanup/export, không xóa temp hệ thống; test failure/disconnect strategy; không sửa mixing |
| P1-09 | Định nghĩa reset cùng người/người mới | Xác nhận profile/health/headphone giữ hay xóa; test isolation. Không bổ sung database/export nếu chưa được yêu cầu |
| P1-10 | Runtime/deployment reproducibility | Chọn Python được hỗ trợ, clean install trên Linux, kiểm tra FFmpeg/requirements; chạy app/ và asset checks; Cloud smoke chỉ sau authorization riêng nếu cần deploy |
| P1-11 | Loại dead artifacts đã xác nhận | Tracked pyc, unused CSS/import/defaults theo scope duyệt; không đụng stimulus WAV; kiểm tra không đổi flow |
| P1-12 | Clinical review packet, chưa sửa logic | Reviewer kết luận C01–C09, định nghĩa acceptance cho SRT/SNR/volume/cutoffs. Chỉ lập task xử lý clinical/audio riêng sau khi có quyết định được duyệt |

Thứ tự đề nghị: P1-01/02 làm bằng chứng → P1-03/04 → P1-05/06 → P1-07/08/09 → P1-10/11. P1-12 có thể chuẩn bị sớm và là điều kiện trước mọi thay đổi protocol hoặc stimulus delivery liên quan. Không gộp sửa clipping, normalization, reversal hay cutoff vào refactor thông thường.

## Trạng thái bàn giao

Review current source và validation cục bộ đã thực hiện; đối chiếu từng finding cũ còn thiếu đầu vào. Không triển khai bất kỳ task Phase 1 nào. Dừng tại báo cáo và chờ approval; muốn hoàn tất comparison cần nội dung/vị trí của hai báo cáo cũ.
