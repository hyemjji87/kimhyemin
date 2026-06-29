"""tabs/tab8.py — 회원구분 분析"""
import streamlit as st
from .utils import *
from ai_insight import render_insight_btn, make_prompt_segment
from .clipboard import copy_button, make_text_segment


def render(data: dict, meta: dict):
    t8 = data.get("tab8_segment", {})
    seg_kpi = t8.get("seg_kpi", {})
    cat_rows = t8.get("cat_rows", [])
    brd_rows = t8.get("brd_rows", [])

    # ── 전체 KPI ──
    section("회원구분별 KPI")
    colors = {"신규": "#1e40af", "WIN-BACK": "#7e22ce", "기존": "#166534"}
    cols = st.columns(3)
    for col, (seg, kpi) in zip(cols, seg_kpi.items()):
        with col:
            st.markdown(f"""
            <div style="background:white;border-radius:8px;padding:14px;
                        box-shadow:0 1px 3px rgba(0,0,0,.08);
                        border-left:4px solid {colors.get(seg,'#4f46e5')}">
              <div style="font-size:.75rem;font-weight:700;color:{colors.get(seg,'#374151')};margin-bottom:8px">{seg}</div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:.75rem">
                <div><span style="color:#9ca3af">거래액</span><br><b>{fmt_M(kpi.get('revenue'))}</b>
                  <span style="color:#6b7280">({kpi.get('rev_pct',0):.1f}%)</span></div>
                <div><span style="color:#9ca3af">고객수</span><br><b>{fmt_n(kpi.get('buyers'))}</b></div>
                <div><span style="color:#9ca3af">CR</span><br><b>{fmt_pct(kpi.get('cr'))}</b></div>
                <div><span style="color:#9ca3af">객단가</span><br><b>{fmt_M(kpi.get('arpu'))}</b></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    # ── 카테고리별 회원구분 ──
    section("카테고리별 회원구분 실적")
    st.markdown('<div class="info-box">💡 편차(%p) = 해당 구분의 카테비중 − 제휴 전체 카테비중. ±3%p 이상 강조.</div>', unsafe_allow_html=True)

    if cat_rows:
        def _seg_cells(r, seg):
            rev  = r.get(f"rev_{seg}", 0)
            wt   = r.get(f"wt_{seg}", 0)
            diff = r.get(f"diff_{seg}", 0)
            hl   = "background:#dbeafe" if diff >= 3 else ("background:#fff3cd" if diff <= -3 else "")
            dc   = "#16a34a" if diff >= 0 else "#dc2626"
            return (f'<td style="padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_M(rev)}</td>'
                    f'<td style="padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_pct(wt)}</td>'
                    f'<td style="padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right;{hl};color:{dc};font-weight:600">{fmt_pp(diff)}</td>')

        rows_html = ""
        for r in cat_rows:
            rows_html += f"""<tr>
              <td style="padding:5px 7px;border-bottom:1px solid #f1f5f9">{r['cat']}</td>
              <td style="padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_M(r.get('rev_total'))}</td>
              <td style="padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_n(r.get('buyers_total'))}</td>
              <td style="padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_pct(r.get('wt_total'))}</td>
              {_seg_cells(r,'신규')}{_seg_cells(r,'WIN-BACK')}{_seg_cells(r,'기존')}
            </tr>"""

        st.markdown(f"""
        <div style="overflow-x:auto;background:white;border-radius:8px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,.07)">
        <table style="width:100%;border-collapse:collapse;font-size:.72rem">
          <thead>
            <tr>
              <th rowspan="2" style="padding:6px 7px;text-align:left;border-bottom:2px solid #e5e7eb;background:#f8fafc">카테고리</th>
              <th colspan="3" style="padding:6px 7px;text-align:center;background:#4f46e5;color:white;border-bottom:1px solid #4338ca">제휴 전체</th>
              <th colspan="3" style="padding:6px 7px;text-align:center;background:#eff6ff;color:#1e40af;border-bottom:1px solid #bfdbfe">신규 고객</th>
              <th colspan="3" style="padding:6px 7px;text-align:center;background:#fdf4ff;color:#7e22ce;border-bottom:1px solid #e9d5ff">WIN-BACK</th>
              <th colspan="3" style="padding:6px 7px;text-align:center;background:#f0fdf4;color:#166534;border-bottom:1px solid #bbf7d0">기존 고객</th>
            </tr>
            <tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb">
              <th style="padding:5px 7px;text-align:right">거래액</th><th style="padding:5px 7px;text-align:right">고객수</th><th style="padding:5px 7px;text-align:right">비중%</th>
              <th style="padding:5px 7px;text-align:right;background:#eff6ff">거래액</th><th style="padding:5px 7px;text-align:right;background:#eff6ff">비중%</th><th style="padding:5px 7px;text-align:right;background:#eff6ff">편차%p</th>
              <th style="padding:5px 7px;text-align:right;background:#fdf4ff">거래액</th><th style="padding:5px 7px;text-align:right;background:#fdf4ff">비중%</th><th style="padding:5px 7px;text-align:right;background:#fdf4ff">편차%p</th>
              <th style="padding:5px 7px;text-align:right;background:#f0fdf4">거래액</th><th style="padding:5px 7px;text-align:right;background:#f0fdf4">비중%</th><th style="padding:5px 7px;text-align:right;background:#f0fdf4">편차%p</th>
            </tr>
          </thead>
          <tbody>{rows_html}</tbody>
        </table></div>
        <p style="font-size:.7rem;color:#9ca3af;margin-top:4px">* 편차 ±3%p 이상 강조</p>
        """, unsafe_allow_html=True)

    # ── 브랜드 TOP15 ──
    section("브랜드별 회원구분 실적 TOP15")
    if brd_rows:
        def _seg_cells_brd(r, seg):
            rev  = r.get(f"rev_{seg}", 0)
            wt   = r.get(f"wt_{seg}", 0)
            diff = r.get(f"diff_{seg}", 0)
            hl   = "background:#dbeafe" if diff >= 2 else ("background:#fff3cd" if diff <= -2 else "")
            dc   = "#16a34a" if diff >= 0 else "#dc2626"
            return (f'<td style="padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_M(rev)}</td>'
                    f'<td style="padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_pct(wt)}</td>'
                    f'<td style="padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right;{hl};color:{dc};font-weight:600">{fmt_pp(diff)}</td>')

        rows_html = ""
        for r in brd_rows:
            rows_html += f"""<tr>
              <td style="padding:5px 7px;border-bottom:1px solid #f1f5f9">{r['brand']}</td>
              <td style="padding:5px 7px;border-bottom:1px solid #f1f5f9">{r.get('cat','-')[:6]}</td>
              <td style="padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_M(r.get('rev_total'))}</td>
              <td style="padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_n(r.get('buyers_total'))}</td>
              <td style="padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_pct(r.get('wt_total'))}</td>
              {_seg_cells_brd(r,'신규')}{_seg_cells_brd(r,'WIN-BACK')}{_seg_cells_brd(r,'기존')}
            </tr>"""

        st.markdown(f"""
        <div style="overflow-x:auto;background:white;border-radius:8px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,.07)">
        <table style="width:100%;border-collapse:collapse;font-size:.72rem">
          <thead>
            <tr>
              <th rowspan="2" style="padding:6px 7px;text-align:left;border-bottom:2px solid #e5e7eb;background:#f8fafc">브랜드</th>
              <th rowspan="2" style="padding:6px 7px;text-align:left;border-bottom:2px solid #e5e7eb;background:#f8fafc">카테</th>
              <th colspan="3" style="padding:6px 7px;text-align:center;background:#4f46e5;color:white;border-bottom:1px solid #4338ca">제휴 전체</th>
              <th colspan="3" style="padding:6px 7px;text-align:center;background:#eff6ff;color:#1e40af;border-bottom:1px solid #bfdbfe">신규</th>
              <th colspan="3" style="padding:6px 7px;text-align:center;background:#fdf4ff;color:#7e22ce;border-bottom:1px solid #e9d5ff">WIN-BACK</th>
              <th colspan="3" style="padding:6px 7px;text-align:center;background:#f0fdf4;color:#166534;border-bottom:1px solid #bbf7d0">기존</th>
            </tr>
            <tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb">
              <th style="padding:5px 7px;text-align:right">거래액</th><th style="padding:5px 7px;text-align:right">고객수</th><th style="padding:5px 7px;text-align:right">비중%</th>
              <th style="padding:5px 7px;text-align:right;background:#eff6ff">거래액</th><th style="padding:5px 7px;text-align:right;background:#eff6ff">비중%</th><th style="padding:5px 7px;text-align:right;background:#eff6ff">편차%p</th>
              <th style="padding:5px 7px;text-align:right;background:#fdf4ff">거래액</th><th style="padding:5px 7px;text-align:right;background:#fdf4ff">비중%</th><th style="padding:5px 7px;text-align:right;background:#fdf4ff">편차%p</th>
              <th style="padding:5px 7px;text-align:right;background:#f0fdf4">거래액</th><th style="padding:5px 7px;text-align:right;background:#f0fdf4">비중%</th><th style="padding:5px 7px;text-align:right;background:#f0fdf4">편차%p</th>
            </tr>
          </thead>
          <tbody>{rows_html}</tbody>
        </table></div>
        <p style="font-size:.7rem;color:#9ca3af;margin-top:4px">* 편차 ±2%p 이상 강조</p>
        """, unsafe_allow_html=True)

    st.markdown("---")
    copy_button(make_text_segment(data), "📋 회원구분 데이터 복사 → Claude에 붙여넣기", key="copy_tab8")
    render_insight_btn("회원구분 인사이트 생성", make_prompt_segment(data), key="ai_tab8")
