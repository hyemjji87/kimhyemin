"""tabs/tab1.py — 전체 Overview"""
import streamlit as st
import pandas as pd
from .utils import *
from ai_insight import render_insight_btn, make_prompt_overview
from .clipboard import copy_button, make_text_overview


def render(data: dict, meta: dict):
    t1 = data.get("tab1_overview", {})
    kpi = t1.get("kpi_total", {})

    # ── KPI 카드 7종 ──
    section("핵심 KPI")
    cols = st.columns(7)
    items = [
        ("UV", fmt_n(kpi.get("uv_26")), fmt_n(kpi.get("uv_25")), kpi.get("uv_yoy")),
        ("인증수", fmt_n(kpi.get("cert_26")), fmt_n(kpi.get("cert_25")), kpi.get("cert_yoy")),
        ("당월인증거래액", fmt_M(kpi.get("revenue_26")), fmt_M(kpi.get("revenue_25")), kpi.get("revenue_yoy")),
        ("구매고객수", fmt_n(kpi.get("buyers_26")), fmt_n(kpi.get("buyers_25")), kpi.get("buyers_yoy")),
        ("CR", fmt_pct(kpi.get("cr_26")), fmt_pct(kpi.get("cr_25")), kpi.get("cr_yoy")),
        ("객단가", fmt_M(kpi.get("arpu_26")), fmt_M(kpi.get("arpu_25")), kpi.get("arpu_yoy")),
        ("인증당거래액", fmt_M(kpi.get("rev_per_cert_26")), fmt_M(kpi.get("rev_per_cert_25")), kpi.get("rev_per_cert_yoy")),
    ]
    for col, (label, val, prev, yoy) in zip(cols, items):
        with col:
            st.markdown(kpi_card(label, val, prev, yoy), unsafe_allow_html=True)

    # ── 제휴사별 요약 테이블 ──
    section("제휴사별 성과 요약")
    af_rows = t1.get("affiliate_summary", [])
    if af_rows:
        rows_html = ""
        for r in af_rows:
            is_new = r.get("is_new", False)
            rows_html += f"""
            <tr>
              <td>{r['name']}</td>
              <td class="r">{fmt_M(r.get('revenue_26'))}</td>
              <td class="r">{fmt_M(r.get('revenue_25')) if not is_new else '-'}</td>
              <td class="r">{yoy_badge(r.get('yoy_pct'), is_new)}</td>
              <td class="r">{fmt_n(r.get('cert_26'))}</td>
              <td class="r">{fmt_n(r.get('cert_25')) if not is_new else '-'}</td>
              <td class="r">{yoy_badge(r.get('cert_26')/r.get('cert_25')*100-100 if r.get('cert_25') else None, is_new)}</td>
              <td class="r">{fmt_pct(r.get('cr_26'))}</td>
              <td class="r">{fmt_pct(r.get('cr_25')) if not is_new else '-'}</td>
              <td class="r" style="color:{'#16a34a' if (r.get('cr_26') or 0)-(r.get('cr_25') or 0)>=0 else '#dc2626'}">{fmt_pp((r.get('cr_26') or 0)-(r.get('cr_25') or 0)) if not is_new else '-'}</td>
              <td class="r">{fmt_n(r.get('uv_26'))}</td>
              <td class="r">{fmt_n(r.get('uv_25')) if not is_new else '-'}</td>
              <td class="r">{yoy_badge((r.get('uv_26') or 0)/(r.get('uv_25') or 1)*100-100 if r.get('uv_25') else None, is_new)}</td>
            </tr>"""

        st.markdown(f"""
        <div style="overflow-x:auto">
        <table class="tbl" style="width:100%;border-collapse:collapse;font-size:.76rem">
          <thead><tr style="background:#f8fafc">
            <th>제휴사</th>
            <th class="r">거래액 26</th><th class="r">거래액 25</th><th class="r">YoY</th>
            <th class="r">인증수 26</th><th class="r">인증수 25</th><th class="r">인증 YoY</th>
            <th class="r">CR 26</th><th class="r">CR 25</th><th class="r">CR △%p</th>
            <th class="r">UV 26</th><th class="r">UV 25</th><th class="r">UV YoY</th>
          </tr></thead>
          <tbody>{rows_html}</tbody>
        </table></div>
        <style>
        .tbl th,.tbl td{{padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:left}}
        .tbl th{{background:#f8fafc;font-size:.72rem;font-weight:600;color:#374151;border-bottom:2px solid #e5e7eb}}
        .r{{text-align:right!important}}
        </style>
        """, unsafe_allow_html=True)

    # ── 일자별 거래액 추이 ──
    section("일자별 당월인증거래액 추이")
    daily = t1.get("daily_trend", [])
    if daily:
        labels = [d["date_26"][-5:] for d in daily]  # MM-DD
        vals26 = [d.get("rev_26") or 0 for d in daily]
        vals25 = [d.get("rev_25") or 0 for d in daily]
        fig = bar_line_chart(labels, vals26, vals25, bar_name="2026", line_name="2025(전년동기)")
        st.plotly_chart(fig, use_container_width=True)

    # ── AI 인사이트 ──
    st.markdown("---")
    copy_button(make_text_overview(data), "📋 Overview 데이터 복사 → Claude에 붙여넣기", key="copy_tab1")
    render_insight_btn(
        "Overview 종합 인사이트 생성",
        make_prompt_overview(data),
        key="ai_tab1"
    )
