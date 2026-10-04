# Mahalnya Membangun Indonesia

UAS Visualisasi Data dan Informasi 2026. 

## Topik
- **geospasial** (choropleth IKK + proportional symbol PDRB Konstruksi, 514 kab/kota, 2025)
- **hierarki** (treemap + sunburst, Pulau > Provinsi > Jenis Bangunan, 2024)
- **multivariat** (PCA biplot, heatmap korelasi, scatter plot matrix; 8 variabel x 34 provinsi, 2025).

## Struktur
```
app.py                 # aplikasi Streamlit (Plotly)
requirements.txt
style.css
data/                  # data terolah 
scripts/preprocess.py  # CSV BPS + GeoJSON mentah -> data/
```
