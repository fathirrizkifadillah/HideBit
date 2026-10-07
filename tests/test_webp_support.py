"""
tests/test_webp_support.py
==========================
Pengujian Dukungan Format Citra WEBP (Lossless & Lossy) dan Validasi Penolakan SVG
"""

import io
import os
import sys
import base64
from PIL import Image

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from server import app


def test_webp_and_svg():
    client = app.test_client()

    print("=" * 70)
    print("  UJI DUKUNGAN FORMAT WEBP & VALIDASI PROTEKSI FORMAT SVG")
    print("=" * 70)

    # -------------------------------------------------------------
    # 1. Uji Penolakan SVG Secara Elegan & Edukatif
    # -------------------------------------------------------------
    print("\n[*] 1. Menguji Penolakan Berkas SVG (Format Vektor)...")
    svg_data = b'<svg width="100" height="100"><rect width="100" height="100" fill="teal"/></svg>'
    
    # 1a. /api/capacity dengan SVG
    res_cap_svg = client.post(
        "/api/capacity",
        data={"image": (io.BytesIO(svg_data), "vektor.svg", "image/svg+xml")},
        content_type="multipart/form-data"
    )
    assert res_cap_svg.status_code == 400
    assert "SVG (vektor) tidak didukung" in res_cap_svg.json["error"]
    print("    [V] /api/capacity berhasil menolak SVG dengan pesan edukatif.")

    # 1b. /api/embed dengan SVG
    res_embed_svg = client.post(
        "/api/embed",
        data={
            "cover": (io.BytesIO(svg_data), "vektor.svg", "image/svg+xml"),
            "message": "Pesan Rahasia",
            "key": "KunciRahasia123"
        },
        content_type="multipart/form-data"
    )
    assert res_embed_svg.status_code == 400
    assert "SVG (vektor) tidak didukung" in res_embed_svg.json["error"]
    print("    [V] /api/embed berhasil menolak SVG dengan pesan edukatif.")

    # 1c. /api/extract dengan SVG
    res_ext_svg = client.post(
        "/api/extract",
        data={
            "stego": (io.BytesIO(svg_data), "vektor.svg", "image/svg+xml"),
            "key": "KunciRahasia123"
        },
        content_type="multipart/form-data"
    )
    assert res_ext_svg.status_code == 400
    assert "SVG (vektor) tidak didukung" in res_ext_svg.json["error"]
    print("    [V] /api/extract berhasil menolak SVG dengan pesan edukatif.")

    # -------------------------------------------------------------
    # 2. Uji Kapasitas dan Embedding dengan Cover WEBP
    # -------------------------------------------------------------
    print("\n[*] 2. Menguji Kapasitas dan Embedding pada Citra Cover WEBP...")
    test_img = Image.new("RGB", (120, 120), color=(40, 160, 140))
    webp_cover_buf = io.BytesIO()
    test_img.save(webp_cover_buf, format="WEBP", lossless=True)
    webp_cover_bytes = webp_cover_buf.getvalue()

    # 2a. Cek Kapasitas WEBP
    res_cap = client.post(
        "/api/capacity",
        data={"image": (io.BytesIO(webp_cover_bytes), "cover.webp", "image/webp")},
        content_type="multipart/form-data"
    )
    assert res_cap.status_code == 200
    assert res_cap.json["success"] is True
    cap_bytes = res_cap.json["capacity"]["max_payload_bytes"]
    print(f"    [V] Kapasitas WebP berhasil dihitung: {cap_bytes} bytes ({res_cap.json['capacity']['max_payload_kb']} KB)")

    # 2b. Embed ke Cover WEBP
    secret_text = "Pengujian Keamanan Informasi HideBit: Integrasi WebP Lossless Sukses!"
    stego_key = "PasswordWebP2026!"
    res_embed = client.post(
        "/api/embed",
        data={
            "cover": (io.BytesIO(webp_cover_bytes), "cover.webp", "image/webp"),
            "message": secret_text,
            "key": stego_key
        },
        content_type="multipart/form-data"
    )
    assert res_embed.status_code == 200
    assert res_embed.json["success"] is True
    assert "stego_image" in res_embed.json
    assert "stego_image_webp" in res_embed.json
    print(f"    [V] Embed ke Cover WebP sukses! PSNR: {res_embed.json['metrics']['psnr_db']} dB")

    # -------------------------------------------------------------
    # 3. Uji Ekstraksi dari Hasil Stego WEBP Lossless
    # -------------------------------------------------------------
    print("\n[*] 3. Menguji Ekstraksi dari Stego Berformat WEBP Lossless...")
    stego_webp_b64 = res_embed.json["stego_image_webp"].split(",")[1]
    stego_webp_bytes = base64.b64decode(stego_webp_b64)

    res_ext_webp = client.post(
        "/api/extract",
        data={
            "stego": (io.BytesIO(stego_webp_bytes), "hidebit-stego.webp", "image/webp"),
            "key": stego_key
        },
        content_type="multipart/form-data"
    )
    assert res_ext_webp.status_code == 200
    assert res_ext_webp.json["success"] is True
    assert res_ext_webp.json["message"] == secret_text
    print(f"    [V] Ekstraksi dari WebP Lossless BERHASIL 100%: '{res_ext_webp.json['message']}'")

    # -------------------------------------------------------------
    # 4. Uji Kerapuhan WebP Lossy & Pesan Edukatif Lossy Hint
    # -------------------------------------------------------------
    print("\n[*] 4. Menguji Kerapuhan WebP Lossy & Penanganan Kesalahan...")
    stego_pil = Image.open(io.BytesIO(stego_webp_bytes))
    lossy_buf = io.BytesIO()
    stego_pil.save(lossy_buf, format="WEBP", quality=80)  # Lossy compression
    lossy_bytes = lossy_buf.getvalue()

    res_ext_lossy = client.post(
        "/api/extract",
        data={
            "stego": (io.BytesIO(lossy_bytes), "stego_lossy.webp", "image/webp"),
            "key": stego_key
        },
        content_type="multipart/form-data"
    )
    assert res_ext_lossy.status_code == 400
    assert "Kompresi lossy" in res_ext_lossy.json["error"] or "WebP Lossy" in res_ext_lossy.json["error"]
    print(f"    [V] WebP Lossy terdeteksi gagal dan memberikan catatan edukasi:")
    print(f"        -> '{res_ext_lossy.json['error'][:90]}...'")

    print("\n" + "=" * 70)
    print("  SEMUA PENGUJIAN WEBP & SVG BERHASIL DENGAN SEMPURNA!")
    print("=" * 70)


if __name__ == "__main__":
    test_webp_and_svg()
