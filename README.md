# DIN Screening - deploy build

Đây là bản **deploy-only** được tạo từ project DIN hiện tại. Logic DIN/SRT và các ngưỡng đánh giá chưa được thay đổi trong bản này.

## Cấu trúc

- `app/app.py`: entrypoint Streamlit
- `app/core.py`: logic hiện tại của DIN/audio
- `app/pages.py`: giao diện và workflow
- `digits_3regions/`: WAV chữ số cho ba giọng
- `noise/noise.wav`: masker/noise
- `requirements.txt`: Python dependencies
- `packages.txt`: cài FFmpeg trên Streamlit Community Cloud

## Chạy local

Từ thư mục root của repository:

```bash
pip install -r requirements.txt
streamlit run app/app.py
```

## Deploy Streamlit Community Cloud

1. Tạo repository GitHub mới và upload toàn bộ nội dung thư mục này.
2. Mở Streamlit Community Cloud và chọn **Create app**.
3. Chọn repository/branch tương ứng.
4. Main file path: `app/app.py`
5. Deploy.

## Lưu ý

Bản này chỉ nhằm đưa prototype lên web để chạy thử. Các vấn đề về SRT, audio homogenization, volume persistence, calibration và cutoff đã được xác định trong audit nhưng **chưa được sửa** để giữ nguyên baseline hiện tại.
