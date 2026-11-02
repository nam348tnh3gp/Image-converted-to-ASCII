# ASCII Art Studio Pro

**Chuyển đổi ảnh thành nghệ thuật ASCII** với giao diện web đẹp, nhiều tùy chọn chỉnh sửa và xuất file.

## Tính năng

- Hỗ trợ nhiều định dạng ảnh: JPG, PNG, GIF, WEBP, BMP, TIFF...
- Tùy chỉnh chuyên sâu:
  - Độ rộng (40–400 ký tự)
  - Brightness, Contrast, Saturation, **Hue**
  - Grayscale, Sepia, Invert
  - Threshold, Sharpness, Edge Detection
  - Nhiều bảng gradient ASCII (normal, detailed, blocks, retro...)
  - Space Density
- Xuất kết quả:
  - Copy clipboard
  - Tải file `.txt`
  - Tải file `.html` (gallery)
  - Tải ảnh PNG/JPG với màu nền & màu chữ tùy chỉnh
- Giao diện tiếng Việt, responsive
- Sẵn sàng deploy (Heroku / Render / Railway)

## Cài đặt & Chạy local

```bash
# Clone repo
git clone https://github.com/nam348tnh3gp/Image-converted-to-ASCII.git
cd Image-converted-to-ASCII

# Tạo môi trường ảo (khuyến nghị)
python -m venv venv
source venv/bin/activate   # Windows: venv\\Scripts\\activate

# Cài dependencies
pip install -r requirements.txt

# Chạy
python app.py
```

Mở trình duyệt: `http://localhost:5000`

## Deploy

### Heroku
Repo đã có `runtime.txt` và `Procfile`:

```bash
heroku create ten-app-cua-ban
git push heroku main
```

### Render / Railway
Chọn **Python**, build command: `pip install -r requirements.txt`, start command: `gunicorn app:app`

## API Endpoints

| Method | Path              | Mô tả                    |
|--------|-------------------|--------------------------|
| GET    | `/`               | Giao diện chính          |
| POST   | `/convert`        | Chuyển ảnh → ASCII       |
| POST   | `/download/txt`   | Tải .txt                 |
| POST   | `/download/html`  | Tải .html                |
| POST   | `/download/image` | Tải PNG/JPG              |
| GET    | `/health`         | Health check             |

## Công nghệ

- Backend: Flask + Pillow + NumPy
- Frontend: HTML/CSS/JS thuần
- Deploy: Gunicorn

## Giấy phép

MIT

---

**ASCII Art Studio Pro** – Biến mọi bức ảnh thành nghệ thuật ký tự.
