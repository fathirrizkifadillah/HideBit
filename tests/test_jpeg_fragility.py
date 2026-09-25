"""
tests/test_jpeg_fragility.py
============================
Pengujian Kerapuhan (Fragility Test) LSB Steganography terhadap Kompresi JPEG
Tujuan:
Membuktikan secara empiris bahwa metode LSB spasial bersifat "fragile" (rapuh).
Ketika citra stego dikonversi/disimpan ulang dalam format lossy JPEG (kompresi DCT),
bit-bit LSB mengalami distorsi kuantisasi, sehingga proses ekstraksi dan dekripsi GAGAL total.
"""

import os
import sys
import io
from PIL import Image

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.crypto import encrypt_message
from src.stego import embed_payload, extract_payload
from src.steganalysis import extract_message

def test_fragility():
    print("=" * 70)
    print("  UJI KERAPUHAN STEGANOGRAFI LSB TERHADAP KOMPRESI JPEG (LOSSLESS VS LOSSY)")
    print("=" * 70)

    # 1. Siapkan cover dan payload
    cover = Image.open("sample_images/citra1_gradient.png").convert("RGB")
    message = "Dokumen Rahasia Kerapuhan LSB UTS Keamanan Informasi."
    stego_key = "PasswordKerapuhan123"

    # 2. Sisipkan payload ke LSB citra PNG (Lossless)
    payload = encrypt_message(message, stego_key)
    stego_png = embed_payload(cover, payload, stego_key)
    
    os.makedirs("test_results", exist_ok=True)
    stego_png.save("test_results/fragility_test.png", format="PNG")
    print("[1] Citra stego berhasil disimpan dalam format PNG (Lossless).")

    # 3. Verifikasi: Ekstraksi pada format PNG harus BERHASIL 100%
    recovered_text = extract_message(stego_png, stego_key)
    assert recovered_text == message, "Ekstraksi PNG lossless gagal!"
    print("    -> Uji Ekstraksi PNG Lossless: BERHASIL 100% ('" + recovered_text + "')")

    # 4. Simpan ke format JPEG dengan berbagai tingkat kualitas
    qualities = [95, 85, 60]
    print("\n[2] Menguji dampak kompresi lossy JPEG terhadap integritas bit LSB:")

    for q in qualities:
        jpeg_buffer = io.BytesIO()
        stego_png.save(jpeg_buffer, format="JPEG", quality=q)
        jpeg_buffer.seek(0)
        stego_jpeg = Image.open(jpeg_buffer)

        print(f"\n  [*] Menguji Stego Image disimpan ke JPEG (Quality = {q}):")
        try:
            # Mencoba ekstrak dari citra JPEG
            extract_message(stego_jpeg, stego_key)
            print("      [!] Anomali: Pesan berhasil diekstrak (seharusnya gagal)!")
        except ValueError as e:
            print(f"      [V] EKSTRAKSI GAGAL SEPERTI YANG DIHARAPKAN:")
            print(f"          Alasan: {e}")

    print("\n" + "=" * 70)
    print("  KESIMPULAN: METODE LSB SPASIAL TERBUKTI RAPUH (FRAGILE)")
    print("  Kompresi lossy DCT JPEG merusak pola bit LSB dan mengacaukan")
    print("  integritas payload terenkripsi sehingga sistem menolak data rusak.")
    print("=" * 70)

if __name__ == "__main__":
    test_fragility()
