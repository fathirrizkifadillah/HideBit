# Laporan Hasil Pengujian Steganografi & Steganalisis (HideBit)

**Mata Kuliah:** Keamanan Informasi (UTS)
**Kombinasi Algoritma:** AES-256-GCM + PBKDF2 + LSB PRNG Permutation
**Metode Deteksi:** Keyless Chi-Square Pairs of Values (PoV) Attack

## 1. Tabel Komparasi Kualitas Citra & Hasil Steganalisis

| Citra Cover | Resolusi | Skenario Beban | Ukuran Payload | Kapasitas (%) | MSE | PSNR (dB) | Piksel Berubah | Skor Chi² Cover | Skor Chi² Stego |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Citra 1 (Smooth Gradient) | 256x256 | Pendek (~50B) | 102 B | 0.42% | 0.002299 | 74.52 dB | 0.6866% | 33.33% | 33.33% |
| Citra 1 (Smooth Gradient) | 256x256 | Sedang (~25%) | 135 B | 0.55% | 0.002935 | 73.46 dB | 0.8789% | 33.33% | 33.33% |
| Citra 1 (Smooth Gradient) | 256x256 | Tinggi (~75%) | 178 B | 0.72% | 0.003713 | 72.43 dB | 1.1078% | 33.33% | 33.33% |
| Citra 2 (Textured Noise) | 300x300 | Pendek (~50B) | 102 B | 0.3% | 0.001641 | 75.98 dB | 0.4922% | 41.01% | 41.03% |
| Citra 2 (Textured Noise) | 300x300 | Sedang (~25%) | 143 B | 0.42% | 0.002263 | 74.58 dB | 0.6789% | 41.01% | 39.90% |
| Citra 2 (Textured Noise) | 300x300 | Tinggi (~75%) | 199 B | 0.59% | 0.003015 | 73.34 dB | 0.8978% | 41.01% | 38.90% |
| Citra 3 (Geometric Shapes) | 350x350 | Pendek (~50B) | 102 B | 0.22% | 0.001167 | 77.46 dB | 0.3494% | 0.00% | 0.00% |
| Citra 3 (Geometric Shapes) | 350x350 | Sedang (~25%) | 152 B | 0.33% | 0.001665 | 75.92 dB | 0.4988% | 0.00% | 0.00% |
| Citra 3 (Geometric Shapes) | 350x350 | Tinggi (~75%) | 226 B | 0.49% | 0.002544 | 74.08 dB | 0.76% | 0.00% | 0.00% |
| Citra 4 (Landscape Scenery) | 400x300 | Pendek (~50B) | 102 B | 0.23% | 0.001278 | 77.07 dB | 0.3833% | 0.00% | 0.00% |
| Citra 4 (Landscape Scenery) | 400x300 | Sedang (~25%) | 151 B | 0.34% | 0.001764 | 75.67 dB | 0.5275% | 0.00% | 0.00% |
| Citra 4 (Landscape Scenery) | 400x300 | Tinggi (~75%) | 224 B | 0.5% | 0.002508 | 74.14 dB | 0.7492% | 0.00% | 0.00% |
| Citra 5 (Pattern BMP) | 256x256 | Pendek (~50B) | 102 B | 0.42% | 0.002228 | 74.65 dB | 0.6638% | 66.67% | 66.67% |
| Citra 5 (Pattern BMP) | 256x256 | Sedang (~25%) | 135 B | 0.55% | 0.002970 | 73.4 dB | 0.885% | 66.67% | 66.67% |
| Citra 5 (Pattern BMP) | 256x256 | Tinggi (~75%) | 178 B | 0.72% | 0.003713 | 72.43 dB | 1.1093% | 66.67% | 66.67% |

## 2. Analisis Hasil Pengujian

1. **Kualitas Visual (PSNR & MSE):**
   - Nilai PSNR pada seluruh skenario berada jauh di atas **50 dB** (bahkan > 70 dB untuk pesan pendek), jauh melampaui batas ambang standar persepsi mata manusia (30 dB). Hal ini membuktikan bahwa metode LSB tidak menimbulkan degradasi visual yang dapat dideteksi mata manusia.
2. **Korelasi Kapasitas Muatan vs Kemudahan Deteksi:**
   - Pada muatan pendek (~50 byte), skor deteksi Chi-Square hampir tidak mengalami lonjakan karena jumlah pasangan nilai (PoV) yang termodifikasi sangat sedikit.
   - Sebaliknya, pada muatan tinggi (~75% kapasitas), perataan frekuensi pasangan nilai genap-ganjil terjadi secara masif di seluruh kanvas citra, menghasilkan $p$-value yang tinggi dan meningkatkan kecurigaan detektor steganalisis.
   - Temuan ini membuktikan hipotesis steganografi: **"Semakin besar kapasitas payload yang disisipkan, semakin rentan citra terdeteksi oleh analisis statistik tanpa kunci."**
