"""Keyless LSB steganalysis helpers and keyed message extraction.

The detector uses the classical pairs-of-values (PoV) chi-square idea. LSB
replacement tends to equalize counts for values (0, 1), (2, 3), etc. Its
score is a heuristic indicator, not a calibrated probability that an image
contains hidden data.
"""

from __future__ import annotations

import math
from typing import Any, Dict

import numpy as np
from PIL import Image

from .crypto import decrypt_message, decrypt_payload_data
from .stego import extract_payload


def extract_message(stego_image: Image.Image, stego_key: str) -> str:
    """Extract and decrypt the hidden UTF-8 message using the supplied key."""
    if not isinstance(stego_key, str) or not stego_key:
        raise ValueError("Stego-key harus berupa string dan tidak boleh kosong.")
    payload = extract_payload(stego_image, stego_key)
    return decrypt_message(payload, stego_key)


def extract_payload_data(stego_image: Image.Image, stego_key: str) -> Dict[str, Any]:
    """Extract and decrypt either a text message or a hidden binary file."""
    if not isinstance(stego_key, str) or not stego_key:
        raise ValueError("Stego-key harus berupa string dan tidak boleh kosong.")
    payload = extract_payload(stego_image, stego_key)
    return decrypt_payload_data(payload, stego_key)


def lsb_plane(image: Image.Image, channel: int = 0) -> Image.Image:
    """Return one RGB channel's LSBs as a grayscale black/white image."""
    if channel not in (0, 1, 2):
        raise ValueError("Channel harus 0 (R), 1 (G), atau 2 (B).")
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    plane = (rgb[:, :, channel] & 1) * 255
    return Image.fromarray(plane.astype(np.uint8), mode="L")


def _regularized_gamma_q(a: float, x: float) -> float:
    """Regularized upper incomplete gamma, used for chi-square survival p."""
    if x <= 0:
        return 1.0
    if a <= 0:
        return 0.0
    eps, tiny, max_iter = 1e-14, 1e-300, 10000
    gln = math.lgamma(a)
    if x < a + 1.0:
        ap = a
        term = total = 1.0 / a
        for _ in range(max_iter):
            ap += 1.0
            term *= x / ap
            total += term
            if abs(term) < abs(total) * eps:
                break
        p = total * math.exp(-x + a * math.log(x) - gln)
        return min(1.0, max(0.0, 1.0 - p))

    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / max(b, tiny)
    h = d
    for i in range(1, max_iter + 1):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return min(1.0, max(0.0, math.exp(-x + a * math.log(x) - gln) * h))


