import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import glob
from datetime import datetime, timedelta

st.set_page_config(
    page_title="TL Bono | BIST Borçlanma Araçları",
    page_icon="📊",
    layout="wide"
)

# --- STİL ---
st.markdown("""
<style>
    .main { background-color: #0f1117; }
    .metric-card {
        background: #1e2130;
        border: 1px solid #2d3250;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 10px;
    }
    .metric-label { color: #8892b0; font-size: 13px; font-weight: 500; letter-spacing: 0.5px; }
    .metric-value { color: #e6f1ff; font-size: 26px; font-weight: 700; margin-top: 4px; }
    .metric-delta-pos { color: #64ffda; font-size: 13px; }
    .metric-delta-neg { color: #ff6b8a; font-size: 13px; }
    .header-title { color: #e6f1ff; font-size: 32px; font-weight: 800; letter-spacing: -0.5px; }
    .header-sub { color: #8892b0; font-size: 15px; margin-top: -8px; }
    .date-badge {
        background: #2d3250;
        color: #64ffda;
        font-size: 13px;
        padding: 4px 12px;
        border-radius: 20px;
        display: inline-block;
    }
    div[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)


# --- VERİ YÜKLEME ---
@st.cache_data(ttl=3600)
def veri_yukle():
    data_path = os.path.join(os.path.dirname(__file__), "data")
    
    tum_dosyalar = sorted(
        glob.glob(os.path.join(data_path, "*.xlsx")) +
        glob.glob(os.path.join(data_path, "*.xls")) +
        glob.glob(os.path.join(data_path, "*.csv")),
        reverse=True
    )
    
    if not tum_dosyalar:
        return None, None
    
    df_listesi = []
    
    for dosya in tum_dosyalar:
        try:
            if dosya.endswith(".csv"):
                df = pd.read_csv(dosya, sep=None, engine="python", encoding="utf-8-sig")
            else:
                # TL Bono sayfası varsa onu al, yoksa ilk sayfayı
                xl = pd.ExcelFile(dosya)
                if "TL Bono" in xl.sheet_names:
                    df = pd.read_excel(dosya, sheet_name="TL Bono")
                else:
                    df = pd.read_excel(dosya, sheet_name=0)
            
            # Dosya adından tarih çek (ttbYYYYAAGG3 formatı)
            dosya_adi = os.path.basename(dosya)
            tarih_str = ''.join(filter(str.isdigit, dosya_adi))[:8]
            if len(tarih_str) == 8:
                df["Tarih"] = pd.to_datetime(tarih_str, format="%Y%m%d", errors="coerce")
            
            df_listesi.append(df)
        except Exception:
            continue
    
    if not df_listesi:
        return None, None
    
    df_tum = pd.concat(df_listesi, ignore_index=True)
    son_tarih = df_tum["Tarih"].max() if "Tarih" in df_tum.columns else None
    
    return df_tum, son_tarih


# --- BAŞLIK ---
col_baslik, col_tarih = st.columns([3, 1])

with col_baslik:
    st.markdown('<div class="header-title">📊 TL Bono Piyasası</div>', unsafe_allow_html=True)
    st.markdown('<div class="header-sub">BIST Borçlanma Araçları Piyasası Günlük Bülten Verileri</div>', unsafe_allow_html=True)

with col_tarih:
    st.markdown("<br>", unsafe_allow_html=True)
    bugun = datetime.now().strftime("%d.%m.%Y %H:%M")
    st.markdown(f'<div class="date-badge">🕐 {bugun}</div>', unsafe_allow_html=True)

st.markdown("---")

# --- VERİ YÜKLE ---
df, son_tarih = veri_yukle()

if df is None or df.empty:
    st.warning("📂 Henüz veri bulunamadı. `data/` klasörüne Excel veya CSV dosyası ekleyin.")
    st.info("VBA makronuzu çalıştırarak `C:\\\\Users\\\\deniz\\\\OneDrive\\\\Masaüstü\\\\Bono BIST Hacim` klasöründeki dosyaları bu projenin `data/` klasörüne kopyalayın.")
    st.stop()

# --- SON TARİH BİLGİSİ ---
if son_tarih is not None:
    st.markdown(f'<div class="date-badge">📅 Son Veri: {pd.Timestamp(son_tarih).strftime("%d.%m.%Y")}</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

# --- KOLON TANIMLAMA ---
# Kolon isimlerini normalize et
df.columns = [str(c).strip() for c in df.columns]

# C sütununa karşılık gelen kolonu bul (büyük ihtimalle ISIN veya Menkul Kıymet)
col_c = df.columns[2] if len(df.columns) > 2 else None

# Sayısal kolonları bul
sayi_kolonlari = df.select_dtypes(include="number").columns.tolist()
if "Tarih" in sayi_kolonlari:
    sayi_kolonlari.remove("Tarih")

# --- FİLTRELER ---
st.markdown("### 🔍 Filtreler")
filtre_col1, filtre_col2, filtre_col3 = st.columns(3)

with filtre_col1:
    if "Tarih" in df.columns and df["Tarih"].notna().any():
        min_tarih = df["Tarih"].min().date()
        max_tarih = df["Tarih"].max().date()
        tarih_aralik = st.date_input(
            "Tarih Aralığı",
            value=(min_tarih, max_tarih),
            min_value=min_tarih,
            max_value=max_tarih
        )
    else:
        tarih_aralik = None

with filtre_col2:
    if col_c:
        degerler = sorted(df[col_c].dropna().unique().tolist())
        secili = st.multiselect(f"{col_c} Filtresi", options=degerler, default=[])
    else:
        secili = []

with filtre_col3:
    arama = st.text_input("🔎 Genel Arama", placeholder="Herhangi bir değer ara...")

# --- FİLTRE UYGULA ---
df_filtreli = df.copy()

if tarih_aralik and "Tarih" in df.columns and len(tarih_aralik) == 2:
    df_filtreli = df_filtreli[
        (df_filtreli["Tarih"].dt.date >= tarih_aralik[0]) &
        (df_filtreli["Tarih"].dt.date <= tarih_aralik[1])
    ]

if secili and col_c:
    df_filtreli = df_filtreli[df_filtreli[col_c].isin(secili)]

if arama:
    maske = df_filtreli.apply(lambda row: row.astype(str).str.contains(arama, case=False).any(), axis=1)
    df_filtreli = df_filtreli[maske]

st.markdown("---")

# --- METRİKLER ---
st.markdown("### 📈 Özet")
m1, m2, m3, m4 = st.columns(4)

with m1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">TOPLAM KAYIT</div>
        <div class="metric-value">{len(df_filtreli):,}</div>
    </div>""", unsafe_allow_html=True)

