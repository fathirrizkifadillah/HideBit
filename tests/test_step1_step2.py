"""
tests/test_step1_step2.py
=========================
Skrip Pengujian Integrasi untuk Tahap 1 (Kripto) & Tahap 2 (Steganografi LSB PRNG)
"""

import sys
import os
import numpy as np
from PIL import Image

# Tambahkan folder root ke sys.path agar modul src bisa diimport
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.crypto import encrypt_message, decrypt_message
from src.stego import embed_payload, extract_payload, get_image_capacity


def test_crypto_module():
    print("\n--- [TEST 1: MODUL KRIPTOGRAFI AES-256-GCM + PBKDF2] ---")
    pesan_asli = "Halo! Ini adalah dokumen rahasia UTS Keamanan Informasi 2024."
    kunci_benar = "KunciRahasiaKripto#42"
    kunci_salah = "KunciYangSalah"
    
    print(f"Pesan Asli   : {pesan_asli}")
    print(f"Stego Key    : {kunci_benar}")
    
    # Enkripsi
    payload_terenkripsi = encrypt_message(pesan_asli, kunci_benar)
    print(f"Panjang Hasil Enkripsi : {len(payload_terenkripsi)} byte (Salt + Nonce + Ciphertext + Tag)")
    
    # Dekripsi kunci benar
    hasil_dekripsi = decrypt_message(payload_terenkripsi, kunci_benar)
    assert hasil_dekripsi == pesan_asli, "Gagal: Teks hasil dekripsi tidak cocok!"
    print("-> Dekripsi dengan kunci benar: BERHASIL 100%!")
    
    # Dekripsi kunci salah (harus ditolak)
    try:
        decrypt_message(payload_terenkripsi, kunci_salah)
        assert False, "Harusnya gagal ketika kunci salah!"
    except ValueError as e:
        print(f"-> Dekripsi dengan kunci salah: BERHASIL DITOLAK ({e})")


def test_stego_module():
    print("\n--- [TEST 2: MODUL STEGANOGRAFI LSB PRNG] ---")
    
    # Buat sampel gambar dummy 150x150 RGB
    img_array = np.random.randint(50, 200, (150, 150, 3), dtype=np.uint8)
    cover_image = Image.fromarray(img_array, mode="RGB")
    
    # Cek kapasitas
    kapasitas = get_image_capacity(cover_image)
    print(f"Ukuran Citra     : {kapasitas['width']} x {kapasitas['height']} px")
    print(f"Total Piksel     : {kapasitas['total_pixels']}")
    print(f"Kapasitas Maksimal: {kapasitas['max_payload_bytes']} byte (~{kapasitas['max_payload_kb']} KB)")
    
    pesan_rahasia = "Pesan rahasia ini disisipkan acak ke seluruh piksel menggunakan PRNG!"
    stego_key = "PasswordStegoSuperKuat123"
    
    # 1. Enkripsi pesan dulu (Tahap 1)
    payload_terenkripsi = encrypt_message(pesan_rahasia, stego_key)
    print(f"Ukuran Payload Terenkripsi : {len(payload_terenkripsi)} byte")
    
    # 2. Sisipkan ke citra dengan PRNG (Tahap 2)
    stego_image = embed_payload(cover_image, payload_terenkripsi, stego_key)
    print("-> Penyisipan payload ke LSB citra: BERHASIL!")
    
    # Simpan sampel gambar untuk verifikasi mata manusia
    os.makedirs("test_results", exist_ok=True)
    cover_image.save("test_results/sample_cover.png")
    stego_image.save("test_results/sample_stego.png")
    print("-> Citra tersimpan di: test_results/sample_cover.png & sample_stego.png")
    
    # 3. Ekstraksi dengan kunci benar
    extracted_payload = extract_payload(stego_image, stego_key)
    pesan_terbaca = decrypt_message(extracted_payload, stego_key)
    assert pesan_terbaca == pesan_rahasia, "Gagal: Pesan yang diekstrak tidak sama!"
    print(f"-> Ekstraksi & Dekripsi Kunci Benar: BERHASIL! ('{pesan_terbaca}')")
    
    # 4. Ekstraksi dengan kunci salah
    try:
        extract_payload(stego_image, "KunciYangKeliru")
        assert False, "Harusnya ekstraksi gagal jika stego-key keliru!"
    except ValueError as e:
        print(f"-> Ekstraksi dengan kunci salah: BERHASIL DIGAGALKAN ({e})")
        
    # 5. Uji Kapasitas Melebihi Batas
    print("\n--- [TEST 3: VALIDASI BATAS KAPASITAS] ---")
    data_kegedean = b"X" * (kapasitas["max_payload_bytes"] + 50)
    try:
        embed_payload(cover_image, data_kegedean, stego_key)
        assert False, "Harusnya ditolak karena melebihi kapasitas!"
    except ValueError as e:
        print(f"-> Uji tolak muatan berlebih: BERHASIL ({e})")


if __name__ == "__main__":
    print("==================================================================")
    print("  MEMULAI VERIFIKASI TAHAP 1 (KRIPTO) & TAHAP 2 (STEGANOGRAFI)")
    print("==================================================================")
    test_crypto_module()
    test_stego_module()
    print("\n==================================================================")
    print("  HASIL: SEMUA PENGUJIAN TAHAP 1 & 2 LOLOS 100% TANPA KENDALA! ")
    print("==================================================================")
