import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import zipfile
import io
from datetime import date, timedelta, datetime

st.set_page_config(
    page_title="TL Bono | BIST",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #0f1117; }
    [data-testid="stHeader"] { background-color: #0f1117; }
    [data-testid="stSidebar"] { background-color: #1e2130; }
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

EVDS_KEY = "rZzI65ePpI"

# ─────────────────────────────────────────────
# YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────────

def onceki_is_gunu(bugun=None):
    if bugun is None:
        bugun = date.today()
    gun = bugun.weekday()
    if gun == 0:
        return bugun - timedelta(days=3)
    elif gun == 6:
        return bugun - timedelta(days=2)
    else:
        return bugun - timedelta(days=1)


@st.cache_data(ttl=3600, show_spinner=False)
def bist_veri_cek(tarih: date):
    yil = tarih.strftime("%Y")
    ay  = tarih.strftime("%m")
    gun = tarih.strftime("%d")
    url = f"https://www.borsaistanbul.com/data/ttb/{yil}/{ay}/ttb{yil}{ay}{gun}3.zip"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://www.borsaistanbul.com/",
        "Accept": "*/*"
    }
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code != 200:
            return None, f"HTTP {r.status_code} — Veri bulunamadı ({tarih.strftime('%d.%m.%Y')})"
        z = zipfile.ZipFile(io.BytesIO(r.content))
        dosyalar = z.namelist()
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
        if len(df) > 0:
            df = df.iloc[1:].reset_index(drop=True)
        if df.shape[1] > 2:
            col_c = df.columns[2]
            df = df[df[col_c].astype(str).str.startswith("TRT")].reset_index(drop=True)
        return df, None
    except Exception as e:
        return None, str(e)


@st.cache_data(ttl=3600, show_spinner=False)
def evds_dibs_cek():
    baslangic = "11-09-2020"
    bitis     = date.today().strftime("%d-%m-%Y")
    url = (
        "https://evds3.tcmb.gov.tr/igmevdsms-dis/series="
        "TP.DIBSPIYDEG.ST-TP.DIBSPIYDEG.S2"
        f"&startDate={baslangic}&endDate={bitis}"
        "&type=json&frequency=2"
    )
    headers = {"key": EVDS_KEY}
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code != 200:
            return None, f"EVDS HTTP {r.status_code}"
        data = r.json()
        items = data.get("items", [])
        if not items:
            return None, "EVDS'den veri gelmedi."
        satirlar = []
        for item in items:
            tarih_str = item.get("Tarih", "")
            s1 = item.get("TP_DIBSPIYDEG_ST", "")
            s2 = item.get("TP_DIBSPIYDEG_S2", "")
            if not tarih_str:
                continue
            try:
                tarih = datetime.strptime(tarih_str, "%d-%m-%Y").date()
            except Exception:
                continue
            s1_val = float(s1.replace(",", ".")) if s1 and s1 != "" else None
            s2_val = float(s2.replace(",", ".")) if s2 and s2 != "" else None
            oran   = None
            if s1_val and s2_val and (s1_val + s2_val) > 0:
                oran = s2_val / (s1_val + s2_val)
            satirlar.append({
                "Tarih":               tarih,
                "Toplam Ekonomi (S1)": s1_val,
                "Dünyanın Geri Kalanı (S2)": s2_val,
                "Yabancı Pay (S2/Toplam)": oran
            })
        df = pd.DataFrame(satirlar).sort_values("Tarih").reset_index(drop=True)
        return df, None
    except Exception as e:
        return None, str(e)


# ─────────────────────────────────────────────
# SAYFA SEÇİMİ
# ─────────────────────────────────────────────

sayfa = st.sidebar.radio(
    "Sayfa",
    ["📊 Günlük Bülten (BIST)", "🏦 DİBS Piyasa Değeri (TCMB)"],
    label_visibility="collapsed"
)

# ═════════════════════════════════════════════
# SAYFA 1 — BIST GÜNLÜK BÜLTEN
# ═════════════════════════════════════════════

if sayfa == "📊 Günlük Bülten (BIST)":

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown('<div class="header-title">📊 TL Bono Piyasası</div>', unsafe_allow_html=True)
        st.markdown('<div class="header-sub">BIST Borçlanma Araçları Piyasası — Günlük Bülten</div>', unsafe_allow_html=True)
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f'<div class="badge">🗓 Bugün: {date.today().strftime("%d.%m.%Y")}</div>', unsafe_allow_html=True)

    st.markdown("---")

    secilen_tarih = st.date_input(
        "Veri tarihi",
        value=onceki_is_gunu(),
        max_value=date.today(),
        format="DD.MM.YYYY"
    )

    with st.spinner(f"{secilen_tarih.strftime('%d.%m.%Y')} verisi indiriliyor..."):
        df, hata = bist_veri_cek(secilen_tarih)

    if hata:
        st.error(f"⚠️ {hata}")
        st.info("Farklı bir tarih seçin veya o gün piyasa kapalı olabilir.")
        st.stop()

    if df is None or df.empty:
        st.warning("Seçilen tarih için TRT ile başlayan kayıt bulunamadı.")
        st.stop()

    st.markdown(f'<div class="badge">✅ {secilen_tarih.strftime("%d.%m.%Y")} — {len(df):,} kayıt</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    kolonlar       = df.columns.tolist()
    sayi_kolonlari = df.select_dtypes(include="number").columns.tolist()
    col_c          = kolonlar[2] if len(kolonlar) > 2 else None

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
            st.markdown(f"""<div class="metric-card">
                <div class="metric-label">{sayi_kolonlari[0]}</div>
                <div class="metric-value">{df[sayi_kolonlari[0]].sum():,.0f}</div>
            </div>""", unsafe_allow_html=True)
    with m4:
        if len(sayi_kolonlari) > 1:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-label">{sayi_kolonlari[1]} Ort.</div>
                <div class="metric-value">{df[sayi_kolonlari[1]].mean():,.2f}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    if sayi_kolonlari and col_c:
        st.markdown("### 📉 Grafik")
        g1, g2 = st.columns(2)
        with g1:
            sec1    = st.selectbox("Sütun seç", sayi_kolonlari, key="g1")
            df_top  = df.groupby(col_c)[sec1].sum().nlargest(15).reset_index()
            fig     = px.bar(df_top, x=sec1, y=col_c, orientation="h",
                             title=f"İlk 15 — {sec1}", color=sec1,
                             color_continuous_scale=["#2d3250", "#64ffda"])
            fig.update_layout(paper_bgcolor="#1e2130", plot_bgcolor="#1e2130",
                              font=dict(color="#8892b0"),
                              xaxis=dict(gridcolor="#2d3250"),
                              yaxis=dict(gridcolor="#2d3250", categoryorder="total ascending"),
                              margin=dict(l=10, r=10, t=40, b=10),
                              height=400, showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        with g2:
            sec2   = st.selectbox("Sütun seç", sayi_kolonlari, key="g2", index=min(1, len(sayi_kolonlari)-1))
            df_pie = df.groupby(col_c)[sec2].sum().nlargest(10).reset_index()
            fig2   = px.pie(df_pie, values=sec2, names=col_c,
                            title=f"Dağılım — {sec2} (İlk 10)",
                            color_discrete_sequence=px.colors.sequential.Teal)
            fig2.update_layout(paper_bgcolor="#1e2130", font=dict(color="#8892b0"),
                               margin=dict(l=10, r=10, t=40, b=10), height=400)
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.markdown(f"### 📋 Veri Tablosu ({len(df):,} satır)")
    st.dataframe(df, use_container_width=True, height=500, hide_index=True)

    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ CSV olarak indir", data=csv,
                       file_name=f"tl_bono_{secilen_tarih.strftime('%Y%m%d')}.csv",
                       mime="text/csv")


# ═════════════════════════════════════════════
# SAYFA 2 — DİBS PİYASA DEĞERİ (TCMB/EVDS)
# ═════════════════════════════════════════════

elif sayfa == "🏦 DİBS Piyasa Değeri (TCMB)":

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown('<div class="header-title">🏦 DİBS Piyasa Değeri</div>', unsafe_allow_html=True)
        st.markdown('<div class="header-sub">TCMB EVDS — Haftalık, milyon TL</div>', unsafe_allow_html=True)
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f'<div class="badge">🗓 Bugün: {date.today().strftime("%d.%m.%Y")}</div>', unsafe_allow_html=True)

    st.markdown("---")

    with st.spinner("TCMB EVDS'den veri çekiliyor..."):
        df_evds, hata_evds = evds_dibs_cek()

    if hata_evds:
        st.error(f"⚠️ {hata_evds}")
        st.stop()

    if df_evds is None or df_evds.empty:
        st.warning("Veri bulunamadı.")
        st.stop()

    st.markdown(f'<div class="badge">✅ {len(df_evds):,} haftalık veri yüklendi</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Son satır metrikleri
    son = df_evds.dropna(subset=["Toplam Ekonomi (S1)"]).iloc[-1]

    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">Toplam Ekonomi (S1)</div>
            <div class="metric-value">{son['Toplam Ekonomi (S1)']:,.0f}</div>
        </div>""", unsafe_allow_html=True)
    with m2:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">Dünyanın Geri Kalanı (S2)</div>
            <div class="metric-value">{son['Dünyanın Geri Kalanı (S2)']:,.0f}</div>
        </div>""", unsafe_allow_html=True)
    with m3:
        oran_pct = son['Yabancı Pay (S2/Toplam)']
        oran_str = f"{oran_pct:.1%}" if oran_pct else "—"
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">Yabancı Pay (S2 / Toplam)</div>
            <div class="metric-value">{oran_str}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown(f"*Son veri tarihi: {son['Tarih'].strftime('%d.%m.%Y')}*")
    st.markdown("---")

    # Grafik
    st.markdown("### 📉 Grafikler")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_evds["Tarih"], y=df_evds["Toplam Ekonomi (S1)"],
        name="Toplam Ekonomi (S1)", line=dict(color="#64ffda", width=2),
        fill="tozeroy", fillcolor="rgba(100,255,218,0.05)"
    ))
    fig.add_trace(go.Scatter(
        x=df_evds["Tarih"], y=df_evds["Dünyanın Geri Kalanı (S2)"],
        name="Dünyanın Geri Kalanı (S2)", line=dict(color="#ff6b8a", width=2),
        fill="tozeroy", fillcolor="rgba(255,107,138,0.05)"
    ))
    fig.update_layout(
        title="DİBS Piyasa Değeri (milyon TL)",
        paper_bgcolor="#1e2130", plot_bgcolor="#1e2130",
        font=dict(color="#8892b0"),
        xaxis=dict(gridcolor="#2d3250"),
        yaxis=dict(gridcolor="#2d3250"),
        legend=dict(bgcolor="#1e2130"),
        margin=dict(l=10, r=10, t=50, b=10),
        height=380
    )
    st.plotly_chart(fig, use_container_width=True)

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=df_evds["Tarih"], y=df_evds["Yabancı Pay (S2/Toplam)"],
        name="Yabancı Pay", line=dict(color="#f7c59f", width=2),
        fill="tozeroy", fillcolor="rgba(247,197,159,0.08)"
    ))
    fig2.update_layout(
        title="Yabancı Pay — S2 / (S1 + S2)",
        paper_bgcolor="#1e2130", plot_bgcolor="#1e2130",
        font=dict(color="#8892b0"),
        xaxis=dict(gridcolor="#2d3250"),
        yaxis=dict(gridcolor="#2d3250", tickformat=".1%"),
        margin=dict(l=10, r=10, t=50, b=10),
        height=300
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.markdown(f"### 📋 Veri Tablosu ({len(df_evds):,} satır)")

    df_goster = df_evds.copy()
    df_goster["Tarih"] = df_goster["Tarih"].apply(lambda x: x.strftime("%d.%m.%Y"))
    df_goster["Yabancı Pay (S2/Toplam)"] = df_goster["Yabancı Pay (S2/Toplam)"].apply(
        lambda x: f"{x:.2%}" if pd.notna(x) else ""
    )
    st.dataframe(df_goster.iloc[::-1].reset_index(drop=True),
                 use_container_width=True, height=400, hide_index=True)

    csv2 = df_evds.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ CSV olarak indir", data=csv2,
                       file_name="dibs_piyasa_degeri.csv", mime="text/csv")
