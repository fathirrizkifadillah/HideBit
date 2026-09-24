"""
src/stego.py
============
Modul Steganografi LSB dengan PRNG untuk HideBit (Urutan 2)
- Format Header: [ MAGIC 4-byte: 'HBIT' ] + [ PAYLOAD_LEN 4-byte: uint32 ]
- Penyebaran Bit: PRNG Shuffle (Permutasi Deterministik berdasarkan stego-key)
- Pengecekan Kapasitas: Menolak jika payload melebihi kapasitas citra
- Ekstraksi: Mengambil kembali bit dari posisi PRNG yang sama
"""

import hashlib
from typing import Dict, Any
import numpy as np
from PIL import Image

MAGIC_HEADER = b"HBIT"          # 4 byte identitas steganografi HideBit
HEADER_BYTES = len(MAGIC_HEADER) + 4   # 4 byte magic + 4 byte panjang = 8 byte (64 bit)
HEADER_BITS = HEADER_BYTES * 8


def derive_seed_from_key(stego_key: str) -> int:
    """
    Menghasilkan integer 64-bit sebagai seed deterministik dari stego-key
    menggunakan SHA-256 hash.
    """
    digest = hashlib.sha256(stego_key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big")


def get_image_capacity(img: Image.Image) -> Dict[str, Any]:
    """
    Menghitung kapasitas payload maksimum citra cover pada kanal RGB.
    (1 bit per kanal warna per piksel = 3 bit per piksel).
    """
    width, height = img.size
    total_slots = width * height * 3  # Slot bit yang tersedia (R, G, B)
    
    max_payload_bits = total_slots - HEADER_BITS
    max_payload_bytes = max(0, max_payload_bits // 8)
    
    return {
        "width": width,
        "height": height,
        "total_pixels": width * height,
        "total_slots": total_slots,
        "header_bytes": HEADER_BYTES,
        "max_payload_bytes": max_payload_bytes,
        "max_payload_kb": round(max_payload_bytes / 1024, 2)
    }


def bytes_to_bits(data: bytes) -> np.ndarray:
    """Mengubah byte data menjadi array bit 1D (0 atau 1)."""
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8))


def bits_to_bytes(bits: np.ndarray) -> bytes:
    """Mengubah array bit 1D (0 atau 1) kembali menjadi byte data."""
    return np.packbits(bits).tobytes()


def embed_payload(
    cover_image: Image.Image,
    payload_bytes: bytes,
    stego_key: str
) -> Image.Image:
    """
    Menyisipkan payload_bytes ke citra cover menggunakan LSB teracak PRNG.
    
    Langkah:
    1. Cek kapasitas gambar.
    2. Susun header [MAGIC 4B] + [PANJANG 4B] + [PAYLOAD].
    3. Acak koordinat piksel menggunakan PRNG yang di-seed dari stego_key.
    4. Ganti bit LSB (bit-0) pada piksel terpilih.
    """
    # Pastikan citra dalam format RGB
    img_rgb = cover_image.convert("RGB")
    capacity = get_image_capacity(img_rgb)
    payload_len = len(payload_bytes)
    
    # Validasi batas kapasitas
    if payload_len > capacity["max_payload_bytes"]:
        raise ValueError(
            f"Kapasitas tidak cukup! Payload ({payload_len} B) > Kapasitas Maksimum "
            f"({capacity['max_payload_bytes']} B / {capacity['max_payload_kb']} KB)."
        )
        
    # 1. Susun header: Magic (4B) + Panjang payload (4B uint32 big-endian)
    header = MAGIC_HEADER + payload_len.to_bytes(4, byteorder="big")
    full_data = header + payload_bytes
    bits_to_embed = bytes_to_bits(full_data)
    total_bits = len(bits_to_embed)
    
    # 2. Ambil array piksel dan ratakan (flatten) menjadi 1 dimensi
    pixel_array = np.array(img_rgb, dtype=np.uint8)
    flat_pixels = pixel_array.flatten()
    total_slots = flat_pixels.shape[0]
    
    # 3. Buat permutasi urutan piksel acak berdasarkan stego-key
    seed_int = derive_seed_from_key(stego_key)
    rng = np.random.default_rng(seed_int)
    shuffled_indices = rng.permutation(total_slots)
    
    # 4. Ambil indeks sebanyak bit yang ingin disisipkan
    chosen_indices = shuffled_indices[:total_bits]
    
    # 5. Operasi LSB: Kosongkan bit terakhir (& 0xFE / 254) lalu timpa dengan bit rahasia (| bit)
    flat_pixels[chosen_indices] = (flat_pixels[chosen_indices] & np.uint8(0xFE)) | bits_to_embed.astype(np.uint8)

    
    # 6. Kembalikan array ke bentuk dimensi gambar semula (H, W, 3)
    stego_array = flat_pixels.reshape(pixel_array.shape)
    return Image.fromarray(stego_array, mode="RGB")


def extract_payload(
    stego_image: Image.Image,
    stego_key: str
) -> bytes:
    """
    Mengekstrak payload dari stego_image menggunakan stego_key.
    
    Langkah:
    1. Re-generate urutan acak PRNG yang sama persis memakai stego_key.
    2. Ekstrak 64 bit pertama untuk membaca header.
    3. Cek apakah Magic Header cocok ('HBIT'). Jika beda -> tolak langsung.
    4. Baca sisa bit sesuai panjang payload yang tersimpan di header.
    """
    img_rgb = stego_image.convert("RGB")
    capacity = get_image_capacity(img_rgb)
    
    pixel_array = np.array(img_rgb, dtype=np.uint8)
    flat_pixels = pixel_array.flatten()
    total_slots = flat_pixels.shape[0]
    
    # 1. Bangkitkan permutasi PRNG yang sama dengan stego-key
    seed_int = derive_seed_from_key(stego_key)
    rng = np.random.default_rng(seed_int)
    shuffled_indices = rng.permutation(total_slots)
    
    # 2. Ekstrak Header (64 bit pertama)
    header_indices = shuffled_indices[:HEADER_BITS]
    header_bits = flat_pixels[header_indices] & 1
    header_bytes = bits_to_bytes(header_bits)
    
    magic = header_bytes[:4]
    if magic != MAGIC_HEADER:
        raise ValueError("Stego-key salah atau citra tidak mengandung pesan rahasia HideBit!")
        
    payload_len = int.from_bytes(header_bytes[4:8], byteorder="big")
    if payload_len <= 0 or payload_len > capacity["max_payload_bytes"]:
        raise ValueError(f"Data panjang payload rusak ({payload_len} byte).")
        
    # 3. Ekstrak Payload Pesan
    total_payload_bits = payload_len * 8
    payload_indices = shuffled_indices[HEADER_BITS : HEADER_BITS + total_payload_bits]
    
    payload_bits = flat_pixels[payload_indices] & 1
    return bits_to_bytes(payload_bits)
