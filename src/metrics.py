"""
src/metrics.py
==============
Modul Evaluasi Kualitas Citra & Analisis Histogram
- Metrik Kualitas: MSE (Mean Squared Error), PSNR (Peak Signal-to-Noise Ratio), & Detail Statistik Piksel
- Difference Heatmap: Visualisasi pendaran koordinat bit LSB teracak (PRNG) dengan dilatasi adaptif
- Analisis Histogram: Ekstraksi distribusi frekuensi RGB
- Konversi Citra: Serialisasi PIL Image ke Base64 Data URL untuk antarmuka web
"""

import io
import base64
import math
from typing import Dict, Any, Tuple
import numpy as np
from PIL import Image, ImageFilter


def calculate_mse(cover: Image.Image, stego: Image.Image) -> float:
    """
    Menghitung Mean Squared Error (MSE) antara cover image dan stego image.
    Formula: MSE = (1 / (3 * H * W)) * sum((I_cover - I_stego)^2)
    """
    cov_arr = np.asarray(cover.convert("RGB"), dtype=np.float64)
    stg_arr = np.asarray(stego.convert("RGB"), dtype=np.float64)

    if cov_arr.shape != stg_arr.shape:
        raise ValueError("Dimensi cover image dan stego image harus sama persis.")

    mse = float(np.mean((cov_arr - stg_arr) ** 2))
    return mse


def calculate_psnr(cover: Image.Image, stego: Image.Image) -> float:
    """
    Menghitung Peak Signal-to-Noise Ratio (PSNR) dalam satuan desibel (dB).
    Formula: PSNR = 10 * log10(255^2 / MSE)
    Nilai PSNR > 30 dB umumnya tidak dapat dibedakan oleh mata manusia.
    """
    mse = calculate_mse(cover, stego)
    if mse == 0.0:
        return 99.0  # Identik sempurna (praktis tak terhingga)
    
    psnr = 10.0 * math.log10((255.0 ** 2) / mse)
    return round(psnr, 2)


def get_image_metrics(cover: Image.Image, stego: Image.Image) -> Dict[str, Any]:
    """
    Mengembalikan ringkasan statistik komparasi mendalam antara cover vs stego:
    - MSE & PSNR
    - Total piksel, piksel identik (unchanged), dan piksel berubah
    - Sebaran perubahan per kanal warna R, G, B
    - Maksimum delta nilai piksel (selalu 1 pada steganografi LSB)
    """
    cov_rgb = np.asarray(cover.convert("RGB"), dtype=np.uint8)
    stg_rgb = np.asarray(stego.convert("RGB"), dtype=np.uint8)

    diff = np.abs(cov_rgb.astype(np.int16) - stg_rgb.astype(np.int16))
    changed_pixels = int(np.count_nonzero(np.any(diff > 0, axis=2)))
    total_pixels = cov_rgb.shape[0] * cov_rgb.shape[1]
    unchanged_pixels = total_pixels - changed_pixels

    changed_r = int(np.count_nonzero(diff[:, :, 0] > 0))
    changed_g = int(np.count_nonzero(diff[:, :, 1] > 0))
    changed_b = int(np.count_nonzero(diff[:, :, 2] > 0))
    total_channel_slots = total_pixels * 3
    changed_channel_slots = changed_r + changed_g + changed_b

    mse = calculate_mse(cover, stego)
    psnr = calculate_psnr(cover, stego)

    return {
        "mse": round(mse, 6),
        "psnr_db": psnr,
        "changed_pixels": changed_pixels,
        "total_pixels": total_pixels,
        "unchanged_pixels": unchanged_pixels,
        "unchanged_percent": round((unchanged_pixels / total_pixels) * 100, 3) if total_pixels > 0 else 100.0,
        "pixel_change_percent": round((changed_pixels / total_pixels) * 100, 4) if total_pixels > 0 else 0.0,
        "channel_changes": {
            "r": changed_r,
            "g": changed_g,
            "b": changed_b,
            "total_slots": total_channel_slots,
            "changed_slots": changed_channel_slots
        },
        "max_delta": int(np.max(diff)) if diff.size > 0 else 0,
    }


def get_histogram_data(image: Image.Image) -> Dict[str, list]:
    """
    Menghitung histogram frekuensi 256 nilai intensitas per kanal R, G, B.
    """
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    return {
        "r": np.bincount(rgb[:, :, 0].flatten(), minlength=256).tolist(),
        "g": np.bincount(rgb[:, :, 1].flatten(), minlength=256).tolist(),
        "b": np.bincount(rgb[:, :, 2].flatten(), minlength=256).tolist(),
    }


def image_to_base64(image: Image.Image, format_type: str = "PNG") -> str:
    """
    Mengubah PIL Image menjadi Base64 Data URL string agar bisa dirender langsung di HTML <img>.
    """
    buffer = io.BytesIO()
    image.save(buffer, format=format_type)
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    mime = "image/png" if format_type.upper() == "PNG" else "image/jpeg"
    return f"data:{mime};base64,{encoded}"


def generate_difference_heatmap(cover: Image.Image, stego: Image.Image) -> Image.Image:
    """
    Menghasilkan citra selisih (Difference Map / Residual) berdaya visual tinggi:
    1. Latar belakang: siluet redup citra asli agar bentuk objek/foto tetap terbaca.
    2. Bit-bit LSB termodifikasi: didilatasi adaptif (diameter 5-9 px) dengan warna
       neon cyan elektrik (0, 255, 220) dan titik pusat putih berpendar.
    Sehingga perbedaan LSB yang hanya sedikit tetap terlihat sangat kontras dan jelas
    di layar monitor walaupun resolusi citra sangat besar.
    """
    cov_rgb = np.asarray(cover.convert("RGB"), dtype=np.int16)
    stg_rgb = np.asarray(stego.convert("RGB"), dtype=np.int16)

    h, w = cov_rgb.shape[:2]
    diff = np.abs(cov_rgb - stg_rgb)
    changed_mask_2d = np.any(diff > 0, axis=2).astype(np.uint8) * 255

    # Ukuran radius dilatasi adaptif berdasarkan resolusi
    filter_size = max(5, min(13, int(max(w, h) / 120) * 2 + 1))
    
    mask_img = Image.fromarray(changed_mask_2d, mode="L")
    dilated_mask = mask_img.filter(ImageFilter.MaxFilter(size=filter_size))
    dilated_arr = np.asarray(dilated_mask) > 0

    # Siluet redup citra cover (kecerahan ~15%)
    base = (cov_rgb * 0.15).astype(np.uint8)

    # Titik pendaran neon cyan
    base[dilated_arr] = [0, 255, 215]
    # Inti tengah putih terang
    base[changed_mask_2d > 0] = [255, 255, 255]

    return Image.fromarray(base, mode="RGB")