with m2:
    if col_c:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">TEKİL MENKUL KIYMET</div>
            <div class="metric-value">{df_filtreli[col_c].nunique():,}</div>
        </div>""", unsafe_allow_html=True)

with m3:
    if sayi_kolonlari:
        ilk_sayi = sayi_kolonlari[0]
        toplam = df_filtreli[ilk_sayi].sum()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{ilk_sayi.upper()} TOPLAM</div>
            <div class="metric-value">{toplam:,.0f}</div>
        </div>""", unsafe_allow_html=True)

with m4:
    if len(sayi_kolonlari) > 1:
        ikinci_sayi = sayi_kolonlari[1]
        ort = df_filtreli[ikinci_sayi].mean()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{ikinci_sayi.upper()} ORTALAMA</div>
            <div class="metric-value">{ort:,.2f}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("---")

# --- GRAFİKLER ---
if "Tarih" in df_filtreli.columns and sayi_kolonlari and not df_filtreli.empty:
    st.markdown("### 📉 Grafikler")
    
    g1, g2 = st.columns(2)
    
    with g1:
        secili_kolon = st.selectbox("Grafik için kolon seç", sayi_kolonlari, key="grafik1")
        
        df_gunluk = df_filtreli.groupby("Tarih")[secili_kolon].sum().reset_index()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_gunluk["Tarih"],
            y=df_gunluk[secili_kolon],
            mode="lines+markers",
            line=dict(color="#64ffda", width=2),
            marker=dict(color="#64ffda", size=5),
            fill="tozeroy",
            fillcolor="rgba(100, 255, 218, 0.05)"
        ))
        fig.update_layout(
            title=f"Günlük {secili_kolon}",
            paper_bgcolor="#1e2130",
            plot_bgcolor="#1e2130",
            font=dict(color="#8892b0"),
            xaxis=dict(gridcolor="#2d3250"),
            yaxis=dict(gridcolor="#2d3250"),
            margin=dict(l=10, r=10, t=40, b=10),
            height=320
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with g2:
        if col_c and len(sayi_kolonlari) > 0:
            secili_kolon2 = st.selectbox("Dağılım için kolon seç", sayi_kolonlari, key="grafik2")
            df_dag = df_filtreli.groupby(col_c)[secili_kolon2].sum().nlargest(10).reset_index()
            
            fig2 = px.bar(
                df_dag,
                x=secili_kolon2,
                y=col_c,
                orientation="h",
                title=f"İlk 10 — {secili_kolon2}",
                color=secili_kolon2,
                color_continuous_scale=["#2d3250", "#64ffda"]
            )
            fig2.update_layout(
                paper_bgcolor="#1e2130",
                plot_bgcolor="#1e2130",
                font=dict(color="#8892b0"),
                xaxis=dict(gridcolor="#2d3250"),
                yaxis=dict(gridcolor="#2d3250"),
                margin=dict(l=10, r=10, t=40, b=10),
                height=320,
                showlegend=False,
                coloraxis_showscale=False
            )
            st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# --- TABLO ---
st.markdown(f"### 📋 Veri Tablosu &nbsp; <span style='color:#8892b0; font-size:14px;'>({len(df_filtreli):,} satır)</span>", unsafe_allow_html=True)

# Tarih kolonu varsa formatla
df_goster = df_filtreli.copy()
if "Tarih" in df_goster.columns:
    df_goster["Tarih"] = df_goster["Tarih"].dt.strftime("%d.%m.%Y")

st.dataframe(
    df_goster,
    use_container_width=True,
    height=450,
    hide_index=True
)

# --- İNDİR ---
csv = df_filtreli.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label="⬇️ CSV olarak indir",
    data=csv,
    file_name=f"tl_bono_{datetime.now().strftime('%Y%m%d')}.csv",
    mime="text/csv"
)
