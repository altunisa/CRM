from __future__ import annotations

import pandas as pd
import requests
import streamlit as st

API_BASE = st.secrets.get("api_base", "http://localhost:8000")

st.set_page_config(page_title="BKÜ Akıllı CRM", layout="wide")
st.title("BKÜ Akıllı CRM / Fırsat Motoru")

page = st.sidebar.radio("Modül", ["Firma Merkezi", "Fırsat Merkezi"])

if page == "Firma Merkezi":
    st.header("Firma Merkezi")
    col1, col2, col3 = st.columns(3)
    with col1:
        q = st.text_input("Firma Ara")
        il = st.text_input("İl")
    with col2:
        ilce = st.text_input("İlçe")
        firma_tipi = st.selectbox("Firma Tipi", ["", "ruhsat_sahibi", "kanal"])
    with col3:
        hedef_iliski = st.selectbox("Hedef İlişki", ["", "portfoy_isbirligi", "rakip_izleme", "satis_kanali"])
        segment = st.selectbox("Segment", ["", "stratejik", "kanal", "standart"])

    ruhsat_sahibi = st.selectbox("Ruhsat Sahibi", ["", "evet", "hayır"])
    bayi = st.selectbox("Bayi", ["", "evet", "hayır"])

    params = {
        "q": q or None,
        "il": il or None,
        "ilce": ilce or None,
        "firma_tipi_ana": firma_tipi or None,
        "hedef_iliski_tipi": hedef_iliski or None,
        "firma_segment": segment or None,
        "ruhsat_sahibi": True if ruhsat_sahibi == "evet" else False if ruhsat_sahibi == "hayır" else None,
        "bayi": True if bayi == "evet" else False if bayi == "hayır" else None,
        "limit": 300,
    }
    data = requests.get(f"{API_BASE}/crm/firms", params={k: v for k, v in params.items() if v is not None}, timeout=30).json()
    st.dataframe(pd.DataFrame(data), use_container_width=True)

    if st.button("Classify Çalıştır"):
        r = requests.post(f"{API_BASE}/crm/firms/classify", params={"limit": 1000}, timeout=120)
        st.success(r.json())

    gln = st.text_input("GLN Detay")
    if gln:
        detail = requests.get(f"{API_BASE}/crm/firms/{gln}", timeout=20)
        if detail.status_code == 200:
            st.json(detail.json())

    st.subheader("Top Firmalar")
    top = requests.get(f"{API_BASE}/crm/firms/top/list", params={"limit": 25}, timeout=20).json()
    st.dataframe(pd.DataFrame(top), use_container_width=True)

else:
    st.header("Fırsat Merkezi")
    col1, col2, col3 = st.columns(3)
    with col1:
        urun = st.text_input("Ürün")
    with col2:
        bitki = st.text_input("Bitki")
    with col3:
        il = st.text_input("İl", key="opp_il")

    st.subheader("Bölgesel Fırsatlar")
    opp = requests.get(
        f"{API_BASE}/crm/opportunities", params={"bitki": bitki or None, "il": il or None, "limit": 100}, timeout=30
    ).json()
    st.dataframe(pd.DataFrame(opp), use_container_width=True)

    st.subheader("Ürün → Firma Eşleştirme")
    matches = requests.get(
        f"{API_BASE}/crm/product-match",
        params={"urun": urun or None, "bitki": bitki or None, "il": il or None, "limit": 100},
        timeout=30,
    ).json()
    st.dataframe(pd.DataFrame(matches), use_container_width=True)

    st.subheader("Tavsiye Heatmap")
    heatmap = requests.get(f"{API_BASE}/crm/tavsiyeler/heatmap", params={"bitki": bitki or None, "limit": 100}, timeout=30).json()
    st.dataframe(pd.DataFrame(heatmap), use_container_width=True)

    gln = st.text_input("GLN Önerileri")
    if gln:
        rec = requests.get(f"{API_BASE}/crm/firms/{gln}/recommendations", timeout=20)
        if rec.status_code == 200:
            st.json(rec.json())
