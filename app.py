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
import colorsys

warnings.filterwarnings('ignore')

print(f"🐍 Python version: {sys.version}")

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Danh sách các định dạng ảnh được hỗ trợ
SUPPORTED_FORMATS = {
    'jpg': 'JPEG', 'jpeg': 'JPEG', 'png': 'PNG', 'gif': 'GIF',
    'bmp': 'BMP', 'webp': 'WEBP', 'tiff': 'TIFF', 'tif': 'TIFF',
    'ico': 'ICO', 'ppm': 'PPM', 'pgm': 'PGM', 'pbm': 'PBM',
    'xbm': 'XBM', 'pcx': 'PCX', 'tga': 'TGA'
}

# Bảng ký tự ASCII với các gradient khác nhau
ASCII_GRADIENTS = {
    'normal': " .:-=+*#%$@",
    'detailed': " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$",
    'blocks': " ░▒▓█",
    'simple': " .-+=*#%@@",
    'retro': "@%#*+=-:. ",
    'inverted': "@%#*+=-:. ",
    'contrast': " .:-=+*#%@@@@@@",
    'light': " .:-=+*",
    'dark': "*#%@@@",
}

def convert_to_rgb(img):
    """Chuyển đổi ảnh sang RGB, xử lý các định dạng đặc biệt"""
    try:
        if img.mode == 'RGBA':
            rgb_img = Image.new('RGB', img.size, (0, 0, 0))
            rgb_img.paste(img, mask=img.split()[3] if len(img.split()) > 3 else None)
            return rgb_img
        return img.convert('RGB')
    except Exception as e:
        print(f"Error converting to RGB: {e}")
        return img.convert('RGB')

def apply_hue_shift(img, hue_shift):
    """Xoay hue (0-360 độ)"""
    if hue_shift == 0:
        return img
    arr = np.array(img)
    hsv = np.zeros_like(arr, dtype=np.float32)
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            r, g, b = arr[i, j] / 255.0
            h, s, v = colorsys.rgb_to_hsv(r, g, b)
            h = (h + hue_shift / 360.0) % 1.0
            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            hsv[i, j] = [r * 255, g * 255, b * 255]
    return Image.fromarray(hsv.astype(np.uint8))

def enhance_image(img, brightness=1.0, contrast=1.0, saturation=1.0, 
                  sharpness=1.0, grayscale=0, sepia=0, invert=0,
                  threshold=255, edge_detection=0, hue=0):
    """Áp dụng các hiệu ứng chỉnh sửa ảnh"""
    try:
        img = convert_to_rgb(img)
        
        if hue != 0:
            img = apply_hue_shift(img, hue)
        
        if brightness != 1.0:
            img = ImageEnhance.Brightness(img).enhance(brightness)
        if contrast != 1.0:
            img = ImageEnhance.Contrast(img).enhance(contrast)
        if saturation != 1.0:
            img = ImageEnhance.Color(img).enhance(saturation)
        if sharpness != 1.0:
            img = ImageEnhance.Sharpness(img).enhance(sharpness)
        
        if grayscale > 0:
            gray_img = img.convert('L').convert('RGB')
            img = Image.blend(img, gray_img, grayscale)
        
        if sepia > 0:
            sepia_img = Image.new('RGB', img.size)
            pixels = img.load()
            sepia_pixels = sepia_img.load()
            for i in range(img.size[0]):
                for j in range(img.size[1]):
                    r, g, b = pixels[i, j]
                    tr = min(255, int(0.393 * r + 0.769 * g + 0.189 * b))
                    tg = min(255, int(0.349 * r + 0.686 * g + 0.168 * b))
                    tb = min(255, int(0.272 * r + 0.534 * g + 0.131 * b))
                    sepia_pixels[i, j] = (tr, tg, tb)
            img = Image.blend(img, sepia_img, sepia)
        
        if invert > 0:
            invert_img = ImageOps.invert(img)
            img = Image.blend(img, invert_img, invert)
        
        # Threshold: chỉ bật khi < 250 (255 = tắt)
        if threshold < 250:
            gray = img.convert('L')
            threshold_img = gray.point(lambda p: 255 if p > threshold else 0)
            img = threshold_img.convert('RGB')
        
        # Edge detection: blend với ảnh gốc để không bị đen xì
        if edge_detection > 0:
            edge_img = img.convert('L').filter(ImageFilter.FIND_EDGES)
            edge_img = edge_img.point(lambda p: min(255, int(p * (1.5 + edge_detection * 2))))
            if edge_detection < 1.0:
                base = img.convert('L')
                edge_arr = np.array(edge_img, dtype=np.float32)
                base_arr = np.array(base, dtype=np.float32)
                blended = np.clip(base_arr * (1 - edge_detection) + edge_arr * edge_detection, 0, 255)
                edge_img = Image.fromarray(blended.astype(np.uint8))
            img = edge_img.convert('RGB')
        
        return img
    except Exception as e:
        print(f"Error in enhance_image: {e}")
        return img

