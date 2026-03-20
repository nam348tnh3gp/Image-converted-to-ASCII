from flask import Flask, render_template, request, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter, ImageOps
import io
import base64
import numpy as np
import os
import tempfile
import sys
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

print(f"🐍 Python version: {sys.version}")

try:
    from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter, ImageOps
    print(f"✅ Pillow imported successfully")
except ImportError as e:
    print(f"❌ Error importing Pillow: {e}")

try:
    import numpy as np
    print(f"✅ NumPy version: {np.__version__}")
except ImportError as e:
    print(f"❌ Error importing NumPy: {e}")
    class np:
        @staticmethod
        def array(data, dtype=None):
            return data
        @staticmethod
        def clip(data, min_val, max_val):
            return min(max(data, min_val), max_val)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Danh sách các định dạng ảnh được hỗ trợ
SUPPORTED_FORMATS = {
    'jpg': 'JPEG',
    'jpeg': 'JPEG',
    'png': 'PNG',
    'gif': 'GIF',
    'bmp': 'BMP',
    'webp': 'WEBP',
    'tiff': 'TIFF',
    'tif': 'TIFF',
    'ico': 'ICO',
    'ppm': 'PPM',
    'pgm': 'PGM',
    'pbm': 'PBM',
    'xbm': 'XBM',
    'pcx': 'PCX',
    'tga': 'TGA'
}

# Bảng ký tự ASCII với các gradient khác nhau
ASCII_GRADIENTS = {
    'normal': " .:-=+*#%@",
    'detailed': " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$",
    'blocks': "  ░▒▓█",
    'simple': " .-+=*#%@@",
    'retro': "@%#*+=-:. ",
    'inverted': "@%#*+=-:. ",
    'contrast': " .:-=+*#%@@@@@@",
    'light': " .:-=+*",
    'dark': "*#%@@@",
}

def validate_image_format(image_bytes):
    """
    Kiểm tra và xác định định dạng ảnh bằng Pillow (không dùng imghdr)
    """
    try:
        # Thử mở bằng PIL để xác định
        img = Image.open(io.BytesIO(image_bytes))
        format_type = img.format.lower() if img.format else 'unknown'
        return format_type
    except Exception as e:
        print(f"Error validating image: {e}")
        return 'unknown'

def convert_to_rgb(img):
    """
    Chuyển đổi ảnh sang RGB, xử lý các định dạng đặc biệt
    """
    try:
        if img.mode == 'RGBA':
            # Tạo nền đen cho ảnh trong suốt
            rgb_img = Image.new('RGB', img.size, (0, 0, 0))
            rgb_img.paste(img, mask=img.split()[3] if len(img.split()) > 3 else None)
            return rgb_img
        elif img.mode == 'P':
            return img.convert('RGB')
        elif img.mode == 'L':
            return img.convert('RGB')
        elif img.mode == '1':
            return img.convert('RGB')
        elif img.mode == 'CMYK':
            return img.convert('RGB')
        elif img.mode == 'YCbCr':
            return img.convert('RGB')
        else:
            return img.convert('RGB')
    except Exception as e:
        print(f"Error converting to RGB: {e}")
        return img.convert('RGB')

def enhance_image(img, brightness=1.0, contrast=1.0, saturation=1.0, 
                  sharpness=1.0, grayscale=0, sepia=0, invert=0,
                  threshold=128, edge_detection=0):
    """
    Áp dụng các hiệu ứng chỉnh sửa ảnh
    """
    try:
        # Chuyển sang RGB nếu cần
        img = convert_to_rgb(img)
        
        # Điều chỉnh độ sáng
        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(brightness)
        
        # Điều chỉnh độ tương phản
        if contrast != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(contrast)
        
        # Điều chỉnh độ bão hòa
        if saturation != 1.0:
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(saturation)
        
        # Điều chỉnh độ nét
        if sharpness != 1.0:
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(sharpness)
        
        # Chuyển sang grayscale
        if grayscale > 0:
            gray_img = img.convert('L')
            if grayscale < 1.0:
                color_img = img
                img = Image.blend(color_img, gray_img.convert('RGB'), grayscale)
            else:
                img = gray_img.convert('RGB')
        
        # Hiệu ứng Sepia
        if sepia > 0:
            sepia_img = Image.new('RGB', img.size)
            pixels = img.load()
            sepia_pixels = sepia_img.load()
            for i in range(img.size[0]):
                for j in range(img.size[1]):
                    r, g, b = pixels[i, j]
                    tr = int(0.393 * r + 0.769 * g + 0.189 * b)
                    tg = int(0.349 * r + 0.686 * g + 0.168 * b)
                    tb = int(0.272 * r + 0.534 * g + 0.131 * b)
                    sepia_pixels[i, j] = (min(255, tr), min(255, tg), min(255, tb))
            if sepia < 1.0:
                img = Image.blend(img, sepia_img, sepia)
            else:
                img = sepia_img
        
        # Đảo màu
        if invert > 0:
            invert_img = ImageOps.invert(img)
            if invert < 1.0:
                img = Image.blend(img, invert_img, invert)
            else:
                img = invert_img
        
        # Thresholding (ngưỡng)
        if threshold < 255:
            gray = img.convert('L')
            threshold_img = gray.point(lambda p: 255 if p > threshold else 0)
            img = threshold_img.convert('RGB')
        
        # Edge Detection (phát hiện cạnh)
        if edge_detection > 0:
            edge_img = img.convert('L').filter(ImageFilter.FIND_EDGES)
            if edge_detection < 1.0:
                edge_img = edge_img.point(lambda p: p * edge_detection)
            img = edge_img.convert('RGB')
        
        return img
    
    except Exception as e:
        print(f"Error in enhance_image: {e}")
        return img

