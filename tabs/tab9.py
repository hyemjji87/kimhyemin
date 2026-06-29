"""tabs/tab9.py — 첫구매 분析"""
import streamlit as st
import plotly.graph_objects as go
from .utils import *
from ai_insight import render_insight_btn, make_prompt_first
from .clipboard import copy_button, make_text_first


def render(data: dict, meta: dict):
    t9 = data.get("tab9_first", {})
    kpi = t9.get("kpi", {})
    cat_rows = t9.get("cat_rows", [])
    brd_rows = t9.get("brd_rows", [])

    fp_pct = kpi.get("fp_pct_af", 0)
    if fp_pct < 3 or fp_pct > 20:
        warn_box(f"첫구매 비율 {fp_pct:.1f}% — 정상범위(3~20%) 이탈. 운영팀 확인 필요.")

    # ── KPI ──
    section("전체 요약 KPI")
    cols = st.columns(4)
    items = [
        ("첫구매 거래액", fmt_M(kpi.get("fp_rev_26")), fmt_M(kpi.get("fp_rev_25")), kpi.get("fp_rev_yoy")),
        ("첫구매 고객수", fmt_n(kpi.get("fp_buyers_26")), fmt_n(kpi.get("fp_buyers_25")), None),
        ("제휴채널 대비 비중①", fmt_pct(kpi.get("fp_pct_af")), None, None),
        ("몰전체 대비 제휴 첫구매④", fmt_pct(kpi.get("fp_pct_mall")), None, None),
    ]
    for col, (label, val, prev, yoy) in zip(cols, items):
        with col:
            st.markdown(kpi_card(label, val, prev, yoy), unsafe_allow_html=True)

    # 비중 컬럼 정의 배너 (필수)
    st.markdown("""
    <div style="background:#fff7ed;border-left:4px solid #f59e0b;padding:10px 14px;border-radius:0 6px 6px 0;font-size:.78rem;line-height:1.8;margin:8px 0">
    <b>📌 비중 컬럼 정의</b><br>
    ① 첫구매내 비중: 해당 카테/브랜드 첫구매 거래액 ÷ <b>제휴 전체 첫구매 거래액</b> (합=100%)<br>
    ② 카테/브랜드내 첫구매 비중: 해당 첫구매 거래액 ÷ <b>제휴채널 내 해당 카테/브랜드 전체 거래액</b> (★≥15% 강조)<br>
    ④ 몰전체 대비 제휴 첫구매: 해당 카테 제휴 첫구매 ÷ <b>몰전체 해당 카테 거래액</b>
    </div>
    """, unsafe_allow_html=True)

    # ── 카테고리 테이블 + 차트 ──
    section("카테고리별 첫구매 실적")
    if cat_rows:
        rows_html = ""
        for r in cat_rows:
            w2_hl = "background:#dcfce7;font-weight:700" if r.get("w2_star") else ""
            w2_star = " ★" if r.get("w2_star") else ""
            rows_html += f"""
            <tr>
              <td>{r['cat']}</td>
              <td class="r">{fmt_M(r.get('rev_26'))}</td>
              <td class="r">{fmt_pct(r.get('w1_fp_in_pct'))}</td>
              <td class="r" style="{w2_hl}">{fmt_pct(r.get('w2_fp_in_cat_pct'))}{w2_star}</td>
              <td class="r">{fmt_pct(r.get('w3_cat_in_af_pct'))}</td>
              <td class="r">{fmt_pct(r.get('w4_fp_vs_mall_pct'))}</td>
            </tr>"""
        st.markdown(f"""
        <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;font-size:.76rem">
          <thead><tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb">
            <th style="padding:7px 8px;text-align:left">카테고리</th>
            <th style="padding:7px 8px;text-align:right">첫구매 거래액</th>
            <th style="padding:7px 8px;text-align:right">①첫구매내 비중</th>
            <th style="padding:7px 8px;text-align:right">②카테내 비중(★≥15%)</th>
            <th style="padding:7px 8px;text-align:right">③카테 전체비중</th>
            <th style="padding:7px 8px;text-align:right">④몰전체 대비</th>
          </tr></thead>
          <tbody>{rows_html}</tbody>
        </table></div>
        """, unsafe_allow_html=True)

        # bar(①) + line(②) 차트
        if len(cat_rows) > 0:
            cats = [r["cat"][:6] for r in cat_rows[:12]]
            w1s  = [r.get("w1_fp_in_pct") or 0 for r in cat_rows[:12]]
            w2s  = [r.get("w2_fp_in_cat_pct") or 0 for r in cat_rows[:12]]
            fig = go.Figure()
            fig.add_trace(go.Bar(x=cats, y=w1s, name="①첫구매내 비중", marker_color=C["primary"]))
            fig.add_trace(go.Scatter(x=cats, y=w2s, name="②카테내 비중", mode="lines+markers",
                                     line=dict(color=C["amber"], width=2),
                                     yaxis="y2"))
            fig.update_layout(
                height=300, margin=dict(l=0,r=0,t=30,b=0),
                legend=dict(orientation="h", y=1.15),
                yaxis=dict(title="① 비중(%)", gridcolor="#e5e7eb"),
                yaxis2=dict(title="② 비중(%)", overlaying="y", side="right"),
                plot_bgcolor="white", paper_bgcolor="white",
            )
            st.plotly_chart(fig, use_container_width=True)

    # ── 브랜드 TOP15 ──
    section("브랜드별 첫구매 TOP15")
    if brd_rows:
        rows_html = ""
        for r in brd_rows:
            w2_hl = "background:#dcfce7;font-weight:700" if r.get("w2_star") else ""
            w2_star = " ★" if r.get("w2_star") else ""
            rows_html += f"""
            <tr>
              <td>{r['brand']}</td>
              <td>{r.get('cat','-')[:6]}</td>
              <td class="r">{fmt_M(r.get('rev_26'))}</td>
              <td class="r">{fmt_pct(r.get('w1_fp_in_pct'))}</td>
              <td class="r" style="{w2_hl}">{fmt_pct(r.get('w2_fp_in_brd_pct'))}{w2_star}</td>
            </tr>"""
        st.markdown(f"""
        <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;font-size:.76rem">
          <thead><tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb">
            <th style="padding:7px 8px;text-align:left">브랜드</th>
            <th style="padding:7px 8px;text-align:left">카테고리</th>
            <th style="padding:7px 8px;text-align:right">첫구매 거래액</th>
            <th style="padding:7px 8px;text-align:right">①첫구매내 비중</th>
            <th style="padding:7px 8px;text-align:right">②브랜드내 비중(★≥20%)</th>
          </tr></thead>
          <tbody>{rows_html}</tbody>
        </table></div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    copy_button(make_text_first(data), "📋 첫구매 데이터 복사 → Claude에 붙여넣기", key="copy_tab9")
    render_insight_btn("첫구매 인사이트 생성", make_prompt_first(data), key="ai_tab9")
