# HideBit — Secure Image Steganography & Steganalysis

Aplikasi web terintegrasi untuk **Steganografi Citra LSB Teracak (PRNG)** dengan **Kriptografi Terotentikasi (AES-256-GCM)** dan **Detektor Steganalisis (Chi-Square PoV & Visual LSB Plane)**.

Proyek ini dibangun untuk memenuhi tugas **UTS Keamanan Informasi**.

---

## 🌟 Fitur Utama

### 1. Modul Encoder (Penyisipan Rahasia)
- **Kriptografi Kuat:** Pesan dienkripsi menggunakan **AES-256-GCM** (menghasilkan ciphertext + 16-byte authentication tag).
- **Derivasi Kunci:** Menggunakan **PBKDF2-HMAC-SHA256** dengan 100.000 iterasi dan random salt 16-byte untuk menangkal *dictionary/rainbow table attack*.
- **Sebaran Acak Deterministik (PRNG):** Posisi bit LSB diacak merata di seluruh bidang citra menggunakan PRNG ber-seed SHA-256 dari stego-key, bukan berurutan secara linear.
- **Header Khusus (8 Byte):** Identitas magic `HBIT` (4B) + panjang payload uint32 (4B).
- **Evaluasi Kualitas Otomatis:** Menghitung nilai **PSNR (dB)**, **MSE**, dan persentase kapasitas yang terpakai secara real-time.

### 2. Modul Decoder (Ekstraksi Rahasia)
- **Verifikasi Integritas:** Jika stego-key salah satu karakter saja, sistem menolak ekstraksi dan membangkitkan error `InvalidTag` (keaslian data terjamin).
- **Penolakan Cepat:** Header `HBIT` mencegah pemrosesan citra non-stego atau kunci acak yang tidak sesuai.

### 3. Modul Steganalisis (Detektor Tanpa Kunci)
- **Chi-Square Attack (Pairs of Values - PoV):** Mendeteksi perataan frekuensi pasangan nilai piksel genap-ganjil tanpa perlu mengetahui password maupun pesan rahasia.
- **Skor Kecurigaan (0–100%):** Berdasarkan nilai signifikansi statistik ($p$-value).
- **Visual LSB Plane Inspection:** Mengekstrak bit-0 dari kanal warna R, G, dan B menjadi citra visual hitam-putih untuk inspeksi anomali.

---

## 🚀 Cara Menjalankan Aplikasi Web

### 1. Pasang Dependensi
Pastikan Python 3.9+ sudah terpasang, lalu jalankan:
```bash
pip install -r requirements.txt
```

### 2. Jalankan Backend Server
```bash
python server.py
```
Aplikasi web akan aktif dan dapat diakses di browser melalui:
👉 **http://localhost:8080**

---

## 🧪 Pengujian Otomatis

Proyek ini dilengkapi dengan serangkaian skrip pengujian komprehensif:

1. **Uji Fondasi Kriptografi & Steganografi:**
   ```bash
   python tests/test_step1_step2.py
   ```
2. **Uji Integrasi End-to-End API Backend:**
   ```bash
   python tests/test_api_e2e.py
   ```
3. **Uji Kerapuhan Kompresi JPEG (Fragility Test):**
   ```bash
   python tests/test_jpeg_fragility.py
   ```
4. **Benchmark 5 Citra × 3 Beban Pesan (Laporan Otomatis):**
   ```bash
   python tests/benchmark_report.py
   ```
   *Hasil benchmark akan diekspor langsung ke [report/benchmark_results.md](file:///c:/CODING/UTS-KI/report/benchmark_results.md).*

---

## 📁 Struktur Direktori

```text
UTS-KI/
├── src/
│   ├── crypto.py         # Modul enkripsi & dekripsi AES-256-GCM + PBKDF2
│   ├── stego.py          # Modul penyisipan & ekstraksi LSB teracak PRNG
│   ├── steganalysis.py   # Modul deteksi Chi-Square PoV & visual LSB plane
│   └── metrics.py        # Modul metrik kualitas citra (PSNR, MSE, histogram)
├── sample_images/        # 5 citra uji untuk pengujian dan benchmark
├── tests/
│   ├── test_step1_step2.py    # Unit test modul kripto & stego
│   ├── test_api_e2e.py        # Uji end-to-end API Flask
│   ├── test_jpeg_fragility.py # Uji kerapuhan stego terhadap JPEG
│   └── benchmark_report.py    # Otomatisasi pengujian 5 citra x 3 payload
├── report/
│   └── benchmark_results.md   # Hasil tabel PSNR/MSE/Chi-Square untuk laporan
├── index.html            # Antarmuka web modern HideBit
├── styles.css            # Desain styling antarmuka web
├── app.js                # Logika frontend & integrasi fetch API
├── server.py             # Server Flask backend penyedia REST API
└── requirements.txt      # Daftar dependensi Python
```
