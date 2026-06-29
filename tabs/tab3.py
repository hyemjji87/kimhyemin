"""tabs/tab3.py — 제휴사별 전년비"""
import streamlit as st
from .utils import *
from .clipboard import copy_button, make_text_affiliate


def render(data: dict, meta: dict):
    t3 = data.get("tab3_affiliate", {})
    t1_af = data.get("tab1_overview", {}).get("affiliate_summary", [])
    af_list = [r["name"] for r in t1_af]

    if not af_list:
        st.info("제휴사 데이터 없음")
        return

    # 제휴사 선택 탭
    selected = st.selectbox("제휴사 선택", af_list, key="tab3_af")
    af_data = t3.get(selected, {})
    af_meta = next((r for r in t1_af if r["name"] == selected), {})

    if not af_data:
        st.warning(f"{selected} 데이터 없음")
        return

    is_new = af_data.get("is_new", False)

    # ── KPI 카드 4종 ──
    section(f"{selected} 핵심 KPI")
    cols = st.columns(4)
    items = [
        ("UV", fmt_n(af_meta.get("uv_26")), fmt_n(af_meta.get("uv_25")),
         (af_meta.get("uv_26") or 0)/(af_meta.get("uv_25") or 1)*100-100 if af_meta.get("uv_25") else None),
        ("인증수", fmt_n(af_meta.get("cert_26")), fmt_n(af_meta.get("cert_25")),
         (af_meta.get("cert_26") or 0)/(af_meta.get("cert_25") or 1)*100-100 if af_meta.get("cert_25") else None),
        ("당월인증거래액", fmt_M(af_meta.get("revenue_26")), fmt_M(af_meta.get("revenue_25")), af_meta.get("yoy_pct")),
        ("CR", fmt_pct(af_meta.get("cr_26")), fmt_pct(af_meta.get("cr_25")),
         (af_meta.get("cr_26") or 0) - (af_meta.get("cr_25") or 0) if not is_new else None),
    ]
    for col, (label, val, prev, yoy) in zip(cols, items):
        with col:
            if is_new:
                st.markdown(kpi_card(label, val, None, None) + '<div style="margin-top:-6px"><span class="badge-new">신규</span></div>', unsafe_allow_html=True)
            else:
                st.markdown(kpi_card(label, val, prev, yoy), unsafe_allow_html=True)

    # ── 카테고리 / 브랜드 서브탭 ──
    sub = st.tabs(["📦 카테고리", "🏷️ 브랜드 TOP7"])

    with sub[0]:
        cat_rows = af_data.get("cat_rows", [])
        af_tot26 = af_data.get("af_total_26", 0)
        af_tot25 = af_data.get("af_total_25", 0)

        if cat_rows:
            rows_html = ""
            for r in cat_rows:
                yoy_v = r.get("yoy_pct")
                wt_pp = r.get("wt_pp") or 0
                hl = 'style="background:#dbeafe"' if wt_pp >= 3 else ('style="background:#fff3cd"' if wt_pp <= -3 else '')
                rows_html += f"""
                <tr>
                  <td>{r['cat']}</td>
                  <td class="r">{fmt_M(r.get('rev_26'))}</td>
                  <td class="r">{fmt_M(r.get('rev_25')) if not is_new else '-'}</td>
                  <td class="r">{yoy_badge(yoy_v, is_new)}</td>
                  <td class="r">{fmt_pct(r.get('wt_25')) if not is_new else '-'}</td>
                  <td class="r">{fmt_pct(r.get('wt_26'))}</td>
                  <td class="r" {hl} style="color:{'#16a34a' if wt_pp>=0 else '#dc2626'};font-weight:600{';background:#dbeafe' if wt_pp>=3 else (';background:#fff3cd' if wt_pp<=-3 else '')}">{fmt_pp(wt_pp) if not is_new else '-'}</td>
                </tr>"""
            st.markdown(f"""
            <div style="overflow-x:auto">
            <table style="width:100%;border-collapse:collapse;font-size:.76rem">
              <thead><tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb">
                <th style="padding:7px 8px;text-align:left">카테고리</th>
                <th style="padding:7px 8px;text-align:right">2026(M)</th>
                <th style="padding:7px 8px;text-align:right">2025(M)</th>
                <th style="padding:7px 8px;text-align:right">YoY</th>
                <th style="padding:7px 8px;text-align:right">비중 2025</th>
                <th style="padding:7px 8px;text-align:right">비중 2026</th>
                <th style="padding:7px 8px;text-align:right">비중△%p</th>
              </tr></thead>
              <tbody>{rows_html}</tbody>
            </table></div>
            <p style="font-size:.7rem;color:#9ca3af;margin-top:4px">* 비중△ ±3%p 이상 강조</p>
            """, unsafe_allow_html=True)

    with sub[1]:
        brd_rows = af_data.get("brd_rows", [])
        if brd_rows:
            rows_html = ""
            for r in brd_rows:
                rows_html += f"""
                <tr>
                  <td>{r['brand']}</td>
                  <td class="r">{fmt_M(r.get('rev_26'))}</td>
                  <td class="r">{fmt_M(r.get('rev_25')) if not is_new else '-'}</td>
                  <td class="r">{yoy_badge(r.get('yoy_pct'), is_new)}</td>
                </tr>"""
            st.markdown(f"""
            <div style="overflow-x:auto">
            <table style="width:100%;border-collapse:collapse;font-size:.76rem">
              <thead><tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb">
                <th style="padding:7px 8px;text-align:left">브랜드</th>
                <th style="padding:7px 8px;text-align:right">2026(M)</th>
                <th style="padding:7px 8px;text-align:right">2025(M)</th>
                <th style="padding:7px 8px;text-align:right">YoY</th>
              </tr></thead>
              <tbody>{rows_html}</tbody>
            </table></div>
            """, unsafe_allow_html=True)

    st.markdown('---')
    copy_button(make_text_affiliate(data, selected), f'📋 {selected} 데이터 복사 → Claude에 붙여넣기', key='copy_tab3')
