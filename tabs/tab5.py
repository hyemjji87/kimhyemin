"""tabs/tab5.py — 브랜드 전년비"""
import streamlit as st
from .utils import *
from ai_insight import render_insight_btn, make_prompt_brand
from .clipboard import copy_button, make_text_brand


def render(data: dict, meta: dict):
    t5 = data.get("tab5_brand", {})
    t3 = data.get("tab3_affiliate", {})

    # ── 브랜드 거래액 TOP10 (전체 제휴 기준) ──
    section("브랜드 거래액 TOP10")

    # 전체 브랜드 집계 (tab3 데이터 활용)
    brd_agg = {}
    for af, af_data in t3.items():
        for row in af_data.get("brd_rows", []):
            b = row["brand"]
            if b not in brd_agg:
                brd_agg[b] = {"rev_26": 0, "rev_25": 0}
            brd_agg[b]["rev_26"] += row.get("rev_26") or 0
            brd_agg[b]["rev_25"] += row.get("rev_25") or 0

    top10_all = sorted(brd_agg.items(), key=lambda x: x[1]["rev_26"], reverse=True)[:10]
    tot26 = sum(v["rev_26"] for _, v in brd_agg.items()) or 1
    tot25 = sum(v["rev_25"] for _, v in brd_agg.items()) or 1

    if top10_all:
        rows_html = ""
        for i, (b, v) in enumerate(top10_all, 1):
            r26 = v["rev_26"]; r25 = v["rev_25"]
            yoy = _yoy(r26, r25)
            wt26 = round(r26/tot26*100, 2)
            wt25 = round(r25/tot25*100, 2) if r25 > 0 else 0
            wt_pp = round(wt26 - wt25, 2)
            rows_html += f"""<tr>
              <td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:center;color:#6b7280">{i}</td>
              <td style="padding:6px 8px;border-bottom:1px solid #f1f5f9">{b}</td>
              <td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_M(r26)}</td>
              <td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_M(r25) if r25 else '-'}</td>
              <td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right">{yoy_badge(yoy)}</td>
              <td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_pct(wt26)}</td>
              <td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right;color:{'#16a34a' if wt_pp>=0 else '#dc2626'};font-weight:600">{fmt_pp(wt_pp) if r25 else '-'}</td>
            </tr>"""
        st.markdown(f"""
        <div style="overflow-x:auto;background:white;border-radius:8px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,.07)">
        <table style="width:100%;border-collapse:collapse;font-size:.76rem">
          <thead><tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb">
            <th style="padding:7px 8px;text-align:center;font-size:.72rem;color:#374151">순위</th>
            <th style="padding:7px 8px;text-align:left;font-size:.72rem;color:#374151">브랜드</th>
            <th style="padding:7px 8px;text-align:right;font-size:.72rem;color:#374151">2026(M)</th>
            <th style="padding:7px 8px;text-align:right;font-size:.72rem;color:#374151">2025(M)</th>
            <th style="padding:7px 8px;text-align:right;font-size:.72rem;color:#374151">YoY</th>
            <th style="padding:7px 8px;text-align:right;font-size:.72rem;color:#374151">제휴내 비중</th>
            <th style="padding:7px 8px;text-align:right;font-size:.72rem;color:#374151">비중△%p</th>
          </tr></thead>
          <tbody>{rows_html}</tbody>
        </table></div>
        """, unsafe_allow_html=True)

    # ── TOP10 상승/하락 ──
    section("브랜드 상승/하락 TOP10 (전년 5M 이상)")

    def _tbl(rows, title, color):
        rows_html = ""
        for r in rows:
            wt_pp = r.get("wt_pp") or 0
            rows_html += f"""<tr>
              <td style="padding:6px 8px;border-bottom:1px solid #f1f5f9">{r['brand']}</td>
              <td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_M(r.get('rev_26'))}</td>
              <td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_M(r.get('rev_25'))}</td>
              <td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right">{yoy_badge(r.get('yoy_pct'))}</td>
              <td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right;color:{'#16a34a' if wt_pp>=0 else '#dc2626'};font-weight:600">{fmt_pp(wt_pp)}</td>
            </tr>"""
        return f"""
        <div style="font-size:.82rem;font-weight:600;color:{color};margin-bottom:6px">{title}</div>
        <div style="overflow-x:auto;background:white;border-radius:8px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,.07)">
        <table style="width:100%;border-collapse:collapse;font-size:.75rem">
          <thead><tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb">
            <th style="padding:6px 8px;text-align:left;font-size:.72rem">브랜드</th>
            <th style="padding:6px 8px;text-align:right;font-size:.72rem">2026(M)</th>
            <th style="padding:6px 8px;text-align:right;font-size:.72rem">2025(M)</th>
            <th style="padding:6px 8px;text-align:right;font-size:.72rem">YoY</th>
            <th style="padding:6px 8px;text-align:right;font-size:.72rem">비중△%p</th>
          </tr></thead>
          <tbody>{rows_html}</tbody>
        </table></div>"""

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(_tbl(t5.get("top10_up", []), "▲ 상승 TOP10", "#166534"), unsafe_allow_html=True)
    with c2:
        st.markdown(_tbl(t5.get("top10_dn", []), "▼ 하락 TOP10", "#991b1b"), unsafe_allow_html=True)

    # ── 역행 브랜드 카드 ──
    section("전체 추세 역행 브랜드 특이점")
    rev_cards = t5.get("reverse_cards", [])
    if rev_cards:
        cols_per_row = 3
        for i in range(0, len(rev_cards), cols_per_row):
            chunk = rev_cards[i:i+cols_per_row]
            cols = st.columns(len(chunk))
            for col, card in zip(cols, chunk):
                total_yoy = card.get("total_yoy") or 0
                brds_html = ""
                for b in card.get("brands", []):
                    badge = yoy_badge(b.get("yoy_pct"))
                    small = " <span style='color:#9ca3af'>(소량)</span>" if b.get("is_small") else ""
                    brds_html += f"""<div style="margin:4px 0;padding:6px 8px;background:#fef2f2;border-radius:4px;font-size:.75rem">
                      {b['brand']}{small} {badge}
                      <span style="color:#9ca3af;font-size:.7rem"> {fmt_M(b.get('rev_25'))}→{fmt_M(b.get('rev_26'))}</span>
                    </div>"""
                with col:
                    st.markdown(f"""
                    <div style="background:white;border-radius:8px;padding:12px;
                                box-shadow:0 1px 3px rgba(0,0,0,.08);border-top:3px solid #ef4444;margin-bottom:10px">
                      <div style="font-weight:700;font-size:.85rem;margin-bottom:8px">
                        {card['cat']} &nbsp;
                        <span style="color:{'#16a34a' if total_yoy>0 else '#dc2626'}">
                          전체 {'↑' if total_yoy>0 else '↓'}{abs(total_yoy):.1f}%
                        </span>
                      </div>
                      {brds_html}
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="info-box">역행 브랜드 없음</div>', unsafe_allow_html=True)

    st.markdown("---")
    copy_button(make_text_brand(data), "📋 브랜드 데이터 복사 → Claude에 붙여넣기", key="copy_tab5")
    render_insight_btn("브랜드 인사이트 생성", make_prompt_brand(data), key="ai_tab5")


def _yoy(v26, v25):
    try:
        if v25 and abs(v25) > 0:
            return round((v26 - v25) / abs(v25) * 100, 2)
    except Exception:
        pass
    return None