def image_to_ascii_advanced(image_data, width, brightness=1.0, contrast=1.0,
                            saturation=1.0, hue=0, grayscale=0, sepia=0,
                            invert=0, threshold=128, sharpness=1.0,
                            edge_detection=0, gradient='normal', space_density=1):
    """
    Chuyển đổi ảnh thành ASCII art với nhiều tùy chọn nâng cao
    """
    try:
        # Mở ảnh
        if isinstance(image_data, bytes):
            img = Image.open(io.BytesIO(image_data))
        else:
            img = image_data
        
        # Xử lý ảnh GIF động (lấy frame đầu tiên)
        if getattr(img, 'is_animated', False):
            img.seek(0)
        
        # Áp dụng các hiệu ứng
        img = enhance_image(img, brightness, contrast, saturation, 
                           sharpness, grayscale, sepia, invert,
                           threshold, edge_detection)
        
        # Chuyển sang grayscale
        img = img.convert('L')
        
        # Tính chiều cao
        original_width, original_height = img.size
        aspect_ratio = original_height / original_width
        height = int(width * aspect_ratio * 0.45)
        if height < 1:
            height = 1
        
        # Resize ảnh
        try:
            img = img.resize((width, height), Image.Resampling.LANCZOS)
        except AttributeError:
            img = img.resize((width, height), Image.LANCZOS)
        
        # Lấy dữ liệu pixel
        pixels = np.array(img, dtype=np.float32)
        
        # Chọn bảng ký tự
        charset = ASCII_GRADIENTS.get(gradient, ASCII_GRADIENTS['normal'])
        if gradient == 'inverted':
            charset = charset[::-1]
        
        # Điều chỉnh space density
        if space_density != 1:
            pixels = np.clip(pixels * space_density, 0, 255)
        
        # Tạo chuỗi ký tự
        chars = list(charset)
        max_index = len(chars) - 1
        
        # Chuyển đổi từng pixel
        ascii_lines = []
        for y in range(height):
            line_parts = []
            for x in range(width):
                gray_value = int(pixels[y, x])
                char_index = int((gray_value / 255) * max_index)
                char_index = min(max_index, max(0, char_index))
                line_parts.append(chars[char_index])
            ascii_lines.append(''.join(line_parts))
        
        return '\n'.join(ascii_lines)
    
    except Exception as e:
        raise Exception(f"Lỗi xử lý ảnh: {str(e)}")

@app.route('/')
def index():
    """Trang chủ"""
    return render_template('index.html')

@app.route('/ads.txt')
def ads_txt():
    """Phục vụ file ads.txt"""
    try:
        ads_file_path = os.path.join(os.path.dirname(__file__), 'ads.txt')
        
        if os.path.exists(ads_file_path):
            return send_file(
                ads_file_path,
                mimetype='text/plain',
                as_attachment=False
            )
        else:
            sample_content = """# ads.txt file for ASCII Art Studio
# Replace this with your actual ads.txt content
google.com, pub-0000000000000000, DIRECT, f08c47fec0942fa0
"""
            return sample_content, 200, {'Content-Type': 'text/plain'}
    except Exception as e:
        return "Error loading ads.txt", 500

