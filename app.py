from flask import Flask, render_template, request, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import numpy as np
import os
import tempfile
from datetime import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB max file size
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Bảng ký tự ASCII (từ tối đến sáng)
CHAR_SETS = {
    'classic': " .:-=+*#%@",
    'blocks': "  ░▒▓█",
    'simple': " .-+=*#%@@",
    'retro': "@%#*+=-:. ",
    'detailed': " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$",
    'custom': " .:-=+*#%@"
}

def image_to_ascii(image_data, width, brightness=1.0, charset_str=" .:-=+*#%@"):
    """
    Chuyển đổi ảnh thành ASCII art
    
    Args:
        image_data: PIL Image object hoặc bytes
        width: số cột ASCII mong muốn
        brightness: hệ số điều chỉnh độ sáng (0.4 - 2.2)
        charset_str: chuỗi ký tự từ tối đến sáng
    
    Returns:
        string: ASCII art
    """
    try:
        # Mở ảnh nếu là bytes
        if isinstance(image_data, bytes):
            img = Image.open(io.BytesIO(image_data))
        else:
            img = image_data
        
        # Chuyển sang grayscale
        img = img.convert('L')
        
        # Tính toán chiều cao dựa trên aspect ratio
        original_width, original_height = img.size
        aspect_ratio = original_height / original_width
        height = int(width * aspect_ratio * 0.45)  # Hệ số 0.45 cho font monospace
        if height < 1:
            height = 1
        
        # Resize ảnh
        img = img.resize((width, height), Image.Resampling.LANCZOS)
        
        # Lấy dữ liệu pixel
        pixels = np.array(img, dtype=np.float32)
        
        # Điều chỉnh độ sáng
        pixels = np.clip(pixels * brightness, 0, 255)
        
        # Tạo chuỗi ký tự
        chars = list(charset_str)
        max_index = len(chars) - 1
        
        # Chuyển đổi từng pixel thành ký tự
        ascii_lines = []
        for y in range(height):
            line = ''.join(chars[min(max_index, int(pixels[y, x] / 255 * max_index))] for x in range(width))
            ascii_lines.append(line)
        
        return '\n'.join(ascii_lines)
    
    except Exception as e:
        raise Exception(f"Lỗi xử lý ảnh: {str(e)}")

