# HideBit — Secure Image Steganography & Steganalysis

Aplikasi web terintegrasi untuk **Steganografi Citra LSB Teracak (PRNG)** dengan **Kriptografi Terotentikasi (AES-256-GCM)**, **Detektor Steganalisis Forensik (Chi-Square PoV & Bit-0 Plane)**, dan **Visualisasi Perbandingan Histogram RGB**.

Proyek ini dibangun untuk memenuhi tugas **UTS Praktikum Keamanan Informasi (Topik B: Aplikasi Steganografi)**.

---

## 👥 Tim Pengembang
* **Program Studi Informatika — Fakultas Teknik, Universitas Siliwangi (2026)**
* **Dosen Pengampu:** Ir. Alam Rahmatulloh, S.T., M.T., MCE., IPM.

| No | Nama Mahasiswa | NPM | Peran / Kontribusi |
| :-: | :--- | :-: | :--- |
| 1 | **Fathir Rizki Fadillah** | 247006111129 | *Ketua Kelompok* (Fullstack Dev & Integrasi Sistem) |
| 2 | **Aria Muhammad Fahlevi** | 247006111131 | *Anggota* (Pengujian Data & Evaluasi Metrik) |
| 3 | **Moh Raya Alfareza Alban** | 247006111133 | *Anggota* (Dokumentasi Laporan & Desain UI) |

