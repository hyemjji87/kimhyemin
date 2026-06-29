"""tabs/tab4.py - 카테고리 전년비"""
import streamlit as st
from .utils import *
from ai_insight import render_insight_btn, make_prompt_category
from .clipboard import copy_button, make_text_category


def render(data: dict, meta: dict):
    t4 = data.get("tab4_category", {})
    cat_rows = t4.get("cat_rows", [])
    rev_cards = t4.get("reverse_cards", [])

    section("카테고리별 당월인증거래액 YoY")
    if cat_rows:
        # 자동 인사이트
        top_up = sorted([r for r in cat_rows if (r.get("yoy_pct") or 0) > 0],
                        key=lambda x: x.get("yoy_pct") or 0, reverse=True)[:2]
        top_dn = sorted([r for r in cat_rows if (r.get("yoy_pct") or 0) < 0],
                        key=lambda x: x.get("yoy_pct") or 0)[:2]
        parts = []
        if top_up:
            txt = ", ".join(r["cat"] + " (" + "{:+.1f}%".format(r["yoy_pct"]) + ")" for r in top_up)
            parts.append("📈 급성장: " + txt)
        if top_dn:
            txt = ", ".join(r["cat"] + " (" + "{:+.1f}%".format(r["yoy_pct"]) + ")" for r in top_dn)
            parts.append("📉 급락: " + txt)
        if parts:
            st.markdown('<div class="info-box">💡 ' + "<br>".join(parts) + "</div>", unsafe_allow_html=True)

        rows_html = ""
        for r in cat_rows:
            yoy_v = r.get("yoy_pct")
            wt_pp = r.get("wt_pp") or 0
            if wt_pp >= 3:
                hl = "background:#dbeafe"
            elif wt_pp <= -3:
                hl = "background:#fff3cd"
            else:
                hl = ""
            dc = "#16a34a" if wt_pp >= 0 else "#dc2626"
            rows_html += (
                "<tr>"
                "<td style='padding:6px 8px;border-bottom:1px solid #f1f5f9'>" + r["cat"] + "</td>"
                "<td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right'>" + fmt_M(r.get("rev_26")) + "</td>"
                "<td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right'>" + fmt_M(r.get("rev_25")) + "</td>"
                "<td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right'>" + yoy_badge(yoy_v) + "</td>"
                "<td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right'>" + fmt_pct(r.get("wt_26")) + "</td>"
                "<td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right'>" + fmt_pct(r.get("wt_25")) + "</td>"
                "<td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right;" + hl + ";color:" + dc + ";font-weight:600'>" + fmt_pp(wt_pp) + "</td>"
                "</tr>"
            )

        st.markdown(
            "<div style='overflow-x:auto;background:white;border-radius:8px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,.07)'>"
            "<table style='width:100%;border-collapse:collapse;font-size:.76rem'>"
            "<thead><tr style='background:#f8fafc;border-bottom:2px solid #e5e7eb'>"
            "<th style='padding:7px 8px;text-align:left;font-size:.72rem'>카테고리</th>"
            "<th style='padding:7px 8px;text-align:right;font-size:.72rem'>2026(M)</th>"
            "<th style='padding:7px 8px;text-align:right;font-size:.72rem'>2025(M)</th>"
            "<th style='padding:7px 8px;text-align:right;font-size:.72rem'>YoY</th>"
            "<th style='padding:7px 8px;text-align:right;font-size:.72rem'>비중 2026</th>"
            "<th style='padding:7px 8px;text-align:right;font-size:.72rem'>비중 2025</th>"
            "<th style='padding:7px 8px;text-align:right;font-size:.72rem'>비중△%p</th>"
            "</tr></thead>"
            "<tbody>" + rows_html + "</tbody>"
            "</table></div>",
            unsafe_allow_html=True
        )

    section("전체 추세 역행 제휴사 특이점")
    st.markdown('<div class="info-box">💡 전체 카테고리 YoY 방향과 반대로 움직인 제휴사 탐지 결과입니다.</div>', unsafe_allow_html=True)

    if rev_cards:
        for i in range(0, len(rev_cards), 3):
            chunk = rev_cards[i:i+3]
            cols = st.columns(len(chunk))
            for col, card in zip(cols, chunk):
                total_yoy = card.get("total_yoy") or 0
                yoy_dir = "↑" if total_yoy > 0 else "↓"
                yoy_color = "#16a34a" if total_yoy > 0 else "#dc2626"
                afs_html = ""
                for af in card.get("affiliates", []):
                    af_yoy = af.get("af_yoy") or 0
                    badge = yoy_badge(af_yoy)
                    cause = ""
                    for cb in af.get("cause_brands", []):
                        cause += "<br>&nbsp;&nbsp;📌 " + cb["brand"] + " " + yoy_badge(cb.get("yoy_pct"))
                    afs_html += (
                        "<div style='margin:6px 0;padding:8px;background:#fef2f2;border-radius:6px;font-size:.76rem'>"
                        "<b>" + af["name"] + "</b> " + badge + cause +
                        "</div>"
                    )
                with col:
                    st.markdown(
                        "<div style='background:white;border-radius:8px;padding:12px;"
                        "box-shadow:0 1px 3px rgba(0,0,0,.08);border-top:3px solid #ef4444;margin-bottom:10px'>"
                        "<div style='font-weight:700;font-size:.85rem;margin-bottom:8px'>"
                        + card["cat"] + "&nbsp;<span style='color:" + yoy_color + "'>전체 " + yoy_dir + "{:.1f}%</format></span>".replace("{:.1f}%</format>", "{:.1f}%".format(abs(total_yoy)) + "</span>") +
                        "</div>" + afs_html + "</div>",
                        unsafe_allow_html=True
                    )
    else:
        st.markdown('<div class="info-box">역행 제휴사가 없습니다.</div>', unsafe_allow_html=True)

    st.markdown("---")
    copy_button(make_text_category(data), "📋 카테고리 데이터 복사 → Claude에 붙여넣기", key="copy_tab4")
    render_insight_btn("카테고리 인사이트 생성", make_prompt_category(data), key="ai_tab4")