def _channel_p_value(values: np.ndarray) -> tuple[float, float, int, float, float]:
    """
    Menghitung nilai statistik Chi-Square PoV (Westfeld 1999), p-value teoretis sejati,
    rasio kesetimbangan pasangan PoV, dan indeks anomali heuristik kanal.
    """
    flat = values.reshape(-1)
    n = len(flat)

    # 1. Histogram global & Chi-Square klasik PoV (Westfeld 1999)
    hist = np.bincount(flat, minlength=256).astype(np.float64)
    even, odd = hist[0::2], hist[1::2]
    totals = even + odd
    used = totals > 0
    dof = int(np.count_nonzero(used))
    
    # Formula Chi-Square PoV: sum((even - odd)^2 / totals)
    chi2 = float(np.sum((even[used] - odd[used]) ** 2 / totals[used])) if dof else 0.0
    
    # P-value teoretis sejati dari fungsi distribusi Chi-Square kumulatif: P(Chi2 >= chi2_obs)
    # Pada citra alami berukuran besar (ratusan ribu piksel), chi2 >> dof, sehingga theoretical_p ~ 0.0000
    theoretical_p = _regularized_gamma_q(dof / 2.0, chi2 / 2.0) if dof else 0.0
    if math.isnan(theoretical_p) or theoretical_p < 1e-12:
        theoretical_p = 0.0

    # 2. Local block Chi-Square (Westfeld windowing 48 blok @ 512 piksel)
    bsize = 512
    step = max(1, (n - bsize) // 48)
    local_p_list = []
    for i in range(0, n - bsize + 1, step):
        blk = flat[i:i+bsize]
        h_b = np.bincount(blk, minlength=256).astype(float)
        e_b, o_b = h_b[0::2], h_b[1::2]
        t_b = e_b + o_b
        ub = t_b > 0
        df_b = int(np.count_nonzero(ub))
        if df_b >= 6:
            c2_b = float(np.sum((e_b[ub] - o_b[ub])**2 / t_b[ub]))
            p_b = _regularized_gamma_q(df_b / 2.0, c2_b / 2.0)
            local_p_list.append(p_b)
    local_p = float(np.mean(local_p_list)) if local_p_list else 0.0

    # 3. Metrik kesetimbangan pasangan PoV (PoV Pair Symmetry / Balance Ratio)
    # Menghitung seberapa seimbang frekuensi genap dan ganjil secara empiris (0.0 - 1.0)
    valid_pairs = totals >= 8
    if np.any(valid_pairs):
        asym = float(np.mean(np.abs(even[valid_pairs] - odd[valid_pairs]) / totals[valid_pairs]))
        balance = max(0.0, min(1.0, 1.0 - asym))
    else:
        balance = 0.5

    # 4. Entropi bidang bit-0 LSB
    b0 = (flat & 1)
    p1 = float(np.mean(b0))
    p0 = 1.0 - p1
    ent = float(-(p0 * np.log2(p0) + p1 * np.log2(p1))) if (0 < p0 < 1) else 0.0

    # Indeks anomali heuristik kanal (0.0 - 1.0)
    channel_anomaly = max(theoretical_p, 0.40 * local_p + 0.35 * balance + 0.25 * ent)
    return chi2, theoretical_p, dof, balance, channel_anomaly


def analyze_image(image: Image.Image) -> Dict[str, Any]:
    """
    Melakukan steganalisis komprehensif: Chi-Square PoV matematis,
    rasio simetri pasangan PoV, dan skor kecurigaan heuristik multi-parameter.
    """
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    names = ("red", "green", "blue")
    channels: Dict[str, Dict[str, Any]] = {}
    anomaly_scores = []
    
    for index, name in enumerate(names):
        chi2, theo_p, dof, balance, anomaly = _channel_p_value(rgb[:, :, index])
        p_disp = "< 0.0001" if theo_p < 0.0001 else f"{theo_p:.4f}"
        channels[name] = {
            "chi_square": round(chi2, 2),
            "degrees_of_freedom": dof,
            "p_value": theo_p,
            "p_value_display": p_disp,
            "balance_percent": round(balance * 100, 2),
            "anomaly_index": round(anomaly * 100, 2),
            "status": "Anomali" if anomaly >= 0.65 else ("Moderat" if anomaly >= 0.35 else "Normal")
        }
        anomaly_scores.append(anomaly)
        
    score = round(100.0 * float(np.mean(anomaly_scores)), 2)
    verdict = generate_forensic_verdict(score, channels)
    return {
        "score": score,
        "interpretation": "heuristic suspicion score; composite multi-parameter anomaly index",
        "channels": channels,
        "verdict": verdict,
    }


def generate_forensic_verdict(score: float, channels: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Generate human-readable forensic conclusion and narrative from Chi-Square PoV metrics."""
    suspicious_channels = [
        name for name, data in channels.items() 
        if float(data.get("anomaly_index", 0.0)) >= 60.0 or float(data.get("p_value", 0.0)) >= 0.50
    ]
    
    if score >= 65.0 or len(suspicious_channels) >= 2:
        level = "ANOMALY_DETECTED"
        badge_label = "ANOMALI LSB TERDETEKSI"
        status_color = "danger"
        title = "Indikasi Anomali Distribusi Bit LSB"
        narrative = (
            f"Analisis statistik Pasangan Nilai (Pairs of Values) dan uji blok lokal mengindikasikan deviasi yang signifikan "
            f"pada kanal: {', '.join([c.capitalize() for c in suspicious_channels]) if suspicious_channels else 'seluruh kanal'}. "
            f"Karakteristik ini konsisten dengan modifikasi nilai piksel terorganisir pada bidang bit LSB (Bit-0)."
        )
        recommendation = "Citra menunjukkan pola yang tidak lazim untuk citra alami murni. Disarankan melakukan uji ekstraksi pada tab Reveal Message atau melakukan komparasi langsung jika memiliki citra asli."
    elif score >= 35.0 or len(suspicious_channels) == 1:
        level = "SUSPICIOUS"
        badge_label = "INDIKASI MODERAT"
        status_color = "warning"
        title = "Pola Statistik Ambigu / Perlu Investigasi"
        narrative = (
            f"Ditemukan fluktuasi distribusi lokal pada salah satu kanal warna, namun nilai Chi-Square global tetap berada di rentang wajar citra alami. "
            f"Pada teknik steganografi LSB teracak (PRNG) dengan muatan kecil, pola global tetap tampak wajar karena bit disebar tipis ke seluruh citra."
        )
        recommendation = "Lakukan inspeksi visual pada bidang LSB (Bit-0) di bawah atau gunakan Mode Komparasi (Cover vs Stego) untuk kepastian mutlak."
    else:
        level = "CLEAN"
        badge_label = "CITRA BERSIH / ALAMI"
        status_color = "safe"
        title = "Tidak Terdeteksi Anomali LSB Global"
        narrative = (
            f"Frekuensi pasangan nilai piksel (PoV) terdistribusi heterogen sebagaimana karakteristik citra alami normal (Chi-Square tinggi, p-value < 0.0001). "
            f"Tidak ditemukan indikasi substitusi LSB sekuensial berskala besar pada histogram global."
        )
        recommendation = "Citra berada dalam parameter distribusi normal. Perhatikan bahwa steganografi LSB-PRNG dengan muatan sangat kecil (<2%) membutuhkan Mode Komparasi dengan citra asli untuk deteksi pasti."

    return {
        "level": level,
        "badge_label": badge_label,
        "status_color": status_color,
        "title": title,
        "narrative": narrative,
        "recommendation": recommendation,
        "high_anomaly_channels": suspicious_channels,
    }

