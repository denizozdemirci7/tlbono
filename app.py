import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import zipfile
import io
from datetime import date, timedelta

st.set_page_config(
    page_title="TL Bono | BIST",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #0f1117; }
    [data-testid="stHeader"] { background-color: #0f1117; }
    .metric-card {
        background: #1e2130;
        border: 1px solid #2d3250;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 10px;
    }
    .metric-label { color: #8892b0; font-size: 12px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; }
    .metric-value { color: #e6f1ff; font-size: 28px; font-weight: 700; margin-top: 4px; }
    .header-title { color: #e6f1ff; font-size: 34px; font-weight: 800; }
    .header-sub { color: #8892b0; font-size: 14px; margin-top: -6px; }
    .badge { background: #2d3250; color: #64ffda; font-size: 12px; padding: 4px 12px; border-radius: 20px; display: inline-block; }
</style>
""", unsafe_allow_html=True)


def onceki_is_gunu(bugun=None):
    if bugun is None:
        bugun = date.today()
    gun = bugun.weekday()  # 0=Pzt, 6=Paz
    if gun == 0:
        return bugun - timedelta(days=3)
    elif gun == 6:
        return bugun - timedelta(days=2)
    else:
        return bugun - timedelta(days=1)


@st.cache_data(ttl=3600, show_spinner=False)
def veri_cek(tarih: date):
    yil = tarih.strftime("%Y")
    ay  = tarih.strftime("%m")
    gun = tarih.strftime("%d")

    url = f"https://www.borsaistanbul.com/data/ttb/{yil}/{ay}/ttb{yil}{ay}{gun}3.zip"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.borsaistanbul.com/",
        "Accept": "*/*"
    }

    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code != 200:
            return None, f"HTTP {r.status_code} — Veri bulunamadı ({tarih.strftime('%d.%m.%Y')})"

        z = zipfile.ZipFile(io.BytesIO(r.content))
        dosyalar = z.namelist()

        # CSV veya Excel bul
        csv_dosyalar = [f for f in dosyalar if f.endswith(".csv")]
        xls_dosyalar = [f for f in dosyalar if f.endswith(".xlsx") or f.endswith(".xls")]

        if csv_dosyalar:
            with z.open(csv_dosyalar[0]) as f:
                df = pd.read_csv(f, sep=None, engine="python", encoding="utf-8-sig", header=0)
        elif xls_dosyalar:
            with z.open(xls_dosyalar[0]) as f:
                df = pd.read_excel(f, header=0)
        else:
            return None, "ZIP içinde veri dosyası bulunamadı."

        # 2. satırı sil (başlık sonrası boş/açıklama satırı)
        if len(df) > 0:
            df = df.iloc[1:].reset_index(drop=True)

        # C sütunu (index 2) TRT filtresi
        if df.shape[1] > 2:
            col_c = df.columns[2]
            df = df[df[col_c].astype(str).str.startswith("TRT")].reset_index(drop=True)

        df["_tarih"] = tarih
        return df, None

    except Exception as e:
        return None, str(e)


# --- BAŞLIK ---
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown('<div class="header-title">📊 TL Bono Piyasası</div>', unsafe_allow_html=True)
    st.markdown('<div class="header-sub">BIST Borçlanma Araçları Piyasası — Günlük Bülten</div>', unsafe_allow_html=True)
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    bugun_str = date.today().strftime("%d.%m.%Y")
    st.markdown(f'<div class="badge">🗓 Bugün: {bugun_str}</div>', unsafe_allow_html=True)

st.markdown("---")

# --- TARİH SEÇİCİ ---
col_t1, col_t2 = st.columns([2, 3])
with col_t1:
    secilen_tarih = st.date_input(
        "Veri tarihi",
        value=onceki_is_gunu(),
        max_value=date.today(),
        format="DD.MM.YYYY"
    )

# --- VERİ ÇEK ---
with st.spinner(f"{secilen_tarih.strftime('%d.%m.%Y')} verisi indiriliyor..."):
    df, hata = veri_cek(secilen_tarih)

if hata:
    st.error(f"⚠️ {hata}")
    st.info("Farklı bir tarih seçmeyi deneyin veya o gün piyasa kapalı olabilir.")
    st.stop()

if df is None or df.empty:
    st.warning("Seçilen tarih için TRT ile başlayan kayıt bulunamadı.")
    st.stop()

st.markdown(f'<div class="badge">✅ {secilen_tarih.strftime("%d.%m.%Y")} verisi yüklendi — {len(df):,} kayıt</div>', unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# --- KOLON İSİMLERİ ---
kolonlar = df.columns.tolist()
sayi_kolonlari = df.select_dtypes(include="number").columns.tolist()
col_c = kolonlar[2] if len(kolonlar) > 2 else None

# --- METRİKLER ---
m1, m2, m3, m4 = st.columns(4)

with m1:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">Toplam Kayıt</div>
        <div class="metric-value">{len(df):,}</div>
    </div>""", unsafe_allow_html=True)

with m2:
    if col_c:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">Tekil Menkul Kıymet</div>
            <div class="metric-value">{df[col_c].nunique():,}</div>
        </div>""", unsafe_allow_html=True)

with m3:
    if sayi_kolonlari:
        toplam = df[sayi_kolonlari[0]].sum()
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">{sayi_kolonlari[0]}</div>
            <div class="metric-value">{toplam:,.0f}</div>
        </div>""", unsafe_allow_html=True)

with m4:
    if len(sayi_kolonlari) > 1:
        ort = df[sayi_kolonlari[1]].mean()
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">{sayi_kolonlari[1]} Ort.</div>
            <div class="metric-value">{ort:,.2f}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("---")

# --- GRAFİK ---
if sayi_kolonlari and col_c:
    st.markdown("### 📉 Grafik")
    g1, g2 = st.columns(2)

    with g1:
        sec1 = st.selectbox("Sütun seç", sayi_kolonlari, key="g1")
        df_top = df.groupby(col_c)[sec1].sum().nlargest(15).reset_index()
        fig = px.bar(
            df_top, x=sec1, y=col_c, orientation="h",
            title=f"İlk 15 — {sec1}",
            color=sec1,
            color_continuous_scale=["#2d3250", "#64ffda"]
        )
        fig.update_layout(
            paper_bgcolor="#1e2130", plot_bgcolor="#1e2130",
            font=dict(color="#8892b0"),
            xaxis=dict(gridcolor="#2d3250"),
            yaxis=dict(gridcolor="#2d3250", categoryorder="total ascending"),
            margin=dict(l=10, r=10, t=40, b=10),
            height=400, showlegend=False, coloraxis_showscale=False
        )
        st.plotly_chart(fig, use_container_width=True)

    with g2:
        sec2 = st.selectbox("Sütun seç", sayi_kolonlari, key="g2", index=min(1, len(sayi_kolonlari)-1))
        df_pie = df.groupby(col_c)[sec2].sum().nlargest(10).reset_index()
        fig2 = px.pie(
            df_pie, values=sec2, names=col_c,
            title=f"Dağılım — {sec2} (İlk 10)",
            color_discrete_sequence=px.colors.sequential.Teal
        )
        fig2.update_layout(
            paper_bgcolor="#1e2130",
            font=dict(color="#8892b0"),
            margin=dict(l=10, r=10, t=40, b=10),
            height=400
        )
        st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# --- TABLO ---
st.markdown(f"### 📋 Veri Tablosu ({len(df):,} satır)")

df_goster = df.drop(columns=["_tarih"], errors="ignore")
st.dataframe(df_goster, use_container_width=True, height=500, hide_index=True)

# --- İNDİR ---
csv = df_goster.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "⬇️ CSV olarak indir",
    data=csv,
    file_name=f"tl_bono_{secilen_tarih.strftime('%Y%m%d')}.csv",
    mime="text/csv"
)
