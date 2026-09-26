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


def _channel_p_value(values: np.ndarray) -> tuple[float, float, int]:
    hist = np.bincount(values.reshape(-1), minlength=256).astype(np.float64)
    even, odd = hist[0::2], hist[1::2]
    totals = even + odd
    used = totals > 0
    # Under the PoV null hypothesis the two counts in each pair are equal.
    chi2 = float(np.sum((even[used] - odd[used]) ** 2 / totals[used]))
    dof = int(np.count_nonzero(used))
    p_value = _regularized_gamma_q(dof / 2.0, chi2 / 2.0) if dof else 1.0
    return chi2, p_value, dof


def analyze_image(image: Image.Image) -> Dict[str, Any]:
    """Return per-channel PoV chi-square results and a heuristic 0–100 score.

    A high p-value means the paired histogram counts are unusually similar,
    which can be consistent with LSB replacement. Natural images can also
    produce this pattern; the score is therefore not a true probability.
    """
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    names = ("red", "green", "blue")
    channels: Dict[str, Dict[str, float | int]] = {}
    p_values = []
    for index, name in enumerate(names):
        chi2, p_value, dof = _channel_p_value(rgb[:, :, index])
        channels[name] = {
            "chi_square": chi2,
            "degrees_of_freedom": dof,
            "p_value": p_value,
        }
        p_values.append(p_value)
    score = round(100.0 * float(np.mean(p_values)), 2)
    return {
        "score": score,
        "interpretation": "heuristic suspicion score; not a calibrated probability",
        "channels": channels,
    }

