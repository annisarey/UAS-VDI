# 🏗️ Mahalnya Membangun Indonesia

Dasbor *data storytelling* interaktif tentang **Indeks Kemahalan Konstruksi (IKK)**, struktur nilai konstruksi, dan profil multivariat konstruksi Indonesia.

Proyek ini dibuat untuk UAS Visualisasi Data dan Informasi (K203407), Program Studi D-IV Komputasi Statistik, Politeknik Statistika STIS, TA 2025/2026.

| | |
|---|---|
| 🔗 **Aplikasi (publik, tanpa login)** | https://mahalnya-membangun-indonesia.streamlit.app/ |
| 📦 **Repositori** | https://github.com/annisarey/UAS-VDI |
| 👤 **Penulis** | Annisa Raihana Mudzakir (222312986), kelas 3SD2 |
| 🎓 **Dosen pengampu** | Farid Ridho, S.S.T., M.T. |

---

## Gambaran Singkat

Biaya membangun, besar pasar konstruksi, dan karakter industri konstruksi tidak bergerak searah. Dasbor ini menceritakan hal itu dalam tiga bab:

| Bab | Topik visualisasi | Teknik | Cakupan |
|---|---|---|---|
| **I. Biaya** | Geospasial | Peta *choropleth* IKK + peta simbol proporsional PDRB konstruksi | 514 kab/kota, 2025 |
| **II. Struktur pasar** | Hierarki | *Treemap* dan *sunburst* (Indonesia → Pulau → Provinsi → Jenis bangunan) | 34 provinsi, 2024 |
| **III. Profil provinsi** | Multivariat | Biplot PCA, *heatmap* (profil dan korelasi), *scatterplot matrix* | 8 indikator, 34 provinsi, 2025 |

### Cara membaca visual (encoding)

- **Peta:** warna = IKK (indeks); luas lingkaran = PDRB konstruksi (nilai absolut). Garis tebal menandai wilayah yang dipilih.
- **Treemap/Sunburst:** luas = nilai konstruksi (triliun Rp); warna = porsi konstruksi sipil (%).
- **Biplot PCA:** titik = provinsi; warna = kelompok pulau; panah = arah indikator.
- **Heatmap/SPLOM:** korelasi antarindikator dan pola pasangan variabel.

### Interaksi

Tooltip kustom, filter provinsi/kab-kota dengan zoom otomatis, *toggle* lapisan peta, filter kelompok pulau, *drill-down* pada hierarki, penyorotan provinsi, *brushing* (kotak/laso) pada biplot, dan pemilih variabel pada heatmap dan SPLOM. Kontrol dikemas dalam *popover* agar muat di ponsel.

### Temuan utama (deskriptif)

- IKK tertinggi: **Puncak, Papua (361,36)**; terendah: **Belu, NTT (76,68)**; rasio ≈ 4,71×. PDRB konstruksi terbesar: **Kota Jakarta Utara (≈ Rp57,15 T)**. Wilayah termahal belum tentu pasar terbesar.
- Sepuluh kab/kota teratas menyumbang ≈ 31,0% PDRB konstruksi, padahal hanya ≈ 1,9% dari jumlah wilayah.
- **Jawa menyerap ≈ 72,1%** nilai konstruksi yang diselesaikan (data 2024).
- Dua komponen PCA menjelaskan **≈ 72,9%** variasi (PC1 58,2%; PC2 14,7%). Jawa Barat paling jauh dari pusat skor.

---

## Struktur Repositori

```
UAS-VDI/
├── app.py              # Aplikasi Streamlit (seluruh visualisasi dan narasi)
├── style.css           # Gaya tampilan (tema, responsif, tooltip, navigasi)
├── 
├── requirements.txt    # Dependensi Python
├── README.md
├── script
    ├── preprocess.py     # Pra-pemrosesan: gabung CSV BPS + batas wilayah, sederhanakan geometri
└── data/               # Data terolah (dibaca oleh app.py)
    ├── kabkota.geojson   # Batas kab/kota + IKK, PDRB konstruksi, porsi konstruksi
    ├── hierarki.json     # Nilai konstruksi: pulau, provinsi, gedung/sipil/khusus
    └── multivariat.json  # 8 indikator per provinsi
```

## Data

Seluruh data utama bersumber dari **BPS**; data belanja modal dari **Portal SIKD, Kementerian Keuangan**. Akses data: 1 Oktober 2026.

