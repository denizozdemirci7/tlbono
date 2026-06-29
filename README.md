# TL Bono | BIST Borçlanma Araçları Piyasası

BIST günlük bülten verilerini görselleştiren Streamlit uygulaması.

## Kurulum

### 1. Yerel çalıştırma
```bash
pip install -r requirements.txt
streamlit run app.py
```

### 2. Streamlit Cloud'a deploy
1. Bu repoyu GitHub'a yükle
2. [share.streamlit.io](https://share.streamlit.io) adresine git
3. GitHub reponuzu seç → Deploy

## Veri Ekleme

`data/` klasörüne VBA makronuzdan gelen `.xlsx` dosyalarını koyun.  
Dosya adı formatı: `ttbYYYYAAGG3.xlsx`

Her dosyada **TL Bono** adlı sheet aranır, yoksa ilk sheet kullanılır.
