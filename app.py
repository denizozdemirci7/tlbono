import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import date, datetime

st.set_page_config(
    page_title="DİBS Piyasa Değeri | TCMB",
    page_icon="🏦",
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
    .metric-value { color: #e6f1ff; font-size: 26px; font-weight: 700; margin-top: 4px; }
    .header-title { color: #e6f1ff; font-size: 34px; font-weight: 800; }
    .header-sub { color: #8892b0; font-size: 14px; margin-top: -6px; }
    .badge { background: #2d3250; color: #64ffda; font-size: 12px; padding: 4px 12px; border-radius: 20px; display: inline-block; }
</style>
""", unsafe_allow_html=True)

EVDS_KEY = "rZzI65ePpI"


@st.cache_data(ttl=3600, show_spinner=False)
def evds_dibs_cek():
    baslangic = "11-09-2020"
    bitis = date.today().strftime("%d-%m-%Y")
    url = (
        "https://evds3.tcmb.gov.tr/igmevdsms-dis/series="
        "TP.DIBSPIYDEG.ST-TP.DIBSPIYDEG.S2-TP.DIBSPIYDEG.S121-TP.DIBSPIYDEG.S122-TP.DIBSPIYDEG.S129-TP.DIBSPIYDEG.S1234"
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

        def parse(item, key):
            v = item.get(key, "")
            return float(v.replace(",", ".")) if v and v != "" else None

        satirlar = []
        for item in items:
            tarih_str = item.get("Tarih", "")
            if not tarih_str:
                continue
            try:
                tarih = datetime.strptime(tarih_str, "%d-%m-%Y").date()
            except Exception:
                continue

            st_val    = parse(item, "TP_DIBSPIYDEG_ST")
            s2_val    = parse(item, "TP_DIBSPIYDEG_S2")
            s121_val  = parse(item, "TP_DIBSPIYDEG_S121")
            s122_val  = parse(item, "TP_DIBSPIYDEG_S122")
            s129_val  = parse(item, "TP_DIBSPIYDEG_S129")
            s1234_val = parse(item, "TP_DIBSPIYDEG_S1234")

            fonlar_val = None
            if s129_val is not None and s1234_val is not None:
                fonlar_val = s129_val + s1234_val
            elif s129_val is not None:
                fonlar_val = s129_val
            elif s1234_val is not None:
                fonlar_val = s1234_val

            def oran(val):
                if val is not None and st_val and st_val > 0:
                    return val / st_val
                return None

            satirlar.append({
                "Tarih":                     tarih,
                "Toplam (ST)":               st_val,
                "Dünyanın Geri Kalanı (S2)": s2_val,
                "TCMB (S121)":               s121_val,
                "Bankalar (S122)":           s122_val,
                "Fonlar (S129+S1234)":       fonlar_val,
                "Dünyanın Geri Kalanı / Toplam": oran(s2_val),
                "TCMB / Toplam":             oran(s121_val),
                "Bankalar / Toplam":         oran(s122_val),
                "Fonlar / Toplam":           oran(fonlar_val),
            })
        df = pd.DataFrame(satirlar).sort_values("Tarih").reset_index(drop=True)
        return df, None
    except Exception as e:
        return None, str(e)


# --- BAŞLIK ---
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown('<div class="header-title">🏦 DİBS Piyasa Değeri</div>', unsafe_allow_html=True)
    st.markdown('<div class="header-sub">TCMB EVDS — Haftalık, milyon TL</div>', unsafe_allow_html=True)
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f'<div class="badge">🗓 Bugün: {date.today().strftime("%d.%m.%Y")}</div>', unsafe_allow_html=True)

st.markdown("---")

# --- VERİ ÇEK ---
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

son = df_evds.dropna(subset=["Toplam (ST)"]).iloc[-1]

# --- METRİKLER: DEĞERLER ---
st.markdown("#### Piyasa Değerleri (milyon TL)")
m1, m2, m3, m4, m5 = st.columns(5)

def metrik(col, baslik, deger):
    val = f"{deger:,.0f}" if deger is not None and pd.notna(deger) else "—"
    col.markdown(f"""<div class="metric-card">
        <div class="metric-label">{baslik}</div>
        <div class="metric-value">{val}</div>
    </div>""", unsafe_allow_html=True)

metrik(m1, "Toplam (ST)",               son["Toplam (ST)"])
metrik(m2, "Dünyanın Geri Kalanı (S2)", son["Dünyanın Geri Kalanı (S2)"])
metrik(m3, "TCMB (S121)",               son["TCMB (S121)"])
metrik(m4, "Bankalar (S122)",           son["Bankalar (S122)"])
metrik(m5, "Fonlar (S129+S1234)",       son["Fonlar (S129+S1234)"])

st.markdown("<br>", unsafe_allow_html=True)

# --- METRİKLER: ORANLAR ---
st.markdown("#### Toplama Oranlar")
r1, r2, r3, r4 = st.columns(4)

def oran_metrik(col, baslik, oran):
    val = f"{oran:.2%}" if oran is not None and pd.notna(oran) else "—"
    col.markdown(f"""<div class="metric-card">
        <div class="metric-label">{baslik}</div>
        <div class="metric-value">{val}</div>
    </div>""", unsafe_allow_html=True)

oran_metrik(r1, "Dünyanın Geri Kalanı / Toplam", son["Dünyanın Geri Kalanı / Toplam"])
oran_metrik(r2, "TCMB / Toplam",                 son["TCMB / Toplam"])
oran_metrik(r3, "Bankalar / Toplam",             son["Bankalar / Toplam"])
oran_metrik(r4, "Fonlar / Toplam",               son["Fonlar / Toplam"])

st.markdown(f"*Son veri tarihi: {son['Tarih'].strftime('%d.%m.%Y')}*")
st.markdown("---")

# --- GRAFİK 1: PİYASA DEĞERLERİ ---
st.markdown("### 📉 Piyasa Değerleri (milyon TL)")
fig1 = go.Figure()
renkler = {
    "Toplam (ST)":               "#64ffda",
    "Dünyanın Geri Kalanı (S2)": "#ff6b8a",
    "TCMB (S121)":               "#f7c59f",
    "Bankalar (S122)":           "#a8dadc",
    "Fonlar (S129+S1234)":       "#c77dff",
}
for kolon, renk in renkler.items():
    fig1.add_trace(go.Scatter(
        x=df_evds["Tarih"], y=df_evds[kolon],
        name=kolon, line=dict(color=renk, width=2)
    ))
fig1.update_layout(
    paper_bgcolor="#1e2130", plot_bgcolor="#1e2130",
    font=dict(color="#8892b0"),
    xaxis=dict(gridcolor="#2d3250"),
    yaxis=dict(gridcolor="#2d3250"),
    legend=dict(bgcolor="#1e2130"),
    margin=dict(l=10, r=10, t=30, b=10), height=400
)
st.plotly_chart(fig1, use_container_width=True)

# --- GRAFİK 2: ORANLAR ---
st.markdown("### 📊 Toplama Oranlar")
oran_kolonlar = [
    ("Dünyanın Geri Kalanı / Toplam", "#ff6b8a", "rgba(255,107,138,0.08)", "Dünyanın Geri Kalanı / Toplam"),
    ("TCMB / Toplam",                 "#f7c59f", "rgba(247,197,159,0.08)", "TCMB / Toplam"),
    ("Bankalar / Toplam",             "#a8dadc", "rgba(168,218,220,0.08)", "Bankalar / Toplam"),
    ("Fonlar / Toplam",               "#c77dff", "rgba(199,125,255,0.08)", "Fonlar / Toplam"),
]
gc1, gc2 = st.columns(2)
for idx, (kolon, renk, fill, baslik) in enumerate(oran_kolonlar):
    seri = df_evds[["Tarih", kolon]].dropna()

    idx_min = seri[kolon].idxmin()
    idx_max = seri[kolon].idxmax()
    idx_son = seri.index[-1]

    ozel_idx = list({idx_min, idx_max, idx_son})
    ozel_x = [seri.loc[i, "Tarih"] for i in ozel_idx]
    ozel_y = [seri.loc[i, kolon] for i in ozel_idx]
    ozel_label = []
    for i in ozel_idx:
        v = seri.loc[i, kolon]
        if i == idx_son and i == idx_max:
            etiket = f"Son & Max<br>{v:.2%}"
        elif i == idx_son and i == idx_min:
            etiket = f"Son & Min<br>{v:.2%}"
        elif i == idx_son:
            etiket = f"Son<br>{v:.2%}"
        elif i == idx_max:
            etiket = f"Max<br>{v:.2%}"
        else:
            etiket = f"Min<br>{v:.2%}"
        ozel_label.append(etiket)

    fig_o = go.Figure()
    fig_o.add_trace(go.Scatter(
        x=seri["Tarih"], y=seri[kolon],
        name=kolon, line=dict(color=renk, width=2),
        fill="tozeroy", fillcolor=fill
    ))
    fig_o.add_trace(go.Scatter(
        x=ozel_x, y=ozel_y,
        mode="markers+text",
        marker=dict(color=renk, size=8, line=dict(color="#0f1117", width=2)),
        text=ozel_label,
        textposition="top center",
        textfont=dict(color=renk, size=11),
        showlegend=False
    ))
    fig_o.update_layout(
        title=baslik,
        paper_bgcolor="#1e2130", plot_bgcolor="#1e2130",
        font=dict(color="#8892b0"),
        xaxis=dict(gridcolor="#2d3250"),
        yaxis=dict(gridcolor="#2d3250", tickformat=".1%"),
        margin=dict(l=10, r=10, t=40, b=30),
        height=300, showlegend=False
    )
    if idx % 2 == 0:
        gc1.plotly_chart(fig_o, use_container_width=True)
    else:
        gc2.plotly_chart(fig_o, use_container_width=True)

st.markdown("---")

# --- TABLO ---
st.markdown(f"### 📋 Veri Tablosu ({len(df_evds):,} satır)")
df_goster = df_evds.copy()
df_goster["Tarih"] = df_goster["Tarih"].apply(lambda x: x.strftime("%d.%m.%Y"))
for oran_kol in ["Dünyanın Geri Kalanı / Toplam", "TCMB / Toplam", "Bankalar / Toplam", "Fonlar / Toplam"]:
    df_goster[oran_kol] = df_goster[oran_kol].apply(
        lambda x: f"{x:.2%}" if pd.notna(x) and x is not None else ""
    )
st.dataframe(df_goster.iloc[::-1].reset_index(drop=True),
             use_container_width=True, height=400, hide_index=True)

csv = df_evds.to_csv(index=False).encode("utf-8-sig")
st.download_button("⬇️ CSV olarak indir", data=csv,
                   file_name="dibs_piyasa_degeri.csv", mime="text/csv")
