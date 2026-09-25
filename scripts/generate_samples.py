"""
scripts/generate_samples.py
===========================
Menghasilkan 5 sampel citra cover dengan variasi tekstur dan resolusi
untuk pengujian dan dataset laporan UTS Keamanan Informasi.
"""

import os
import numpy as np
from PIL import Image, ImageDraw

os.makedirs("sample_images", exist_ok=True)

def create_samples():
    print("[*] Menghasilkan 5 sampel citra uji...")

    # 1. Citra 1: Gradien Halus (Smooth Gradient) - 256x256
    w, h = 256, 256
    arr1 = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            arr1[y, x] = [int(x / w * 255), int(y / h * 255), int((x + y) / (w + h) * 255)]
    img1 = Image.fromarray(arr1, mode="RGB")
    img1.save("sample_images/citra1_gradient.png")
    print("  -> sample_images/citra1_gradient.png (256x256)")

    # 2. Citra 2: Tekstur Abstrak / Noise Lembut (Textured Noise) - 300x300
    np.random.seed(42)
    base = np.random.randint(80, 180, (300, 300, 3), dtype=np.uint8)
    img2 = Image.fromarray(base, mode="RGB")
    img2.save("sample_images/citra2_texture.png")
    print("  -> sample_images/citra2_texture.png (300x300)")

    # 3. Citra 3: Ilustrasi Geometris (Shapes & Contours) - 350x350
    img3 = Image.new("RGB", (350, 350), color=(240, 245, 245))
    draw3 = ImageDraw.Draw(img3)
    draw3.rectangle([30, 30, 180, 180], fill=(45, 120, 180), outline=(20, 60, 100), width=3)
    draw3.ellipse([150, 120, 320, 290], fill=(220, 90, 80), outline=(150, 40, 30), width=3)
    draw3.polygon([(60, 300), (180, 220), (220, 330)], fill=(70, 175, 120))
    img3.save("sample_images/citra3_geometric.png")
    print("  -> sample_images/citra3_geometric.png (350x350)")

    # 4. Citra 4: Lanskap Digital Sintetis (Landscape Scenery) - 400x300
    img4 = Image.new("RGB", (400, 300), color=(135, 206, 235)) # Sky
    draw4 = ImageDraw.Draw(img4)
    draw4.ellipse([280, 30, 350, 100], fill=(255, 220, 100)) # Sun
    draw4.polygon([(0, 300), (120, 140), (260, 300)], fill=(80, 130, 75)) # Mountain 1
    draw4.polygon([(160, 300), (290, 170), (400, 300)], fill=(65, 110, 60)) # Mountain 2
    draw4.rectangle([0, 250, 400, 300], fill=(50, 160, 90)) # Field
    img4.save("sample_images/citra4_landscape.png")
    print("  -> sample_images/citra4_landscape.png (400x300)")

    # 5. Citra 5: Citra Format BMP Tanpa Kompresi (Lossless BMP) - 256x256
    arr5 = np.zeros((256, 256, 3), dtype=np.uint8)
    for y in range(256):
        arr5[y, :, 0] = y
        arr5[:, y, 1] = 255 - y
        arr5[y, :, 2] = (y * 2) % 256
    img5 = Image.fromarray(arr5, mode="RGB")
    img5.save("sample_images/citra5_pattern.bmp")
    print("  -> sample_images/citra5_pattern.bmp (256x256 BMP)")

    print("[V] 5 Citra Uji Berhasil Disiapkan di folder sample_images/!")

if __name__ == "__main__":
    create_samples()
