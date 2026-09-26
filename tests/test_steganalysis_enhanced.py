"""
tests/test_steganalysis_enhanced.py
===================================
Pengujian Unit & Integrasi Peningkatan Fitur Steganalisis HideBit:
1. Blind Steganalysis + Vonis Forensik (Human-readable Verdict & Narrative)
2. Dual Comparative Steganalysis (Cover vs Stego: PSNR, MSE, Heatmap, Shift Chi-Square)
"""

import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image
import numpy as np

from src.steganalysis import analyze_image, generate_forensic_verdict
from src.metrics import get_image_metrics, calculate_psnr, calculate_mse, generate_difference_heatmap
from src.stego import embed_payload
from src.crypto import encrypt_message

class TestEnhancedSteganalysis(unittest.TestCase):
    def setUp(self):
        # Buat citra cover sintetis (gradien alami)
        arr = np.zeros((100, 100, 3), dtype=np.uint8)
        for y in range(100):
            for x in range(100):
                arr[y, x] = [(x + y) % 256, (x * 2) % 256, (y * 2) % 256]
        self.cover_img = Image.fromarray(arr, mode="RGB")

        # Buat citra stego dengan menyisipkan payload terenkripsi
        key = "StegoAnalysisKeyTest#2024"
        payload = encrypt_message("Uji coba deteksi steganalisis forensik HideBit", key)
        self.stego_img = embed_payload(self.cover_img, payload, key)

    def test_blind_verdict(self):
        # Uji analisis citra cover
        res_cov = analyze_image(self.cover_img)
        self.assertIn("verdict", res_cov)
        self.assertIn("level", res_cov["verdict"])
        self.assertIn("title", res_cov["verdict"])
        self.assertIn("narrative", res_cov["verdict"])
        self.assertIn("recommendation", res_cov["verdict"])

        # Uji analisis citra stego
        res_stg = analyze_image(self.stego_img)
        self.assertIn("verdict", res_stg)
        print("\n[*] Hasil Analisis Citra Stego:")
        print(f"    - Skor Kecurigaan: {res_stg['score']}/100")
        print(f"    - Level Vonis: {res_stg['verdict']['level']}")
        print(f"    - Judul Vonis: {res_stg['verdict']['title']}")
        print(f"    - Narasi Forensik: {res_stg['verdict']['narrative']}")

    def test_dual_comparative_metrics(self):
        metrics = get_image_metrics(self.cover_img, self.stego_img)
        self.assertGreater(metrics["psnr_db"], 40.0)
        self.assertGreater(metrics["changed_pixels"], 0)
        self.assertLess(metrics["pixel_change_percent"], 50.0)

        diff = generate_difference_heatmap(self.cover_img, self.stego_img)
        self.assertEqual(diff.size, self.cover_img.size)
        print("\n[*] Hasil Pengujian Komparasi Dual Image:")
        print(f"    - PSNR: {metrics['psnr_db']} dB")
        print(f"    - MSE: {metrics['mse']}")
        print(f"    - Piksel Berubah: {metrics['changed_pixels']} ({metrics['pixel_change_percent']}%)")

if __name__ == "__main__":
    unittest.main()