def image_to_ascii_advanced(image_data, width, brightness=1.0, contrast=1.0,
                            saturation=1.0, hue=0, grayscale=0, sepia=0,
                            invert=0, threshold=255, sharpness=1.0,
                            edge_detection=0, gradient='normal', space_density=1.0):
    """Chuyển đổi ảnh thành ASCII art với nhiều tùy chọn nâng cao"""
    try:
        if isinstance(image_data, bytes):
            img = Image.open(io.BytesIO(image_data))
        else:
            img = image_data
        
        if getattr(img, 'is_animated', False):
            img.seek(0)
        
        img = enhance_image(img, brightness, contrast, saturation, 
                           sharpness, grayscale, sepia, invert,
                           threshold, edge_detection, hue)
        
        img = img.convert('L')
        
        original_width, original_height = img.size
        aspect_ratio = original_height / original_width
        height = max(1, int(width * aspect_ratio * 0.45))
        
        try:
            img = img.resize((width, height), Image.Resampling.LANCZOS)
        except AttributeError:
            img = img.resize((width, height), Image.LANCZOS)
        
        pixels = np.array(img, dtype=np.float32)
        
        charset = ASCII_GRADIENTS.get(gradient, ASCII_GRADIENTS['normal'])
        if gradient == 'inverted':
            charset = charset[::-1]
        
        if space_density != 1.0:
            pixels = np.clip(pixels * space_density, 0, 255)
        
        chars = list(charset)
        max_index = len(chars) - 1
        
        ascii_lines = []
        for y in range(height):
            line_parts = []
            for x in range(width):
                gray_value = int(pixels[y, x])
                char_index = int((gray_value / 255.0) * max_index)
                char_index = min(max_index, max(0, char_index))
                line_parts.append(chars[char_index])
            ascii_lines.append(''.join(line_parts))
        
        return '\n'.join(ascii_lines)
    except Exception as e:
        raise Exception(f"Lỗi xử lý ảnh: {str(e)}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ads.txt')
def ads_txt():
    ads_file_path = os.path.join(os.path.dirname(__file__), 'ads.txt')
    if os.path.exists(ads_file_path):
        return send_file(ads_file_path, mimetype='text/plain', as_attachment=False)
    return "google.com, pub-4257712618696739, DIRECT, f08c47fec0942fa0", 200, {'Content-Type': 'text/plain'}

@app.route('/convert', methods=['POST'])
def convert():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'Không tìm thấy file ảnh'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'Chưa chọn file'}), 400
        
        filename = file.filename.lower()
        ext = filename.split('.')[-1] if '.' in filename else ''
        
        if ext not in SUPPORTED_FORMATS:
            return jsonify({'error': f'Định dạng ảnh không được hỗ trợ: {ext}'}), 400
        
        width = int(request.form.get('width', 100))
        brightness = float(request.form.get('brightness', 100)) / 100
        contrast = float(request.form.get('contrast', 100)) / 100
        saturation = float(request.form.get('saturation', 100)) / 100
        hue = float(request.form.get('hue', 0))
        grayscale = float(request.form.get('grayscale', 0)) / 100
        sepia = float(request.form.get('sepia', 0)) / 100
        invert = float(request.form.get('invert', 0)) / 100
        threshold = int(request.form.get('threshold', 255))
        sharpness = float(request.form.get('sharpness', 10)) / 10
        edge_detection = float(request.form.get('edge_detection', 0)) / 10
        gradient = request.form.get('gradient', 'normal')
        space_density = float(request.form.get('space_density', 1))
        
        img_bytes = file.read()
        if len(img_bytes) == 0:
            return jsonify({'error': 'File ảnh rỗng'}), 400
        
        img = Image.open(io.BytesIO(img_bytes))
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
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'error': 'Thiếu dữ liệu ảnh'}), 400
        
        img_data = base64.b64decode(data['image'].split(',')[1] if ',' in data['image'] else data['image'])
        
        width = int(data.get('width', 100))
        brightness = float(data.get('brightness', 100)) / 100
        contrast = float(data.get('contrast', 100)) / 100
        saturation = float(data.get('saturation', 100)) / 100
        hue = float(data.get('hue', 0))
        grayscale = float(data.get('grayscale', 0)) / 100
        sepia = float(data.get('sepia', 0)) / 100
        invert = float(data.get('invert', 0)) / 100
        threshold = int(data.get('threshold', 255))
        sharpness = float(data.get('sharpness', 10)) / 10
        edge_detection = float(data.get('edge_detection', 0)) / 10
        gradient = data.get('gradient', 'normal')
        space_density = float(data.get('space_density', 1))
        
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
    try:
        data = request.get_json()
        ascii_art = data.get('ascii', '')
        filename = f"ascii_art_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        temp_file.write(ascii_art)
        temp_file.close()
        
        return send_file(temp_file.name, as_attachment=True, download_name=filename, mimetype='text/plain')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/html', methods=['POST'])