| Lapisan | Isi | Sumber | Tahun |
|---|---|---|---|
| Geospasial | IKK; PDRB Lapangan Usaha F (Konstruksi) per kab/kota | BPS | 2025 |
| Hierarki | Nilai konstruksi yang diselesaikan menurut jenis (gedung, sipil, khusus) | BPS | 2024 |
| Multivariat | 8 indikator per provinsi (tabel di bawah) | BPS, SIKD Kemenkeu | 2025 |

**Indikator yang Digunakan**

1. Indeks Kemahalan Konstruksi (IKK), 2025
2. PDRB Atas Dasar Harga Konstan (2010) Lapangan Usaha Konstruksi, 2025
3. Banyaknya perusahaan konstruksi, 2025
4. Indeks nilai konstruksi yang diselesaikan (2016=100), 2025
5. Indeks balas jasa pekerja tetap dan upah pekerja harian (2016=100), 2025
6. Indeks pekerja tetap konstruksi (2016=100), 2025
7. Indeks hari orang pekerja harian (2016=100), 2025
8. Belanja modal menurut provinsi (Postur APBD), 2025
9. Nilai Konstruksi yang Diselesaikan Perusahaan Konstruksi (Juta Rupiah), 2024


**Sumber (judul, URL)**

- BPS, *Indeks Kemahalan Konstruksi Provinsi dan Kabupaten/Kota 2025* (Katalog 7102025, No. 06200.25020): https://www.bps.go.id/id/publication/2025/10/01/935f3f46173c68d21b6c5126/indeks-kemahalan-konstruksi-provinsi-dan-kabupaten-kota-2025.html
- BPS, *Produk Domestik Regional Bruto Kabupaten/Kota di Indonesia 2021–2025* (Katalog 9302025): https://www.bps.go.id/assets/publication/2026/06/10/234d5061d35a199c70e77766/produk-domestik-regional-bruto-kabupaten-kota-di-indonesia-2021-2025.html
- BPS, Tabel *Nilai Konstruksi yang Diselesaikan Perusahaan Konstruksi (Juta Rupiah)*: https://www.bps.go.id/id/statistics-table/2/MjI5IzI%3D/nilai-konstruksi-yang-diselesaikan-perusahaan-konstruksi.html
- BPS, Tabel *Banyaknya Perusahaan Konstruksi*: https://www.bps.go.id/id/statistics-table/2/MjE2IzI=/banyaknya-perusahaan-konstruksi.html
- BPS, Tabel *Indeks Triwulanan Nilai Konstruksi yang Diselesaikan … (2016=100)*: https://www.bps.go.id/id/statistics-table/2/NTUzIzI%3D/indeks-triwulanan-nilai-konstruksi-yang-diselesaikan-perusahaan-konstruksi-menurut-provinsi-2016-100-.html
- BPS, Tabel *Indeks Triwulanan Balas Jasa Pekerja Tetap dan Upah Pekerja Harian … (2016=100)*: https://www.bps.go.id/id/statistics-table/2/NTUwIzI%3D/indeks-triwulanan-balas-jasa-pekerja-tetap-dan-upah-pekerja-harian-konstruksi-menurut-provinsi-2016-100-.html
- BPS, Tabel *Indeks Triwulanan Pekerja Tetap Konstruksi … (2016=100)*: https://www.bps.go.id/id/statistics-table/2/NTQ4IzI%3D/indeks-triwulanan-pekerja-tetap-konstruksi-menurut-provinsi-2016-100-.html
- BPS, Tabel *Indeks Triwulanan Hari Orang Pekerja Harian … (2016=100)*: https://www.bps.go.id/id/statistics-table/2/NTQ5IzI%3D/indeks-triwulanan-hari-orang-pekerja-harian-perusahaan-konstruksi-menurut-provinsi-2016-100-.html
- Kementerian Keuangan RI, Portal Data SIKD: Postur APBD: https://djpk.kemenkeu.go.id/portal/data/apbd
- Batas wilayah kab/kota (data pendukung non-BPS): https://geoservices.big.go.id/portal/apps/webappviewer/index.html?id=49bda2cefd3f4b92aa726300bcdb40f7

> **Catatan tahun:** data hierarki memakai 2024 karena rincian nilai konstruksi menurut jenis belum dirilis BPS untuk 2025. Bab II dibaca sebagai *struktur* pasar, bukan perbandingan nominal langsung dengan peta.

