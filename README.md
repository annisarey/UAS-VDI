# Konstruksi Indonesia: Biaya, Nilai, dan Denyutnya (Streamlit)

UAS Visualisasi Data dan Informasi 2026. Tiga topik: **geospasial** (choropleth IKK + proportional symbol PDRB Konstruksi, 513 kab/kota, 2025), **hierarki** (treemap + sunburst, Pulau > Provinsi > Jenis Bangunan, 2024), **multivariat** (PCA biplot, heatmap korelasi, scatter plot matrix; 8 variabel x 34 provinsi, 2025).

## Struktur
```
app.py                 # aplikasi Streamlit (Plotly)
requirements.txt
data/                  # data terolah yang dibaca app.py
scripts/preprocess.py  # CSV BPS + GeoJSON mentah -> data/
raw/                   # file mentah (geojson 42 MB: jangan di-commit)
```

## Menjalankan lokal
```bash
pip install -r requirements.txt
streamlit run app.py
```
(Opsional, `data/` sudah terisi) regenerasi data: letakkan `administrasi_kabkota.geojson`, `geospasial.csv`, `hierarchy.csv`, `multivariate.csv` di `raw/`, lalu `python scripts/preprocess.py raw`.

## Deploy (Streamlit Community Cloud, gratis, tanpa login untuk pengunjung)
1. Buat repo GitHub **publik**; commit `app.py`, `requirements.txt`, `data/`, `scripts/`, `README.md` (`raw/` sudah di `.gitignore`).
2. Buka https://share.streamlit.io, login GitHub, **New app**, pilih repo, branch `main`, main file `app.py`, Deploy.
3. Salin URL `*.streamlit.app` ke makalah dan footer. Aplikasi bisa "tidur" jika sepi; buka sebelum penilaian agar aktif.

## Interaksi
- Geospasial: hover tooltip, zoom/pan, checkbox layer, filter provinsi.
- Hierarki: klik untuk drill-down + breadcrumb (path bar treemap, pusat sunburst), filter pulau.
- Multivariat: box/lasso pada PCA atau multiselect menyorot provinsi di scatter plot matrix (brushing and linking).

## Keputusan pengolahan (tulis di makalah)
- **Join peta**: kunci nama + penanda kota dari `kdkab >= 71`; alias manual Kota Baru, Mahakam Ulu, Mamuju Utara (= Pasangkayu). CSV tanpa kode wilayah, jadi ini keterbatasan. 513 poligon terpakai dari 514 baris.
- **Simplifikasi geometri**: Douglas-Peucker 0,012 derajat (42 MB menjadi 0,5 MB).
- **Hierarki**: pemetaan provinsi ke pulau manual; Papua pemekaran ("-") dikeluarkan; satuan diasumsikan juta Rp.
- **Multivariat**: log10 untuk PDRB konstruksi, jumlah perusahaan, belanja modal, lalu z-score; 4 provinsi Papua baru dibuang (NA), tersisa 34.
- **Warna**: viridis (kuantil), cividis, PuOr, Okabe-Ito: semuanya ramah buta warna.

## Yang masih harus kamu kerjakan
1. Isi *Sumber data* (judul tabel, tahun, URL, tanggal akses) di footer `app.py` dan makalah.
2. Pastikan satuan data (PDRB miliar Rp? nilai konstruksi juta Rp?).
3. Makalah IEEE 6-8 halaman, 10 referensi (3 internasional), tangkapan layar, URL app dan repo, deklarasi AI di Metodologi.
