"""
src/crypto.py
=============
Modul Kriptografi & Kompresi untuk HideBit
- Dukungan Fleksibel: Menyembunyikan Pesan Teks (UTF-8) atau Berkas Biner (PDF, DOCX, ZIP, TXT, dll.)
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

TAG_TYPE_TEXT = b"T"
TAG_TYPE_FILE = b"F"


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


def get_compression_info(data_bytes: bytes) -> Dict[str, Any]:
    """
    Menghitung estimasi efisiensi kompresi zlib pada data bytes.
    """
    compressed = zlib.compress(data_bytes, level=9)
    raw_len = len(data_bytes)
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


def encrypt_payload_data(data: bytes, data_type: str = "text", filename: str = "", password: str = "") -> bytes:
    """
    Membungkus data (teks atau berkas biner), mengompresi secara adaptif (zlib),
    lalu mengenkripsi menggunakan AES-256-GCM.
    
    Format Envelope:
    - Text: [ b'T' (1B) ] + [ DATA_BYTES ]
    - File: [ b'F' (1B) ] + [ FN_LEN (1B uint8) ] + [ FILENAME ] + [ FILE_DATA_BYTES ]
    
    Format Payload Akhir:
    [ SALT (16B) ] + [ NONCE (12B) ] + [ CIPHERTEXT(FLAG + ENVELOPE) + AUTH TAG (16B) ]
    """
    if not data:
        raise ValueError("Data rahasia tidak boleh kosong.")
    if not password:
        raise ValueError("Stego-key tidak boleh kosong.")

    # 1. Susun Envelope sesuai tipe data
    if data_type == "file":
        safe_fn = (filename or "secret_file.bin").encode("utf-8")[:255]
        envelope = TAG_TYPE_FILE + bytes([len(safe_fn)]) + safe_fn + data
    else:
        envelope = TAG_TYPE_TEXT + data

    # 2. Kompresi adaptif zlib
    compressed_bytes = zlib.compress(envelope, level=9)
    if len(compressed_bytes) < len(envelope):
        body = FLAG_ZLIB_COMPRESSED + compressed_bytes
    else:
        body = FLAG_UNCOMPRESSED + envelope

    # 3. Parameter acak kriptografi
    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    key = derive_key(password, salt)

    # 4. Enkripsi AES-256-GCM
    aesgcm = AESGCM(key)
    ciphertext_with_tag = aesgcm.encrypt(nonce, body, None)
    return salt + nonce + ciphertext_with_tag


def decrypt_payload_data(payload: bytes, password: str) -> Dict[str, Any]:
    """
    Mendekripsi payload terenkripsi menggunakan AES-256-GCM,
    mendekompresi zlib, lalu mendeteksi apakah isinya Teks atau Berkas Biner.
    
    Returns:
        Dict:
          {"type": "text", "text": str, "size": int}
          or
          {"type": "file", "filename": str, "data": bytes, "size": int}
    """
    min_length = SALT_SIZE + NONCE_SIZE + 16
    if len(payload) < min_length:
        raise ValueError("Payload terenkripsi terlalu pendek atau tidak valid.")
        
    salt = payload[:SALT_SIZE]
    nonce = payload[SALT_SIZE:SALT_SIZE + NONCE_SIZE]
    ciphertext_with_tag = payload[SALT_SIZE + NONCE_SIZE:]
    
    key = derive_key(password, salt)
    aesgcm = AESGCM(key)
    try:
        decrypted_body = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
    except InvalidTag:
        raise ValueError("Dekripsi GAGAL: Stego-key salah atau data telah dimanipulasi!")

    # 1. Cek flag kompresi
    flag = decrypted_body[:1]
    raw_envelope = decrypted_body[1:]

    if flag == FLAG_ZLIB_COMPRESSED:
        try:
            envelope = zlib.decompress(raw_envelope)
        except Exception:
            raise ValueError("Dekripsi GAGAL: Dekompresi zlib gagal/data rusak.")
    elif flag == FLAG_UNCOMPRESSED:
        envelope = raw_envelope
    else:
        envelope = decrypted_body

    # 2. Cek tipe isi envelope (Teks atau Berkas)
    type_tag = envelope[:1]
    if type_tag == TAG_TYPE_FILE:
        fn_len = envelope[1]
        filename = envelope[2:2 + fn_len].decode("utf-8", errors="replace")
        file_data = envelope[2 + fn_len:]
        return {
            "type": "file",
            "filename": filename,
            "data": file_data,
            "size": len(file_data)
        }
    elif type_tag == TAG_TYPE_TEXT:
        text = envelope[1:].decode("utf-8", errors="replace")
        return {
            "type": "text",
            "text": text,
            "size": len(envelope) - 1
        }
    else:
        # Fallback kompatibilitas versi awal
        try:
            return {
                "type": "text",
                "text": envelope.decode("utf-8"),
                "size": len(envelope)
            }
        except UnicodeDecodeError:
            raise ValueError("Dekripsi GAGAL: Format payload tidak dikenali.")


def encrypt_message(plaintext: str, password: str) -> bytes:
    """Wrapper untuk enkripsi teks string (kompatibilitas mundur)."""
    return encrypt_payload_data(plaintext.encode("utf-8"), data_type="text", filename="", password=password)


def decrypt_message(payload: bytes, password: str) -> str:
    """Wrapper untuk dekripsi teks string (kompatibilitas mundur)."""
    res = decrypt_payload_data(payload, password)
    if res["type"] == "text":
        return res["text"]
    return f"[Berkas Terlampir: {res['filename']} ({res['size']} byte)]"
