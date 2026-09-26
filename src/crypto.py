"""
src/crypto.py
=============
Modul Kriptografi & Kompresi untuk HideBit
- Kompresi Data: zlib (Deflate level 9) adaptif sebelum enkripsi
- Algoritma Enkripsi: AES-256-GCM (Authenticated Encryption with Associated Data)
- Derivasi Kunci: PBKDF2-HMAC-SHA256 (100.000 iterasi dengan Salt acak 16 byte)
- Fitur Integritas: Otomatis menolak jika stego-key salah atau data rusak
"""

import os
import zlib
from typing import Tuple, Dict, Any

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.exceptions import InvalidTag
except ImportError:
    raise ImportError(
        "Library 'cryptography' belum terpasang. Jalankan: pip install cryptography"
    )

SALT_SIZE = 16          # 128-bit acak untuk mencegah serangan Rainbow Table
NONCE_SIZE = 12         # 96-bit nonce standar yang aman untuk AES-GCM
PBKDF2_ITERATIONS = 100_000

FLAG_UNCOMPRESSED = b"\x00"
FLAG_ZLIB_COMPRESSED = b"\x01"


def derive_key(password: str, salt: bytes) -> bytes:
    """
    Menghasilkan kunci 256-bit (32 byte) dari password/stego-key string
    menggunakan algoritma PBKDF2 dengan HMAC-SHA256.
    """
    if not isinstance(password, str) or not password:
        raise ValueError("Stego-key / password harus berupa string dan tidak boleh kosong.")
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,               # 32 byte = 256 bit untuk AES-256
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def get_compression_info(plaintext: str) -> Dict[str, Any]:
    """
    Menghitung estimasi efisiensi kompresi zlib pada plaintext.
    """
    raw_bytes = plaintext.encode("utf-8")
    compressed = zlib.compress(raw_bytes, level=9)
    raw_len = len(raw_bytes)
    comp_len = len(compressed)

    if comp_len < raw_len:
        saved_bytes = raw_len - comp_len
        ratio = round((saved_bytes / raw_len) * 100, 1)
        return {
            "is_compressed": True,
            "raw_bytes": raw_len,
            "compressed_bytes": comp_len,
            "saved_bytes": saved_bytes,
            "ratio_percent": ratio
        }
    return {
        "is_compressed": False,
        "raw_bytes": raw_len,
        "compressed_bytes": raw_len,
        "saved_bytes": 0,
        "ratio_percent": 0.0
    }


def encrypt_message(plaintext: str, password: str) -> bytes:
    """
    Kompresi teks (zlib) lalu enkripsi menggunakan AES-256-GCM.
    
    Format payload yang dihasilkan:
    [ SALT (16 byte) ] + [ NONCE (12 byte) ] + [ CIPHERTEXT(FLAG + DATA) + AUTH TAG (16 byte) ]
    
    Returns:
        bytes: Data terenkripsi siap disisipkan ke citra.
    """
    if not plaintext:
        raise ValueError("Pesan rahasia tidak boleh kosong.")
    if not password:
        raise ValueError("Stego-key tidak boleh kosong.")

    raw_bytes = plaintext.encode("utf-8")
    compressed_bytes = zlib.compress(raw_bytes, level=9)

    # 1. Kompresi adaptif: hanya pakai zlib jika ukuran lebih kecil
    if len(compressed_bytes) < len(raw_bytes):
        body = FLAG_ZLIB_COMPRESSED + compressed_bytes
    else:
        body = FLAG_UNCOMPRESSED + raw_bytes

    # 2. Generate salt dan nonce acak untuk setiap enkripsi
    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    
    # 3. Turunkan kunci simetris 256-bit dari password
    key = derive_key(password, salt)
    
    # 4. Enkripsi pesan dengan AES-GCM (otomatis menyertakan 16 byte Auth Tag di akhir)
    aesgcm = AESGCM(key)
    ciphertext_with_tag = aesgcm.encrypt(nonce, body, None)
    
    # 5. Gabungkan menjadi satu kesatuan payload bytes
    return salt + nonce + ciphertext_with_tag


def decrypt_message(payload: bytes, password: str) -> str:
    """
    Mendekripsi payload terenkripsi menggunakan AES-256-GCM
    lalu mendekompresi payload jika dikompresi.
    
    Raises:
        ValueError: Jika password salah atau data bit rusak/termodifikasi.
    """
    min_length = SALT_SIZE + NONCE_SIZE + 16  # Minimal harus ada salt + nonce + tag
    if len(payload) < min_length:
        raise ValueError("Payload terenkripsi terlalu pendek atau tidak valid.")
        
    # 1. Pecah payload sesuai strukturnya
    salt = payload[:SALT_SIZE]
    nonce = payload[SALT_SIZE:SALT_SIZE + NONCE_SIZE]
    ciphertext_with_tag = payload[SALT_SIZE + NONCE_SIZE:]
    
    # 2. Turunkan kunci menggunakan salt yang sama
    key = derive_key(password, salt)
    
    # 3. Dekripsi dan verifikasi keaslian (Auth Tag)
    aesgcm = AESGCM(key)
    try:
        decrypted_body = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
    except InvalidTag:
        raise ValueError("Dekripsi GAGAL: Stego-key salah atau data telah dimanipulasi!")

    # 4. Cek flag kompresi
    flag = decrypted_body[:1]
    data = decrypted_body[1:]

    if flag == FLAG_ZLIB_COMPRESSED:
        try:
            decompressed = zlib.decompress(data)
            return decompressed.decode("utf-8")
        except Exception:
            raise ValueError("Dekripsi GAGAL: Dekompresi data korup.")
    elif flag == FLAG_UNCOMPRESSED:
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("Dekripsi GAGAL: Data hasil dekripsi bukan teks UTF-8 yang valid.")
    else:
        # Fallback kompatibilitas jika payload lama tanpa header flag
        try:
            return decrypted_body.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("Dekripsi GAGAL: Format payload tidak dikenali.")
