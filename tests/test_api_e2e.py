"""
tests/test_api_e2e.py
=====================
Pengujian End-to-End API Backend Flask HideBit
"""

import urllib.request
import urllib.error
import json
import base64

def test_api():
    base_url = "http://localhost:8080"
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"

    with open("test_results/sample_cover.png", "rb") as f:
        img_data = f.read()

    print("[*] 1. Menguji POST /api/embed...")
    embed_body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="cover"; filename="cover.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("latin1") + img_data + (
        f"\r\n--{boundary}\r\n"
        f'Content-Disposition: form-data; name="message"\r\n\r\n'
        f"Pesan Rahasia API Berhasil Diuji!\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="key"\r\n\r\n'
        f"StegoKeyRahasia#2024\r\n"
        f"--{boundary}--\r\n"
    ).encode("latin1")

    req = urllib.request.Request(
        f"{base_url}/api/embed",
        data=embed_body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )

    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode())
        assert res["success"] is True
        print(f"    -> Embed Sukses! PSNR: {res['metrics']['psnr_db']} dB, MSE: {res['metrics']['mse']}")
        stego_b64 = res["stego_image"].split(",")[1]
        stego_bytes = base64.b64decode(stego_b64)

    print("[*] 2. Menguji POST /api/extract (Kunci Benar)...")
    extract_body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="stego"; filename="stego.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("latin1") + stego_bytes + (
        f"\r\n--{boundary}\r\n"
        f'Content-Disposition: form-data; name="key"\r\n\r\n'
        f"StegoKeyRahasia#2024\r\n"
        f"--{boundary}--\r\n"
    ).encode("latin1")

    req_ext = urllib.request.Request(
        f"{base_url}/api/extract",
        data=extract_body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )

    with urllib.request.urlopen(req_ext) as resp:
        res_ext = json.loads(resp.read().decode())
        assert res_ext["success"] is True
        print(f"    -> Pesan berhasil diekstrak: '{res_ext['message']}'")
        assert res_ext["message"] == "Pesan Rahasia API Berhasil Diuji!"

    print("[*] 3. Menguji POST /api/extract (Kunci Salah - Harus Ditolak)...")
    wrong_body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="stego"; filename="stego.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("latin1") + stego_bytes + (
        f"\r\n--{boundary}\r\n"
        f'Content-Disposition: form-data; name="key"\r\n\r\n'
        f"KunciYangSalahTotal123\r\n"
        f"--{boundary}--\r\n"
    ).encode("latin1")

    req_wrong = urllib.request.Request(
        f"{base_url}/api/extract",
        data=wrong_body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )

    try:
        urllib.request.urlopen(req_wrong)
        assert False, "Harusnya gagal ketika kunci salah!"
    except urllib.error.HTTPError as e:
        err = json.loads(e.read().decode())
        print(f"    -> Berhasil ditolak: HTTP {e.code} - {err['error']}")

    print("[*] 4. Menguji POST /api/analyze (Steganalisis)...")
    analyze_body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="stego.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("latin1") + stego_bytes + (
        f"\r\n--{boundary}--\r\n"
    ).encode("latin1")

    req_an = urllib.request.Request(
        f"{base_url}/api/analyze",
        data=analyze_body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )

    with urllib.request.urlopen(req_an) as resp:
        res_an = json.loads(resp.read().decode())
        assert res_an["success"] is True
        print(f"    -> Skor Steganalisis: {res_an['score']}/100")
        print(f"    -> LSB Planes (R, G, B) diterima: {bool(res_an['lsb_planes']['red'])}")

    print("\n[V] SEMUA ENDPOINT API BERJALAN SEMPURNA!")

if __name__ == "__main__":
    test_api()