def download_html():
    try:
        data = request.get_json()
        ascii_art = data.get('ascii', '')
        filename = f"ascii_gallery_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        def escape_html(text):
            return (text.replace('&', '&amp;').replace('<', '&lt;')
                    .replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;'))
        
        html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>ASCII Art</title>
    <style>
        body {{ background: #0a0f1e; color: #9ef0ff; font-family: monospace; padding: 2rem; }}
        pre {{ background: #01060c; padding: 1.5rem; border-radius: 1rem; white-space: pre; }}
    </style>
</head>
<body>
    <h1 style="text-align:center;">◢ ASCII ART ◣</h1>
    <pre>{escape_html(ascii_art)}</pre>
    <p style="text-align:center; opacity:0.6;">Generated by ASCII Art Studio | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</body>
</html>"""
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
        temp_file.write(html_content)
        temp_file.close()
        
        return send_file(temp_file.name, as_attachment=True, download_name=filename, mimetype='text/html')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/image', methods=['POST'])
def download_image():
    try:
        data = request.get_json()
        ascii_art = data.get('ascii', '')
        format_type = data.get('format', 'png').lower()
        font_size = int(data.get('font_size', 14))
        bg_color = data.get('bg_color', '#000000')
        text_color = data.get('text_color', '#9ef0ff')
        padding = int(data.get('padding', 20))
        
        lines = ascii_art.split('\n')
        if not lines:
            return jsonify({'error': 'ASCII trống'}), 400
        
        font = ImageFont.load_default()
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", font_size)
        except:
            pass
        
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
            'webp': ('WEBP', 'image/webp')
        }
        pil_format, mime_type = format_map.get(format_type, ('PNG', 'image/png'))
        
        if format_type in ['jpg', 'jpeg']:
            img = img.convert('RGB')
            img.save(img_buffer, format=pil_format, quality=95)
        else:
            img.save(img_buffer, format=pil_format)
        
        img_buffer.seek(0)
        filename = f"ascii_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format_type}"
        
        return send_file(img_buffer, as_attachment=True, download_name=filename, mimetype=mime_type)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/supported-formats')
def supported_formats():
    return jsonify({'formats': list(SUPPORTED_FORMATS.keys()), 'count': len(SUPPORTED_FORMATS)})

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'supported_formats': list(SUPPORTED_FORMATS.keys())
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