@app.route('/convert', methods=['POST'])
def convert():
    """API chuyển đổi ảnh sang ASCII với tất cả tùy chọn"""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'Không tìm thấy file ảnh'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'Chưa chọn file'}), 400
        
        # Kiểm tra định dạng file
        filename = file.filename.lower()
        ext = filename.split('.')[-1] if '.' in filename else ''
        
        if ext not in SUPPORTED_FORMATS:
            return jsonify({'error': f'Định dạng ảnh không được hỗ trợ: {ext}. Hỗ trợ: JPG, PNG, GIF, BMP, WEBP, TIFF, ICO, PPM, PGM, PBM, XBM, PCX, TGA'}), 400
        
        # Đọc tất cả tham số
        width = int(request.form.get('width', 100))
        brightness = float(request.form.get('brightness', 100)) / 100
        contrast = float(request.form.get('contrast', 100)) / 100
        saturation = float(request.form.get('saturation', 100)) / 100
        hue = float(request.form.get('hue', 0))
        grayscale = float(request.form.get('grayscale', 0)) / 100
        sepia = float(request.form.get('sepia', 0)) / 100
        invert = float(request.form.get('invert', 0)) / 100
        threshold = int(request.form.get('threshold', 128))
        sharpness = float(request.form.get('sharpness', 9)) / 10
        edge_detection = float(request.form.get('edge_detection', 1)) / 10
        gradient = request.form.get('gradient', 'normal')
        space_density = int(request.form.get('space_density', 1))
        
        # Đọc ảnh
        img_bytes = file.read()
        
        # Kiểm tra file rỗng
        if len(img_bytes) == 0:
            return jsonify({'error': 'File ảnh rỗng'}), 400
        
        # Mở ảnh với xử lý lỗi
        try:
            img = Image.open(io.BytesIO(img_bytes))
        except Exception as e:
            return jsonify({'error': f'Không thể mở file ảnh: {str(e)}'}), 400
        
        # Chuyển đổi
        ascii_art = image_to_ascii_advanced(
            img, width, brightness, contrast, saturation, hue,
            grayscale, sepia, invert, threshold, sharpness,
            edge_detection, gradient, space_density
        )
        
        return jsonify({
            'success': True,
            'ascii': ascii_art,
            'width': width,
            'height': len(ascii_art.split('\n')),
            'format': ext
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/convert/base64', methods=['POST'])
def convert_base64():
    """API chuyển đổi ảnh base64 sang ASCII"""
    try:
        data = request.get_json()
        
        if not data or 'image' not in data:
            return jsonify({'error': 'Thiếu dữ liệu ảnh'}), 400
        
        # Giải mã base64
        img_data = base64.b64decode(data['image'].split(',')[1] if ',' in data['image'] else data['image'])
        
        # Đọc tham số
        width = int(data.get('width', 100))
        brightness = float(data.get('brightness', 100)) / 100
        contrast = float(data.get('contrast', 100)) / 100
        saturation = float(data.get('saturation', 100)) / 100
        hue = float(data.get('hue', 0))
        grayscale = float(data.get('grayscale', 0)) / 100
        sepia = float(data.get('sepia', 0)) / 100
        invert = float(data.get('invert', 0)) / 100
        threshold = int(data.get('threshold', 128))
        sharpness = float(data.get('sharpness', 9)) / 10
        edge_detection = float(data.get('edge_detection', 1)) / 10
        gradient = data.get('gradient', 'normal')
        space_density = int(data.get('space_density', 1))
        
        # Chuyển đổi
        img = Image.open(io.BytesIO(img_data))
        ascii_art = image_to_ascii_advanced(
            img, width, brightness, contrast, saturation, hue,
            grayscale, sepia, invert, threshold, sharpness,
            edge_detection, gradient, space_density
        )
        
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
        
        def escape_html(text):
            return (text
                    .replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                    .replace('"', '&quot;')
                    .replace("'", '&#39;'))
        
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
        
        lines = ascii_art.split('\n')
        
        # Tìm font monospace
        font = None
        font_paths = [
            '/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
            '/System/Library/Fonts/Monaco.dfont',
            'C:\\Windows\\Fonts\\consola.ttf',
            None
        ]
        
        for font_path in font_paths:
            try:
                if font_path:
                    font = ImageFont.truetype(font_path, font_size)
                else:
                    font = ImageFont.load_default()
                break
            except:
                continue
        
        if font is None:
            font = ImageFont.load_default()
        
        char_width = font_size * 0.6
        char_height = font_size * 1.2
        
        max_line_length = max(len(line) for line in lines)
        img_width = int(max_line_length * char_width) + (padding * 2)
        img_height = int(len(lines) * char_height) + (padding * 2)
        
        img = Image.new('RGB', (img_width, img_height), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        y_offset = padding
        for line in lines:
            draw.text((padding, y_offset), line, font=font, fill=text_color)
            y_offset += char_height
        
        img_buffer = io.BytesIO()
        
        format_map = {
            'png': ('PNG', 'image/png'),
            'jpg': ('JPEG', 'image/jpeg'),
            'jpeg': ('JPEG', 'image/jpeg'),
            'bmp': ('BMP', 'image/bmp'),
            'gif': ('GIF', 'image/gif'),
            'webp': ('WEBP', 'image/webp')
        }
        
        pil_format, mime_type = format_map.get(format_type, ('PNG', 'image/png'))
        
        if format_type in ['jpg', 'jpeg']:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(img_buffer, format=pil_format, quality=95, optimize=True)
        else:
            img.save(img_buffer, format=pil_format, optimize=True)
        
        img_buffer.seek(0)
        filename = f"ascii_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format_type}"
        
        return send_file(img_buffer, as_attachment=True, download_name=filename, mimetype=mime_type)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/supported-formats')
def supported_formats():
    """Trả về danh sách các định dạng ảnh được hỗ trợ"""
    return jsonify({
        'formats': list(SUPPORTED_FORMATS.keys()),
        'count': len(SUPPORTED_FORMATS)
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'supported_formats': list(SUPPORTED_FORMATS.keys())
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
