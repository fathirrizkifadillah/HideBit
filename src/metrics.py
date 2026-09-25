"""
src/metrics.py
==============
Modul Evaluasi Kualitas Citra & Analisis Histogram
- Metrik Kualitas: MSE (Mean Squared Error) dan PSNR (Peak Signal-to-Noise Ratio)
- Analisis Histogram: Ekstraksi distribusi frekuensi RGB
- Konversi Citra: Serialisasi PIL Image ke Base64 Data URL untuk antarmuka web
"""

import io
import base64
import math
from typing import Dict, Any, Tuple
import numpy as np
from PIL import Image


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
    Mengembalikan ringkasan komparasi kualitas citra cover vs stego.
    """
    cov_rgb = np.asarray(cover.convert("RGB"), dtype=np.uint8)
    stg_rgb = np.asarray(stego.convert("RGB"), dtype=np.uint8)

    diff = np.abs(cov_rgb.astype(np.int16) - stg_rgb.astype(np.int16))
    changed_pixels = int(np.count_nonzero(np.any(diff > 0, axis=2)))
    total_pixels = cov_rgb.shape[0] * cov_rgb.shape[1]
    
    mse = calculate_mse(cover, stego)
    psnr = calculate_psnr(cover, stego)

    return {
        "mse": round(mse, 6),
        "psnr_db": psnr,
        "changed_pixels": changed_pixels,
        "total_pixels": total_pixels,
        "pixel_change_percent": round((changed_pixels / total_pixels) * 100, 4) if total_pixels > 0 else 0.0,
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
