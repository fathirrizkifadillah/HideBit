"""
tests/test_file_payload_e2e.py
==============================
Verifikasi End-to-End untuk Penyembunyian Berkas Biner (PDF, DOCX, ZIP, TXT)
dan Kompatibilitas Mundur Pesan Teks via API Backend Flask.
"""

import urllib.request
import urllib.error
import json
import base64
import os

BASE_URL = "http://localhost:8080"
BOUNDARY = "----WebKitFormBoundary9zXkTrZu0gW7MA4Y"

def test_file_embed_and_extract():
    print("=" * 65)
    print("  TEST 1: PENYEMBUNYIAN & EKSTRAKSI BERKAS BINER (PDF DUMMY)")
    print("=" * 65)

    with open("test_results/sample_cover.png", "rb") as f:
        cover_bytes = f.read()

    # Buat dummy PDF content
    dummy_pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n0000000000 65535 f \n"
        b"trailer\n<< /Root 1 0 R >>\n%%EOF\n"
    )
    secret_filename = "rahasia_negara.pdf"
    stego_key = "KunciRahasiaBerkas#2026"

    # 1. POST /api/embed dengan berkas rahasia
    print(f"[*] Mengirim payload berkas '{secret_filename}' ({len(dummy_pdf_content)} byte)...")
    body = (
        f"--{BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="cover"; filename="cover.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("latin1") + cover_bytes + (
        f"\r\n--{BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="secret_file"; filename="{secret_filename}"\r\n'
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode("latin1") + dummy_pdf_content + (
        f"\r\n--{BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="key"\r\n\r\n'
        f"{stego_key}\r\n"
        f"--{BOUNDARY}--\r\n"
    ).encode("latin1")

    req = urllib.request.Request(
        f"{BASE_URL}/api/embed",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={BOUNDARY}"},
        method="POST"
    )

    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode())
        assert res["success"] is True
        assert res["payload_type"] == "file"
        print(f"    -> Embed Berkas SUKSES!")
        print(f"       Tipe: {res['payload_type']}, Label: {res['payload_label']}")
        print(f"       Ukuran Raw: {res['raw_bytes']} byte, Cipher: {res['payload_bytes']} byte")
        print(f"       PSNR: {res['metrics']['psnr_db']} dB, MSE: {res['metrics']['mse']}")
        stego_b64 = res["stego_image"].split(",")[1]
        stego_bytes = base64.b64decode(stego_b64)

    # 2. POST /api/extract dengan kunci benar
    print(f"[*] Mengekstrak berkas rahasia dengan stego-key yang benar...")
    body_ext = (
        f"--{BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="stego"; filename="stego.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("latin1") + stego_bytes + (
        f"\r\n--{BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="key"\r\n\r\n'
        f"{stego_key}\r\n"
        f"--{BOUNDARY}--\r\n"
    ).encode("latin1")

    req_ext = urllib.request.Request(
        f"{BASE_URL}/api/extract",
        data=body_ext,
        headers={"Content-Type": f"multipart/form-data; boundary={BOUNDARY}"},
        method="POST"
    )

    with urllib.request.urlopen(req_ext) as resp:
        res_ext = json.loads(resp.read().decode())
        assert res_ext["success"] is True
        assert res_ext["type"] == "file"
        assert res_ext["filename"] == secret_filename
        extracted_file_bytes = base64.b64decode(res_ext["file_data"])
        assert extracted_file_bytes == dummy_pdf_content
        print(f"    -> Ekstraksi Berkas SUKSES 100%!")
        print(f"       Nama Berkas: {res_ext['filename']}")
        print(f"       Ukuran: {res_ext['size']} byte")
        print(f"       Kesesuaian Bit-per-bit: IDENTIK!")

    # 3. POST /api/extract dengan kunci SALAH
    print(f"[*] Menguji ekstraksi dengan kunci yang SALAH (harus ditolak)...")
    body_wrong = (
        f"--{BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="stego"; filename="stego.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("latin1") + stego_bytes + (
        f"\r\n--{BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="key"\r\n\r\n'
        f"KunciSalahTotal123\r\n"
        f"--{BOUNDARY}--\r\n"
    ).encode("latin1")

    req_wrong = urllib.request.Request(
        f"{BASE_URL}/api/extract",
        data=body_wrong,
        headers={"Content-Type": f"multipart/form-data; boundary={BOUNDARY}"},
        method="POST"
    )

    try:
        urllib.request.urlopen(req_wrong)
        assert False, "Harusnya gagal ketika kunci salah!"
    except urllib.error.HTTPError as e:
        err = json.loads(e.read().decode())
        print(f"    -> Berhasil Ditolak: HTTP {e.code} - {err['error']}")

    print("\n" + "=" * 65)
    print("  TEST 2: KOMPATIBILITAS MUNDUR PESAN TEKS")
    print("=" * 65)
    text_message = "Pesan teks rahasia tetap berjalan mulus tanpa masalah!"
    text_key = "KunciTeks#42"

    body_text = (
        f"--{BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="cover"; filename="cover.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("latin1") + cover_bytes + (
        f"\r\n--{BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="message"\r\n\r\n'
        f"{text_message}\r\n"
        f"--{BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="key"\r\n\r\n'
        f"{text_key}\r\n"
        f"--{BOUNDARY}--\r\n"
    ).encode("latin1")

    req_text = urllib.request.Request(
        f"{BASE_URL}/api/embed",
        data=body_text,
        headers={"Content-Type": f"multipart/form-data; boundary={BOUNDARY}"},
        method="POST"
    )

    with urllib.request.urlopen(req_text) as resp:
        res_t = json.loads(resp.read().decode())
        assert res_t["success"] is True
        assert res_t["payload_type"] == "text"
        stego_t_bytes = base64.b64decode(res_t["stego_image"].split(",")[1])

    body_ext_t = (
        f"--{BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="stego"; filename="stego.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("latin1") + stego_t_bytes + (
        f"\r\n--{BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="key"\r\n\r\n'
        f"{text_key}\r\n"
        f"--{BOUNDARY}--\r\n"
    ).encode("latin1")

    req_ext_t = urllib.request.Request(
        f"{BASE_URL}/api/extract",
        data=body_ext_t,
        headers={"Content-Type": f"multipart/form-data; boundary={BOUNDARY}"},
        method="POST"
    )

    with urllib.request.urlopen(req_ext_t) as resp:
        res_ext_t = json.loads(resp.read().decode())
        assert res_ext_t["success"] is True
        assert res_ext_t["type"] == "text"
        assert res_ext_t["message"] == text_message
        print(f"    -> Ekstraksi Teks SUKSES: '{res_ext_t['message']}'")

    print("\n>>> SEMUA PENGUJIAN FITUR PILIHAN 1 BERHASIL 100%! <<<\n")

if __name__ == "__main__":
    test_file_embed_and_extract()
