"""tabs/tab6.py — 몰전체 비교"""
import streamlit as st
import plotly.graph_objects as go
from .utils import *
from ai_insight import render_insight_btn, make_prompt_mall
from .clipboard import copy_button, make_text_mall


def render(data: dict, meta: dict):
    t6 = data.get("tab6_mall", {})
    kpi = t6.get("kpi", {})
    cat_rows = t6.get("cat_signal_rows", [])

    warn_box("몰전체_26 시트는 MTD 집계 기준. 전년 전체와 직접 YoY 비교 시 주의.")

    # ── 섹션1: KPI 테이블 ──
    section("몰전체 vs 제휴 핵심 KPI")
    c1, c2 = st.columns([1.4, 1])

    with c1:
        pct_pp = kpi.get("af_mall_pct_pp") or 0
        pct_hl = "background:#dbeafe" if pct_pp > 0 else ("background:#fff3cd" if pct_pp < 0 else "")
        rows_html = f"""
        <tr><td>몰전체 거래액</td>
            <td class="r">{fmt_M(kpi.get('mall_rev_25'))}</td>
            <td class="r">{fmt_M(kpi.get('mall_rev_26'))}</td>
            <td class="r">{yoy_badge(kpi.get('mall_rev_yoy'))}</td></tr>
        <tr><td>제휴 당월인증거래액</td>
            <td class="r">{fmt_M(kpi.get('af_rev_25'))}</td>
            <td class="r">{fmt_M(kpi.get('af_rev_26'))}</td>
            <td class="r">{yoy_badge(kpi.get('af_rev_yoy'))}</td></tr>
        <tr style="{pct_hl}">
            <td><b>제휴/몰전체 비중</b></td>
            <td class="r">{fmt_pct(kpi.get('af_mall_pct_25'))}</td>
            <td class="r">{fmt_pct(kpi.get('af_mall_pct_26'))}</td>
            <td class="r" style="color:{'#16a34a' if pct_pp>=0 else '#dc2626'};font-weight:600">{fmt_pp(pct_pp)}</td></tr>
        <tr><td>몰전체 주문고객수</td>
            <td class="r">{fmt_n(kpi.get('mall_cust_25'))}</td>
            <td class="r">{fmt_n(kpi.get('mall_cust_26'))}</td>
            <td class="r">-</td></tr>
        <tr><td>제휴 구매고객수</td>
            <td class="r">{fmt_n(kpi.get('af_buyers_25'))}</td>
            <td class="r">{fmt_n(kpi.get('af_buyers_26'))}</td>
            <td class="r">-</td></tr>
        """
        st.markdown(f"""
        <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;font-size:.76rem">
          <thead><tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb">
            <th style="padding:7px 8px;text-align:left">구분</th>
            <th style="padding:7px 8px;text-align:right">2025 MTD</th>
            <th style="padding:7px 8px;text-align:right">2026 MTD</th>
            <th style="padding:7px 8px;text-align:right">YoY</th>
          </tr></thead>
          <tbody>{rows_html}</tbody>
        </table></div>
        """, unsafe_allow_html=True)

    with c2:
        # 카테 YoY 비교 차트 (상위 8개)
        top8 = [r for r in cat_rows if r.get("mall_yoy") is not None][:8]
        if top8:
            cats = [r["cat"][:6] for r in top8]
            mall_yoys = [r.get("mall_yoy") or 0 for r in top8]
            af_yoys   = [r.get("af_yoy") or 0 for r in top8]
            fig = go.Figure()
            fig.add_trace(go.Bar(name="몰전체 YoY", x=cats, y=mall_yoys, marker_color=C["gray"]))
            fig.add_trace(go.Bar(name="제휴 YoY", x=cats, y=af_yoys, marker_color=C["primary"]))
            fig.update_layout(barmode="group", height=260,
                              margin=dict(l=0,r=0,t=20,b=0),
                              legend=dict(orientation="h",y=1.15),
                              plot_bgcolor="white", paper_bgcolor="white")
            fig.update_yaxes(gridcolor="#e5e7eb", ticksuffix="%")
            st.plotly_chart(fig, use_container_width=True)

    # ── 섹션2: 카테고리 시그널 테이블 ──
    section("카테고리별 몰전체 vs 제휴 YoY 비교 (전체 카테고리)")
    if cat_rows:
        rows_html = ""
        for r in cat_rows:
            rows_html += f"""
            <tr>
              <td>{r['cat']}</td>
              <td class="r">{fmt_M(r.get('mall_rev_26'))}</td>
              <td class="r">{fmt_M(r.get('mall_rev_25'))}</td>
              <td class="r">{yoy_badge(r.get('mall_yoy'))}</td>
              <td class="r">{fmt_M(r.get('af_rev_26'))}</td>
              <td class="r">{yoy_badge(r.get('af_yoy'))}</td>
              <td>{sig_badge(r.get('signal',''))}</td>
            </tr>"""
        st.markdown(f"""
        <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;font-size:.75rem">
          <thead><tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb">
            <th style="padding:6px 8px;text-align:left">카테고리</th>
            <th style="padding:6px 8px;text-align:right">몰 2026(M)</th>
            <th style="padding:6px 8px;text-align:right">몰 2025(M)</th>
            <th style="padding:6px 8px;text-align:right">몰 YoY</th>
            <th style="padding:6px 8px;text-align:right">제휴 2026(M)</th>
            <th style="padding:6px 8px;text-align:right">제휴 YoY</th>
            <th style="padding:6px 8px;text-align:left">시그널</th>
          </tr></thead>
          <tbody>{rows_html}</tbody>
        </table></div>
        """, unsafe_allow_html=True)

    # ── 섹션3: 브랜드 시그널 ──
    section("브랜드 시그널")
    b1, b2 = st.columns(2)

    def _brd_tbl(rows, title, color):
        rows_html = "".join([f"""
        <tr>
          <td>{r['brand']}</td><td>{r.get('cat','-')}</td>
          <td class="r">{yoy_badge(r.get('mall_yoy'))}</td>
          <td class="r">{yoy_badge(r.get('af_yoy'))}</td>
        </tr>""" for r in rows])
        return f"""
        <div style="font-size:.82rem;font-weight:600;color:{color};margin-bottom:6px">{title}</div>
        <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;font-size:.75rem">
          <thead><tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb">
            <th style="padding:6px 8px;text-align:left">브랜드</th>
            <th style="padding:6px 8px;text-align:left">카테고리</th>
            <th style="padding:6px 8px;text-align:right">몰 YoY</th>
            <th style="padding:6px 8px;text-align:right">제휴 YoY</th>
          </tr></thead>
          <tbody>{rows_html}</tbody>
        </table></div>"""

    with b1:
        st.markdown(_brd_tbl(t6.get("brand_star",[]), "★ 몰↓ 제휴↑ — 제휴 노출 강화 대상", "#1e40af"), unsafe_allow_html=True)
    with b2:
        st.markdown(_brd_tbl(t6.get("brand_warn",[]), "⚠ 몰↑ 제휴↓ — 제휴 고객 이탈, CRM 필요", "#991b1b"), unsafe_allow_html=True)

    st.markdown("---")
    copy_button(make_text_mall(data), "📋 몰전체 비교 데이터 복사 → Claude에 붙여넣기", key="copy_tab6")
    render_insight_btn("몰전체 비교 인사이트 생성", make_prompt_mall(data), key="ai_tab6")