🌐 **Live Web Application:** [https://hidebit.onrender.com](https://hidebit.onrender.com)  
🎥 **Video Demonstrasi UTS:** [https://youtu.be/ZoLfv0R3PX8](https://youtu.be/ZoLfv0R3PX8)  
📊 **Berkas Data Pengujian:** [`DATA PENGUJIAN_UTS_KEAMANAN INFORMASI.xlsx`](./DATA%20PENGUJIAN_UTS_KEAMANAN%20INFORMASI.xlsx)  

---

## 🌟 Fitur Utama

### 1. Modul Encoder (Penyisipan Rahasia)
- **Kriptografi Kuat:** Muatan dienkripsi menggunakan **AES-256-GCM** (menghasilkan ciphertext + 16-byte authentication tag).
- **Derivasi Kunci Kriptografis:** Menggunakan **PBKDF2-HMAC-SHA256** dengan 100.000 iterasi dan random salt 16-byte untuk menangkal *dictionary* & *rainbow table attack*.
- **Sebaran Acak Deterministik (PRNG):** Posisi bit LSB diacak merata ke seluruh bidang citra menggunakan PRNG ber-seed SHA-256 dari stego-key (NumPy permutation).
- **Header Khusus (8 Byte):** Identitas magic `HBIT` (4B) + panjang payload uint32 big-endian (4B) sebagai pengaman *fail-fast* dan pembatas pembacaan bit eksak.
- **Dukungan Berkas Biner Arbitrer (Fitur Pengayaan):** Mampu menyisipkan berkas dokumen (`.docx`, `.pdf`, `.zip`) dengan binary envelope parser dan validasi integritas SHA-256.
- **Kompresi Adaptif:** Kompresi zlib level 9 otomatis jika muatan terbukti terkompresi lebih kecil.
- **Evaluasi Kualitas Otomatis:** Menghitung nilai **PSNR (dB)**, **MSE**, dan *Difference Heatmap* secara real-time.

### 2. Modul Decoder (Ekstraksi Rahasia)
- **Verifikasi Integritas:** Jika stego-key salah 1 karakter saja atau citra mengalami manipulasi, sistem menolak ekstraksi dan memunculkan error autentikasi GCM (*tamper-evident*).
- **Penolakan Cepat (*Fail-Fast*):** Header `HBIT` mencegah pembacaan citra non-stego atau kunci acak yang tidak sesuai.
- **Unduh Dokumen Asli:** Ekstraksi berkas biner otomatis mendeteksi nama dan ekstensi asli berkas serta menyediakan tombol unduh langsung.

### 3. Modul Steganalisis (Detektor Forensik & Telemetri)
- **Uji Statistik Chi-Square PoV (Westfeld 1999):** Mendeteksi perataan frekuensi pasangan nilai piksel berdekatan $(2k, 2k+1)$ tanpa memerlukan kunci maupun pesan asli.
- **Skor Kecurigaan Heuristik (0–100):** Menghitung level anomali statistik global dan lokal citra.
- **Inspeksi Visual Bidang LSB (Bit-0 Plane):** Mengekstrak bit-0 kanal Red, Green, dan Blue ke citra biner kontras tinggi (menampakkan *high-entropy static noise*).
- **Perbandingan Histogram RGB (Publikasi Ilmiah):** Visualisasi kurva frekuensi 256 bin intensitas 3 kanal bertingkat (Merah, Hijau, Biru) untuk membuktikan kurva cover dan stego berhimpit sempurna ($\Delta \text{Mean} \le 0,004$).

---

## 📖 Contoh Penggunaan (Panduan Singkat)

### Skenario A: Menyembunyikan Pesan / Berkas Dokumen (Tab *Hide Message*)
1. Buka aplikasi web di browser.
2. Unggah citra pembawa (*cover image*) berformat PNG atau BMP (misal: `Mount-Everest.png`).
3. Pilih mode muatan: **Pesan Teks** atau **Unggah Berkas** (misal: dokumen `file_testing.docx`).
4. Masukkan kata sandi rahasia atau klik tombol **Generate Strong Key** untuk membuat kunci berentropi tinggi.
5. Klik **Embed Message**. Sistem akan mengenkripsi muatan, menyisipkannya ke bit LSB secara acak, menampilkan nilai PSNR/MSE, serta menyediakan tombol unduh citra stego.

### Skenario B: Mengekstrak Pesan / Berkas Rahasia (Tab *Reveal Message*)
1. Pindah ke tab **Reveal Message**.
2. Unggah citra stego yang telah dihasilkan sebelumnya.
3. Masukkan stego-key yang sesuai.
4. Klik **Reveal Message**. 
   * Jika kunci benar: teks rahasia akan ditampilkan atau tombol unduh berkas asli akan muncul.
   * Jika kunci salah (atau diubah 1 karakter): sistem langsung menolak dan menampilkan pesan galat.

### Skenario C: Menjalankan Analisis Forensik & Histogram (Tab *Steganalysis*)
1. Pindah ke tab **Steganalysis**.
2. Pilih **Mode Komparasi (Cover vs Stego)**.
3. Unggah citra stego pada kotak Citra Uji dan citra asli pada kotak Citra Referensi Cover.
4. Klik **Jalankan Analisis Forensik**.
5. Sistem akan menampilkan skor kecurigaan, selisih piksel terinjeksi, tabel statistik Chi-Square PoV, kurva perbandingan histogram 3 kanal RGB, dan komparasi visual Bit-0 plane.

---

## 🚀 Cara Menjalankan Aplikasi Web Secara Lokal

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
👉 **http://localhost:8000**

---

## 🧪 Pengujian Otomatis (Unit Test Suite)

Proyek ini dilengkapi dengan serangkaian skrip pengujian komprehensif untuk memvalidasi seluruh kriteria penilaian:

1. **Uji Fondasi Kriptografi & Steganografi LSB-PRNG:**
   ```bash
   python tests/test_step1_step2.py
   ```
2. **Uji Integrasi End-to-End RESTful API Backend:**
   ```bash
   python tests/test_api_e2e.py
   ```
3. **Uji Penyisipan & Ekstraksi Berkas Biner Arbitrer (.docx / .pdf):**
   ```bash
   python tests/test_file_payload_e2e.py
   ```
4. **Uji Kerapuhan Kompresi JPEG (Fragility Test Q90, Q75, Q50):**
   ```bash
   python tests/test_jpeg_fragility.py
   ```
5. **Uji Steganalisis Chi-Square PoV & Bit-0 Plane:**
   ```bash
   python tests/test_steganalysis_enhanced.py
   ```

---

## 📁 Struktur Direktori

```text
HideBit/
├── index.html            # Antarmuka web modern HideBit (single-page)
├── styles.css            # Desain styling antarmuka web
├── app.js                # Logika frontend, pemanggilan REST API, & Canvas telemetri
├── server.py             # Server Flask backend (Port 8000)
├── requirements.txt      # Daftar dependensi Python
├── Procfile              # Perintah worker gunicorn untuk cloud deployment
├── render.yaml           # Konfigurasi deployment di platform Render
├── README.md             # Dokumentasi teknis proyek
├── file_testing.docx     # Berkas dokumen sampel untuk pengujian muatan biner
├── DATA PENGUJIAN_UTS_KEAMANAN INFORMASI.xlsx  # Lembar kerja lengkap 8 sheet data uji
├── src/
│   ├── crypto.py         # Modul enkripsi AES-256-GCM, PBKDF2, & kompresi zlib
│   ├── stego.py          # Modul penyisipan & ekstraksi LSB teracak PRNG
│   ├── steganalysis.py   # Modul deteksi Chi-Square PoV & visual LSB plane
│   └── metrics.py        # Modul metrik PSNR, MSE, Difference Heatmap, & histogram
├── sample_images/        # Berkas citra cover sampel uji (PNG/BMP)
├── tests/
│   ├── test_step1_step2.py          # Unit test modul kripto & stego inti
│   ├── test_api_e2e.py              # Uji end-to-end API Flask
│   ├── test_file_payload_e2e.py     # Uji penyisipan & ekstraksi berkas dokumen biner
│   ├── test_jpeg_fragility.py       # Uji kerapuhan stego terhadap kompresi JPEG
│   └── test_steganalysis_enhanced.py # Uji statistik Chi-Square PoV & Bit-0 plane
└── test_results/         # Artefak citra hasil pengujian & plot histogram
```
