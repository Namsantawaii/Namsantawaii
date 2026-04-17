from __future__ import annotations

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

from collector.encar_parser import load_html_from_input, parse_encar_listings

st.set_page_config(page_title="Encar Listing Analyzer", layout="wide")
st.title("엔카 매물 분석기")
st.caption("엔카 검색결과 URL 또는 HTML을 입력해 가격/주행거리 분포를 확인하세요.")

source = st.text_area(
    "엔카 검색결과 URL 또는 HTML",
    height=180,
    placeholder="https://www.encar.com/... 또는 HTML 소스를 붙여넣으세요",
)

if st.button("파싱 실행", type="primary"):
    try:
        html = load_html_from_input(source)
        st.session_state["df"] = parse_encar_listings(html)
    except Exception as exc:  # noqa: BLE001
        st.error(f"파싱 실패: {exc}")


df = st.session_state.get("df")
if df is None:
    st.info("먼저 URL/HTML 입력 후 파싱 실행 버튼을 눌러주세요.")
    st.stop()

if df.empty:
    st.warning("매물을 찾지 못했습니다. 입력 HTML 구조를 확인해주세요.")
    st.stop()

price_col = df["price_manwon"].dropna()
mileage_col = df["mileage_km"].dropna()
year_col = df["year"].dropna().astype(int)

st.subheader("필터")
col1, col2, col3 = st.columns(3)
with col1:
    years = sorted(year_col.unique().tolist()) if not year_col.empty else []
    selected_years = st.multiselect("연식", years, default=years)
with col2:
    if price_col.empty:
        min_price, max_price = 0, 0
    else:
        min_price, max_price = int(price_col.min()), int(price_col.max())
    if min_price == max_price:
        st.number_input("가격(만원)", value=min_price, disabled=True)
        selected_price = (min_price, max_price)
    else:
        selected_price = st.slider("가격(만원)", min_price, max_price, (min_price, max_price))
with col3:
    if mileage_col.empty:
        min_km, max_km = 0, 0
    else:
        min_km, max_km = int(mileage_col.min()), int(mileage_col.max())
    if min_km == max_km:
        st.number_input("주행거리(km)", value=min_km, disabled=True)
        selected_km = (min_km, max_km)
    else:
        selected_km = st.slider("주행거리(km)", min_km, max_km, (min_km, max_km))

filtered = df.copy()
if selected_years:
    filtered = filtered[filtered["year"].isin(selected_years)]
filtered = filtered[
    filtered["price_manwon"].between(selected_price[0], selected_price[1], inclusive="both")
    & filtered["mileage_km"].between(selected_km[0], selected_km[1], inclusive="both")
]

st.subheader("주행거리 vs 가격")
fig = px.scatter(
    filtered,
    x="mileage_km",
    y="price_manwon",
    color="year",
    text="year",
    hover_data=["name", "detail_link"],
    labels={"mileage_km": "주행거리(km)", "price_manwon": "가격(만원)", "year": "연식"},
)
fig.update_traces(marker={"size": 9, "opacity": 0.8})
fig.update_traces(textposition="top center")

trend_source = filtered.dropna(subset=["mileage_km", "price_manwon"])
if len(trend_source) >= 2:
    x = trend_source["mileage_km"].astype(float).to_numpy()
    y = trend_source["price_manwon"].astype(float).to_numpy()
    slope, intercept = np.polyfit(x, y, 1)
    x_line = np.linspace(x.min(), x.max(), 100)
    y_line = slope * x_line + intercept
    fig.add_trace(
        go.Scatter(
            x=x_line,
            y=y_line,
            mode="lines",
            name="추세선",
            line={"color": "black", "width": 2},
        )
    )
st.plotly_chart(fig, use_container_width=True)

st.subheader(f"매물 테이블 ({len(filtered)}건)")
st.dataframe(filtered, use_container_width=True)

csv_data = filtered.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label="CSV 다운로드",
    data=csv_data,
    file_name="encar_filtered_listings.csv",
    mime="text/csv",
)