def ascii_to_image(ascii_art, font_size=12, bg_color='#000000', text_color='#9ef0ff', padding=20):
    """
    Chuyển đổi ASCII art thành ảnh
    
    Args:
        ascii_art: chuỗi ASCII art
        font_size: kích thước font
        bg_color: màu nền (hex)
        text_color: màu chữ (hex)
        padding: khoảng cách viền (pixel)
    
    Returns:
        PIL Image object
    """
    try:
        lines = ascii_art.split('\n')
        
        # Tìm font monospace (ưu tiên các font phổ biến)
        font_paths = [
            '/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf',
            '/System/Library/Fonts/Monaco.dfont',
            'C:\\Windows\\Fonts\\consola.ttf',
            None  # fallback to default
        ]
        
        font = None
        for font_path in font_paths:
            try:
                if font_path:
                    font = ImageFont.truetype(font_path, font_size)
                else:
                    font = ImageFont.load_default()
                break
            except:
                continue
        
        # Tính kích thước ảnh
        char_width = font_size * 0.6  # Ước lượng chiều rộng ký tự monospace
        char_height = font_size * 1.2
        
        img_width = int(len(max(lines, key=len)) * char_width) + (padding * 2)
        img_height = int(len(lines) * char_height) + (padding * 2)
        
        # Tạo ảnh mới
        img = Image.new('RGB', (img_width, img_height), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        # Vẽ từng dòng ASCII
        y_offset = padding
        for line in lines:
            x_offset = padding
            draw.text((x_offset, y_offset), line, font=font, fill=text_color)
            y_offset += char_height
        
        return img
    
    except Exception as e:
        raise Exception(f"Lỗi tạo ảnh: {str(e)}")

@app.route('/')
def index():
    """Trang chủ"""
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    """
    API chuyển đổi ảnh sang ASCII
    Nhận: form data với file ảnh và các tham số
    Trả về: JSON với ASCII art
    """
    try:
        # Kiểm tra file ảnh
        if 'image' not in request.files:
            return jsonify({'error': 'Không tìm thấy file ảnh'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'Chưa chọn file'}), 400
        
        # Đọc tham số
        width = int(request.form.get('width', 100))
        brightness = float(request.form.get('brightness', 1.0))
        charset_name = request.form.get('charset', 'classic')
        custom_chars = request.form.get('custom_chars', '')
        
        # Lấy bảng ký tự
        if charset_name == 'custom' and custom_chars:
            charset = custom_chars
        else:
            charset = CHAR_SETS.get(charset_name, CHAR_SETS['classic'])
        
        # Đọc và xử lý ảnh
        img_bytes = file.read()
        img = Image.open(io.BytesIO(img_bytes))
        
        # Chuyển đổi sang ASCII
        ascii_art = image_to_ascii(img, width, brightness, charset)
        
        return jsonify({
            'success': True,
            'ascii': ascii_art,
            'width': width,
            'height': len(ascii_art.split('\n')),
            'charset': charset_name
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/convert/base64', methods=['POST'])
def convert_base64():
    """
    API chuyển đổi ảnh base64 sang ASCII
    """
    try:
        data = request.get_json()
        
        if not data or 'image' not in data:
            return jsonify({'error': 'Thiếu dữ liệu ảnh'}), 400
        
        # Giải mã base64
        img_data = base64.b64decode(data['image'].split(',')[1] if ',' in data['image'] else data['image'])
        
        # Đọc tham số
        width = int(data.get('width', 100))
        brightness = float(data.get('brightness', 1.0))
        charset_name = data.get('charset', 'classic')
        custom_chars = data.get('custom_chars', '')
        
        # Lấy bảng ký tự
        if charset_name == 'custom' and custom_chars:
            charset = custom_chars
        else:
            charset = CHAR_SETS.get(charset_name, CHAR_SETS['classic'])
        
        # Chuyển đổi
        img = Image.open(io.BytesIO(img_data))
        ascii_art = image_to_ascii(img, width, brightness, charset)
        
        return jsonify({
            'success': True,
            'ascii': ascii_art,
            'width': width,
            'height': len(ascii_art.split('\n'))
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/txt', methods=['POST'])
def download_txt():
    """Tải xuống file .txt"""
    try:
        data = request.get_json()
        ascii_art = data.get('ascii', '')
        filename = f"ascii_art_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # Tạo file tạm
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        temp_file.write(ascii_art)
        temp_file.close()
        
        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name=filename,
            mimetype='text/plain'
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/html', methods=['POST'])
def download_html():
    """Tải xuống file .html"""
    try:
        data = request.get_json()
        ascii_art = data.get('ascii', '')
        filename = f"ascii_gallery_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        # Tạo nội dung HTML
        html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ASCII Art Gallery</title>
    <style>
        body {{
            background: linear-gradient(135deg, #0a0f1e 0%, #0c1222 100%);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            padding: 2rem;
            font-family: 'Courier New', 'Fira Code', monospace;
        }}
        .art-container {{
            background: #01060c;
            padding: 2rem;
            border-radius: 1.5rem;
            box-shadow: 0 20px 35px rgba(0,0,0,0.5);
            overflow-x: auto;
            border: 1px solid #2d3e6e;
        }}
        pre {{
            margin: 0;
            font-size: 12px;
            line-height: 1.2;
            color: #9ef0ff;
            font-family: monospace;
            white-space: pre;
        }}
        @media (max-width: 700px) {{
            pre {{ font-size: 8px; }}
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            color: #5a7d9a;
            font-family: monospace;
        }}
        h1 {{
            text-align: center;
            color: #80b5ff;
            margin-bottom: 1rem;
        }}
    </style>
</head>
<body>
    <div>
        <h1>◢ ASCII ART ◣</h1>
        <div class="art-container">
            <pre>{escape_html(ascii_art)}</pre>
        </div>
        <div class="footer">✨ Generated by ASCII Art Studio | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    </div>
</body>
</html>"""
        
        # Tạo file tạm
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
        temp_file.write(html_content)
        temp_file.close()
        
        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name=filename,
            mimetype='text/html'
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/image', methods=['POST'])
def download_image():
    """Tải xuống ảnh (PNG, JPG, BMP, GIF)"""
    try:
        data = request.get_json()
        ascii_art = data.get('ascii', '')
        format_type = data.get('format', 'png').lower()
        font_size = int(data.get('font_size', 14))
        bg_color = data.get('bg_color', '#000000')
        text_color = data.get('text_color', '#9ef0ff')
        padding = int(data.get('padding', 20))
        
        # Chuyển ASCII sang ảnh
        img = ascii_to_image(ascii_art, font_size, bg_color, text_color, padding)
        
        # Lưu ảnh vào buffer
        img_buffer = io.BytesIO()
        
        # Xác định định dạng và MIME type
        format_map = {
            'png': ('PNG', 'image/png'),
            'jpg': ('JPEG', 'image/jpeg'),
            'jpeg': ('JPEG', 'image/jpeg'),
            'bmp': ('BMP', 'image/bmp'),
            'gif': ('GIF', 'image/gif')
        }
        
        if format_type not in format_map:
            format_type = 'png'
        
        pil_format, mime_type = format_map[format_type]
        
        # Lưu ảnh
        if format_type == 'jpg' or format_type == 'jpeg':
            # Chuyển sang RGB nếu cần và lưu với quality cao
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(img_buffer, format=pil_format, quality=95, optimize=True)
        else:
            img.save(img_buffer, format=pil_format)
        
        img_buffer.seek(0)
        
        filename = f"ascii_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format_type}"
        
        return send_file(
            img_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype=mime_type
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def escape_html(text):
    """Escape HTML special characters"""
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;'))

@app.route('/health')
def health():
    """Health check endpoint cho Render"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