---

## Pra-pemrosesan

Skrip `preprocess.py` mengubah berkas mentah menjadi tiga berkas ringan di `data/`:

1. **Geospasial:** menggabungkan `geospasial.csv` dengan `administrasi_kabkota.geojson` memakai nama wilayah yang dinormalisasi dan pembeda kota/kabupaten dari kode wilayah, plus tabel alias untuk nama yang berbeda penulisan. Menghitung porsi konstruksi = PDRB konstruksi ÷ PDRB total × 100. Geometri disederhanakan dengan Douglas–Peucker (toleransi 0,012°), koordinat dibulatkan, dan poligon sangat kecil dibuang.
2. **Hierarki:** memetakan provinsi ke enam kelompok pulau, lalu membentuk Pulau → Provinsi → Jenis (gedung, sipil, khusus).
3. **Multivariat:** menggabungkan 8 indikator per provinsi dan membuang provinsi dengan nilai kosong. Provinsi yang dikeluarkan: Papua Barat Daya, Papua Selatan, Papua Tengah, Papua Pegunungan.

Skrip mencetak ringkasan validasi (poligon cocok/tidak cocok, baris CSV tak terpakai, provinsi tak terpetakan, provinsi dibuang) untuk memeriksa kunci gabung.

Pada aplikasi, indikator berskala besar (PDRB konstruksi, jumlah perusahaan, belanja modal) ditransformasi `log10`, seluruh variabel distandardisasi (*z-score*), lalu PCA dihitung dari matriks korelasi melalui dekomposisi nilai eigen.

### Menjalankan ulang pra-pemrosesan

Berkas mentah yang dibutuhkan: `administrasi_kabkota.geojson`, `geospasial.csv`, `hierarchy.csv`, `multivariate.csv` (CSV berpemisah `;`).

```bash
# dari akar repositori; argumen = folder berkas mentah (bawaan: ../raw)
python preprocess.py path/ke/raw
```

Keluaran ditulis ke `data/kabkota.geojson`, `data/hierarki.json`, dan `data/multivariat.json`. Folder `data/` harus sudah ada.

---

## Menjalankan Secara Lokal

Prasyarat: Python 3.10+.

```bash
git clone https://github.com/annisarey/UAS-VDI.git
cd UAS-VDI
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Pustaka utama: `streamlit`, `plotly`, `pandas`, `numpy`. Peta memakai lapisan MapLibre dengan *basemap* Carto Positron, sehingga membutuhkan koneksi internet untuk memuat tile.

## Deployment

Aplikasi di-*deploy* di **Streamlit Community Cloud** langsung dari repositori GitHub ini (*main file*: `app.py`). Tidak perlu login maupun instalasi untuk membukanya.

---

## Aksesibilitas dan Responsivitas

- Palet: skala hijau-biru (IKK), Cividis (komposisi hierarki), PuOr divergen (korelasi), dan enam warna kategorikal untuk kelompok pulau.
- Tata letak responsif (grafik Plotly `responsive`, CSS khusus); kontrol dikemas dalam *popover* untuk layar kecil.
- Uji simulasi buta warna formal dan uji kebergunaan dengan responden **belum dilakukan**.

## Keterbatasan

- Data hierarki 2024, lapisan lain 2025.
- Lingkaran pada peta memakai titik representatif dari ring geometri utama, bukan sentroid sebenarnya.
- PCA dua dimensi hanya merangkum ≈ 72,9% variasi; empat provinsi Papua hasil pemekaran dikeluarkan karena data tidak lengkap.
- IKK bersifat relatif terhadap wilayah referensi, bukan harga absolut.
- *Brushing* pada biplot PCA belum otomatis menyorot titik yang sama pada heatmap atau SPLOM (linking lintas grafik belum ada).
- Korelasi tidak membuktikan sebab-akibat.

## Deklarasi Penggunaan AI

Asisten AI generatif digunakan sebagai alat bantu untuk *brainstorming*, peninjauan kode, *debugging*, dan penyuntingan bahasa. Pemilihan data, rancangan visualisasi, validasi angka, keputusan implementasi, dan interpretasi akhir diperiksa dan ditetapkan oleh penulis.

## Sumber Data

Data bersumber dari BPS dan Kemenkeu; gunakan sesuai ketentuan masing-masing sumber.
