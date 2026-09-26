"""
server.py
=========
Backend Flask Server untuk HideBit - Steganografi Citra LSB + Kriptografi AES-256-GCM
dan Analisis Steganalisis Chi-Square & Visual LSB Plane.
"""

import os
import io
import traceback
from flask import Flask, request, jsonify, send_from_directory
from PIL import Image

from src.crypto import (
    encrypt_message, decrypt_message,
    encrypt_payload_data, decrypt_payload_data,
    get_compression_info
)
from src.stego import embed_payload, extract_payload, get_image_capacity
from src.steganalysis import analyze_image, lsb_plane, extract_message, extract_payload_data
from src.metrics import get_image_metrics, get_histogram_data, image_to_base64, generate_difference_heatmap

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=BASE_DIR)


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory(BASE_DIR, filename)


@app.route("/api/capacity", methods=["POST"])
def check_capacity():
    """Menghitung kapasitas maksimum muatan gambar cover."""
    if "image" not in request.files:
        return jsonify({"success": False, "error": "Tidak ada berkas citra yang diunggah."}), 400
    
    file = request.files["image"]
    try:
        img = Image.open(file.stream).convert("RGB")
        cap = get_image_capacity(img)
        return jsonify({"success": True, "capacity": cap})
    except Exception as e:
        return jsonify({"success": False, "error": f"Gagal membaca citra: {str(e)}"}), 400


@app.route("/api/embed", methods=["POST"])
def embed():
    """
    Menyisipkan pesan rahasia (teks atau berkas biner) terenkripsi AES-256-GCM
    ke LSB citra cover dengan sebaran piksel teracak PRNG.
    """
    if "cover" not in request.files:
        return jsonify({"success": False, "error": "Berkas cover image wajib diunggah."}), 400
    
    key = request.form.get("key", "").strip()
    if not key:
        return jsonify({"success": False, "error": "Stego-key tidak boleh kosong."}), 400

    # Cek apakah payload berupa berkas biner atau pesan teks
    is_file = "secret_file" in request.files and request.files["secret_file"].filename != ""
    secret_file = request.files.get("secret_file") if is_file else None
    message = request.form.get("message", "").strip()

    if not is_file and not message:
        return jsonify({"success": False, "error": "Pesan teks atau berkas rahasia wajib diisi/diunggah."}), 400

    try:
        cover_file = request.files["cover"]
        cover_img = Image.open(cover_file.stream).convert("RGB")
        capacity = get_image_capacity(cover_img)

        # 1. Enkripsi payload dengan AES-256-GCM + PBKDF2 (kompresi adaptif zlib)
        if is_file:
            file_bytes = secret_file.read()
            filename = os.path.basename(secret_file.filename)
            comp_info = get_compression_info(file_bytes)
            encrypted_payload = encrypt_payload_data(file_bytes, data_type="file", filename=filename, password=key)
            payload_type = "file"
            payload_label = filename
            raw_size = len(file_bytes)
        else:
            text_bytes = message.encode("utf-8")
            comp_info = get_compression_info(text_bytes)
            encrypted_payload = encrypt_payload_data(text_bytes, data_type="text", filename="", password=key)
            payload_type = "text"
            payload_label = f"{len(message)} karakter"
            raw_size = len(text_bytes)

        payload_len = len(encrypted_payload)

        # 2. Sisipkan ke citra cover menggunakan LSB teracak PRNG
        stego_img = embed_payload(cover_img, encrypted_payload, key)

        # 3. Hitung metrik kualitas citra (PSNR, MSE, perubahan piksel)
        metrics = get_image_metrics(cover_img, stego_img)

        # 4. Hitung persentase kapasitas yang digunakan
        used_percent = round((payload_len / max(1, capacity["max_payload_bytes"])) * 100, 2)

        # 5. Konversi stego image & difference heatmap ke Base64 PNG data URL
        stego_b64 = image_to_base64(stego_img, "PNG")
        diff_img = generate_difference_heatmap(cover_img, stego_img)
        diff_b64 = image_to_base64(diff_img, "PNG")

        return jsonify({
            "success": True,
            "stego_image": stego_b64,
            "difference_map": diff_b64,
            "metrics": metrics,
            "compression": comp_info,
            "payload_type": payload_type,
            "payload_label": payload_label,
            "payload_bytes": payload_len,
            "raw_bytes": raw_size,
            "message_chars": len(message) if not is_file else 0,
            "capacity_bytes": capacity["max_payload_bytes"],
            "capacity_percent": used_percent,
            "image_size": f"{cover_img.width} x {cover_img.height} px"
        })

    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Terjadi kesalahan saat embedding: {str(e)}"}), 500


@app.route("/api/extract", methods=["POST"])
def extract():
    """
    Mengekstrak dan mendekripsi payload rahasia (teks atau berkas) dari stego image menggunakan stego-key.
    """
    if "stego" not in request.files:
        return jsonify({"success": False, "error": "Berkas stego image wajib diunggah."}), 400
    
    key = request.form.get("key", "").strip()
    if not key:
        return jsonify({"success": False, "error": "Stego-key wajib diisi."}), 400

    try:
        stego_file = request.files["stego"]
        stego_img = Image.open(stego_file.stream).convert("RGB")

        # Ekstrak payload dari LSB PRNG dan dekripsi dengan AES-256-GCM
        revealed = extract_payload_data(stego_img, key)
        if revealed["type"] == "file":
            import base64
            file_b64 = base64.b64encode(revealed["data"]).decode("ascii")
            return jsonify({
                "success": True,
                "type": "file",
                "filename": revealed["filename"],
                "file_data": file_b64,
                "size": revealed["size"],
                "message": f"Berkas rahasia '{revealed['filename']}' ({revealed['size']} byte) berhasil diekstrak."
            })
        else:
            return jsonify({
                "success": True,
                "type": "text",
                "message": revealed["text"],
                "size": revealed["size"]
            })

    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Gagal mengekstrak: {str(e)}"}), 500


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """
    Melakukan steganalisis Chi-Square (Pairs of Values) dan ekstraksi visual LSB Plane.
    """
    if "image" not in request.files:
        return jsonify({"success": False, "error": "Berkas citra wajib diunggah untuk analisis."}), 400

    try:
        img_file = request.files["image"]
        img = Image.open(img_file.stream).convert("RGB")

        # 1. Analisis statistik Chi-Square PoV
        analysis_result = analyze_image(img)

        # 2. Ekstrak LSB Plane per kanal (0=Red, 1=Green, 2=Blue)
        red_lsb = lsb_plane(img, channel=0)
        green_lsb = lsb_plane(img, channel=1)
        blue_lsb = lsb_plane(img, channel=2)

        # 3. Data Histogram untuk perbandingan/inspeksi
        hist_data = get_histogram_data(img)

        return jsonify({
            "success": True,
            "score": analysis_result["score"],
            "interpretation": analysis_result["interpretation"],
            "channels": analysis_result["channels"],
            "lsb_planes": {
                "red": image_to_base64(red_lsb, "PNG"),
                "green": image_to_base64(green_lsb, "PNG"),
                "blue": image_to_base64(blue_lsb, "PNG")
            },
            "histogram": hist_data
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Analisis gagal: {str(e)}"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"[*] HideBit Server berjalan di http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
