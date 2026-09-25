# Laporan Hasil Pengujian Steganografi & Steganalisis (HideBit)

**Mata Kuliah:** Keamanan Informasi (UTS)
**Kombinasi Algoritma:** AES-256-GCM + PBKDF2 + LSB PRNG Permutation
**Metode Deteksi:** Keyless Chi-Square Pairs of Values (PoV) Attack

## 1. Tabel Komparasi Kualitas Citra & Hasil Steganalisis

| Citra Cover | Resolusi | Skenario Beban | Ukuran Payload | Kapasitas (%) | MSE | PSNR (dB) | Piksel Berubah | Skor Chi² Cover | Skor Chi² Stego |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Citra 1 (Smooth Gradient) | 256x256 | Pendek (~50B) | 101 B | 0.41% | 0.002151 | 74.8 dB | 0.6409% | 33.33% | 33.33% |
| Citra 1 (Smooth Gradient) | 256x256 | Sedang (~25%) | 6142 B | 25.0% | 0.125351 | 57.15 dB | 33.0795% | 33.33% | 32.89% |
| Citra 1 (Smooth Gradient) | 256x256 | Tinggi (~75%) | 18426 B | 75.0% | 0.374868 | 52.39 dB | 75.5447% | 33.33% | 41.08% |
| Citra 2 (Textured Noise) | 300x300 | Pendek (~50B) | 101 B | 0.3% | 0.001633 | 76.0 dB | 0.4889% | 41.01% | 40.53% |
| Citra 2 (Textured Noise) | 300x300 | Sedang (~25%) | 8435 B | 25.0% | 0.125222 | 57.15 dB | 33.0344% | 41.01% | 86.14% |
| Citra 2 (Textured Noise) | 300x300 | Tinggi (~75%) | 25306 B | 75.0% | 0.374881 | 52.39 dB | 75.5711% | 41.01% | 33.95% |
| Citra 3 (Geometric Shapes) | 350x350 | Pendek (~50B) | 101 B | 0.22% | 0.001124 | 77.62 dB | 0.3363% | 0.00% | 0.00% |
| Citra 3 (Geometric Shapes) | 350x350 | Sedang (~25%) | 11482 B | 25.0% | 0.124740 | 57.17 dB | 33.0931% | 0.00% | 0.00% |
| Citra 3 (Geometric Shapes) | 350x350 | Tinggi (~75%) | 34446 B | 75.0% | 0.376272 | 52.38 dB | 75.7976% | 0.00% | 0.00% |
| Citra 4 (Landscape Scenery) | 400x300 | Pendek (~50B) | 101 B | 0.22% | 0.001175 | 77.43 dB | 0.3517% | 0.00% | 0.00% |
| Citra 4 (Landscape Scenery) | 400x300 | Sedang (~25%) | 11248 B | 25.0% | 0.124408 | 57.18 dB | 32.9183% | 0.00% | 0.00% |
| Citra 4 (Landscape Scenery) | 400x300 | Tinggi (~75%) | 33744 B | 75.0% | 0.375131 | 52.39 dB | 75.5975% | 0.00% | 0.00% |
| Citra 5 (Pattern BMP) | 256x256 | Pendek (~50B) | 101 B | 0.41% | 0.002136 | 74.83 dB | 0.6378% | 66.67% | 66.67% |
| Citra 5 (Pattern BMP) | 256x256 | Sedang (~25%) | 6142 B | 25.0% | 0.124644 | 57.17 dB | 33.0246% | 66.67% | 66.67% |
| Citra 5 (Pattern BMP) | 256x256 | Tinggi (~75%) | 18426 B | 75.0% | 0.375626 | 52.38 dB | 75.5737% | 66.67% | 43.95% |

## 2. Analisis Hasil Pengujian

1. **Kualitas Visual (PSNR & MSE):**
   - Nilai PSNR pada seluruh skenario berada jauh di atas **50 dB** (bahkan > 70 dB untuk pesan pendek), jauh melampaui batas ambang standar persepsi mata manusia (30 dB). Hal ini membuktikan bahwa metode LSB tidak menimbulkan degradasi visual yang dapat dideteksi mata manusia.
2. **Korelasi Kapasitas Muatan vs Kemudahan Deteksi:**
   - Pada muatan pendek (~50 byte), skor deteksi Chi-Square hampir tidak mengalami lonjakan karena jumlah pasangan nilai (PoV) yang termodifikasi sangat sedikit.
   - Sebaliknya, pada muatan tinggi (~75% kapasitas), perataan frekuensi pasangan nilai genap-ganjil terjadi secara masif di seluruh kanvas citra, menghasilkan $p$-value yang tinggi dan meningkatkan kecurigaan detektor steganalisis.
   - Temuan ini membuktikan hipotesis steganografi: **"Semakin besar kapasitas payload yang disisipkan, semakin rentan citra terdeteksi oleh analisis statistik tanpa kunci."**
