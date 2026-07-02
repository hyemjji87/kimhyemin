"""
html_export.py
================
전체 대시보드(탭1~탭9, 하위 선택까지 포함)를 Streamlit 없이도 열리는
단일 정적 HTML 파일로 내보내는 모듈.

- tabs/utils.py의 순수 포맷터(fmt_M, kpi_card, yoy_badge 등)와
  차트 빌더(bar_line_chart, grouped_bar, diff_bar)를 그대로 재사용해서
  라이브 대시보드와 숫자·스타일이 100% 동일하게 나오도록 한다.
- Plotly 차트는 CDN 1회 로드 + 개별 div로 내보내 완전한 인터랙티브 차트를 유지한다.
- 탭3(제휴사별)은 전체 제휴사 블록을 미리 다 렌더링해두고
  <select> onchange JS로 전환한다 (라이브 앱의 selectbox와 동일 동작).
- 탭7(주차분석)은 JSON에 저장된 '기본 주차(=분석 시점 마감 주차)' 데이터만 담겨있으므로
  해당 주차 기준으로 고정 렌더링하고, 주차를 바꾸려면 라이브 앱을 쓰라고 안내한다.
"""

import plotly.io as pio
from datetime import datetime

from tabs.utils import (
    fmt_M, fmt_pct, fmt_pp, fmt_n, kpi_card, yoy_badge, sig_badge, C,
    bar_line_chart, grouped_bar, diff_bar,
)


# ─────────────────────────────────────────────────────────────
# 공통 헬퍼 (Streamlit 의존 없는 순수 문자열 버전)
# ─────────────────────────────────────────────────────────────
def _yoy(v26, v25):
    try:
        if v25 and abs(v25) > 0:
            return round((v26 - v25) / abs(v25) * 100, 2)
    except Exception:
        pass
    return None


def _section(title):
    return f'<div class="stitle">{title}</div>'


def _info_box(text):
    return f'<div class="info-box">💡 {text}</div>'


def _warn_box(text):
    return f'<div class="warn-box">⚠️ {text}</div>'


_CHART_SEQ = {"n": 0}


def _fig_div(fig):
    _CHART_SEQ["n"] += 1
    return pio.to_html(fig, include_plotlyjs=False, full_html=False,
                        div_id=f"chart_{_CHART_SEQ['n']}")


# ─────────────────────────────────────────────────────────────
# 탭1: 전체 Overview
# ─────────────────────────────────────────────────────────────
def _build_tab1(data, meta):
    t1 = data.get("tab1_overview", {})
    kpi = t1.get("kpi_total", {})
    out = [_section("핵심 KPI")]

    items = [
        ("UV", fmt_n(kpi.get("uv_26")), fmt_n(kpi.get("uv_25")), kpi.get("uv_yoy")),
        ("인증수", fmt_n(kpi.get("cert_26")), fmt_n(kpi.get("cert_25")), kpi.get("cert_yoy")),
        ("당월인증거래액", fmt_M(kpi.get("revenue_26")), fmt_M(kpi.get("revenue_25")), kpi.get("revenue_yoy")),
        ("구매고객수", fmt_n(kpi.get("buyers_26")), fmt_n(kpi.get("buyers_25")), kpi.get("buyers_yoy")),
        ("CR", fmt_pct(kpi.get("cr_26")), fmt_pct(kpi.get("cr_25")), kpi.get("cr_yoy")),
        ("객단가", fmt_M(kpi.get("arpu_26")), fmt_M(kpi.get("arpu_25")), kpi.get("arpu_yoy")),
        ("인증당거래액", fmt_M(kpi.get("rev_per_cert_26")), fmt_M(kpi.get("rev_per_cert_25")), kpi.get("rev_per_cert_yoy")),
    ]
    cards = "".join(f'<div style="flex:1;min-width:130px">{kpi_card(l, v, p, y)}</div>' for l, v, p, y in items)
    out.append(f'<div style="display:flex;gap:8px;flex-wrap:wrap">{cards}</div>')

    out.append(_section("제휴사별 성과 요약"))
    af_rows = t1.get("affiliate_summary", [])
    if af_rows:
        rows_html = ""
        for r in af_rows:
            is_new = r.get("is_new", False)
            cert_yoy = (r.get('cert_26')/r.get('cert_25')*100-100) if r.get('cert_25') else None
            uv_yoy = ((r.get('uv_26') or 0)/(r.get('uv_25') or 1)*100-100) if r.get('uv_25') else None
            rows_html += f"""
            <tr>
              <td>{r['name']}</td>
              <td class="r">{fmt_M(r.get('revenue_26'))}</td>
              <td class="r">{fmt_M(r.get('revenue_25')) if not is_new else '-'}</td>
              <td class="r">{yoy_badge(r.get('yoy_pct'), is_new)}</td>
              <td class="r">{fmt_n(r.get('cert_26'))}</td>
              <td class="r">{fmt_n(r.get('cert_25')) if not is_new else '-'}</td>
              <td class="r">{yoy_badge(cert_yoy, is_new)}</td>
              <td class="r">{fmt_pct(r.get('cr_26'))}</td>
              <td class="r">{fmt_pct(r.get('cr_25')) if not is_new else '-'}</td>
              <td class="r" style="color:{'#16a34a' if (r.get('cr_26') or 0)-(r.get('cr_25') or 0)>=0 else '#dc2626'}">{fmt_pp((r.get('cr_26') or 0)-(r.get('cr_25') or 0)) if not is_new else '-'}</td>
              <td class="r">{fmt_n(r.get('uv_26'))}</td>
              <td class="r">{fmt_n(r.get('uv_25')) if not is_new else '-'}</td>
              <td class="r">{yoy_badge(uv_yoy, is_new)}</td>
            </tr>"""
        out.append(f"""
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
        </table></div>""")

    out.append(_section("일자별 당월인증거래액 추이"))
    daily = t1.get("daily_trend", [])
    if daily:
        labels = [d["date_26"][-5:] for d in daily]
        vals26 = [d.get("rev_26") or 0 for d in daily]
        vals25 = [d.get("rev_25") or 0 for d in daily]
        fig = bar_line_chart(labels, vals26, vals25, bar_name="2026", line_name="2025(전년동기)")
        out.append(_fig_div(fig))

    return "".join(out)


# ─────────────────────────────────────────────────────────────
# 탭2: 인증당거래액 분해
# ─────────────────────────────────────────────────────────────
def _build_tab2(data):
    t2 = data.get("tab2_decomp", {})
    rows = t2.get("rows", [])
    out = [_section("인증당거래액 = CR × 객단가 분해")]

    if rows:
        existing = [r for r in rows if not r.get("is_new")]
        if existing:
            avg_rpc26 = sum(r["rev_per_cert_26"] or 0 for r in existing) / len(existing)
            avg_rpc25 = sum(r["rev_per_cert_25"] or 0 for r in existing) / len(existing)
            avg_cr26 = sum(r["cr_26"] or 0 for r in existing) / len(existing)
            avg_cr25 = sum(r["cr_25"] or 0 for r in existing) / len(existing)
            avg_apu26 = sum(r["arpu_26"] or 0 for r in existing) / len(existing)
            avg_apu25 = sum(r["arpu_25"] or 0 for r in existing) / len(existing)
            rpc_yoy = _yoy(avg_rpc26, avg_rpc25)
            cr_pp = round(avg_cr26 - avg_cr25, 2)
            apu_yoy = _yoy(avg_apu26, avg_apu25)

            cards = "".join(f'<div style="flex:1;min-width:200px">{kpi_card(l, v, p, y)}</div>' for l, v, p, y in [
                ("인증당거래액(평균)", fmt_M(avg_rpc26), fmt_M(avg_rpc25), rpc_yoy),
                ("CR 효과(평균)", fmt_pct(avg_cr26), fmt_pct(avg_cr25), cr_pp),
                ("객단가 효과(평균)", fmt_M(avg_apu26), fmt_M(avg_apu25), apu_yoy),
            ])
            out.append(f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px">{cards}</div>')

        rows_html = ""
        for r in rows:
            is_new = r.get("is_new", False)
            cr_pp_v = r.get("cr_pp")
            cr_color = "#16a34a" if (cr_pp_v or 0) >= 0 else "#dc2626"
            rows_html += f"""<tr>
              <td style="padding:6px 8px;border-bottom:1px solid #f1f5f9">
                {r['name']}{'&nbsp;<span class="badge-new">신규</span>' if is_new else ''}
              </td>
              <td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_M(r.get('rev_per_cert_26'))}</td>
              <td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_M(r.get('rev_per_cert_25')) if not is_new else '-'}</td>
              <td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right">{yoy_badge(r.get('rev_per_cert_yoy'), is_new)}</td>
              <td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_pct(r.get('cr_26'))}</td>
              <td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_pct(r.get('cr_25')) if not is_new else '-'}</td>
              <td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right;color:{cr_color};font-weight:600">{fmt_pp(cr_pp_v) if not is_new else '-'}</td>
              <td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_M(r.get('arpu_26'))}</td>
              <td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_M(r.get('arpu_25')) if not is_new else '-'}</td>
              <td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right">{yoy_badge(r.get('arpu_yoy'), is_new)}</td>
            </tr>"""
        out.append(f"""
        <div style="overflow-x:auto;background:white;border-radius:8px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,.07)">
        <table style="width:100%;border-collapse:collapse;font-size:.75rem">
          <thead><tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb">
            <th style="padding:7px 8px;text-align:left;font-size:.72rem">제휴사</th>
            <th style="padding:7px 8px;text-align:right;font-size:.72rem">인증당거래액 26</th>
            <th style="padding:7px 8px;text-align:right;font-size:.72rem">인증당거래액 25</th>
            <th style="padding:7px 8px;text-align:right;font-size:.72rem">YoY</th>
            <th style="padding:7px 8px;text-align:right;font-size:.72rem">CR 26</th>
            <th style="padding:7px 8px;text-align:right;font-size:.72rem">CR 25</th>
            <th style="padding:7px 8px;text-align:right;font-size:.72rem">CR △%p</th>
            <th style="padding:7px 8px;text-align:right;font-size:.72rem">객단가 26</th>
            <th style="padding:7px 8px;text-align:right;font-size:.72rem">객단가 25</th>
            <th style="padding:7px 8px;text-align:right;font-size:.72rem">객단가 YoY</th>
          </tr></thead>
          <tbody>{rows_html}</tbody>
        </table></div>""")
    return "".join(out)


# ─────────────────────────────────────────────────────────────
# 탭3: 제휴사별 카테고리·브랜드 (select로 전체 제휴사 전환)
# ─────────────────────────────────────────────────────────────
def _build_tab3(data):
    t3 = data.get("tab3_affiliate", {})
    t1_af = data.get("tab1_overview", {}).get("affiliate_summary", [])
    af_list = [r["name"] for r in t1_af]
    if not af_list:
        return "<p>제휴사 데이터 없음</p>"

    options_html = "".join(f'<option value="af3_{i}">{name}</option>' for i, name in enumerate(af_list))
    blocks_html = ""
    for i, af_name in enumerate(af_list):
        af_data = t3.get(af_name, {})
        af_meta = next((r for r in t1_af if r["name"] == af_name), {})
        is_new = af_data.get("is_new", False)

        uv_yoy = ((af_meta.get('uv_26') or 0)/(af_meta.get('uv_25') or 1)*100-100) if af_meta.get('uv_25') else None
        cert_yoy = ((af_meta.get('cert_26') or 0)/(af_meta.get('cert_25') or 1)*100-100) if af_meta.get('cert_25') else None
        cr_diff = (af_meta.get('cr_26') or 0) - (af_meta.get('cr_25') or 0) if not is_new else None

        cards_items = [
            ("UV", fmt_n(af_meta.get("uv_26")), fmt_n(af_meta.get("uv_25")), uv_yoy),
            ("인증수", fmt_n(af_meta.get("cert_26")), fmt_n(af_meta.get("cert_25")), cert_yoy),
            ("당월인증거래액", fmt_M(af_meta.get("revenue_26")), fmt_M(af_meta.get("revenue_25")), af_meta.get("yoy_pct")),
            ("CR", fmt_pct(af_meta.get("cr_26")), fmt_pct(af_meta.get("cr_25")), cr_diff),
        ]
        cards = ""
        for label, val, prev, yoy in cards_items:
            if is_new:
                cards += f'<div style="flex:1;min-width:150px">{kpi_card(label, val, None, None)}<div style="margin-top:-6px"><span class="badge-new">신규</span></div></div>'
            else:
                cards += f'<div style="flex:1;min-width:150px">{kpi_card(label, val, prev, yoy)}</div>'

        # 카테고리 테이블
        cat_rows_html = ""
        for r in af_data.get("cat_rows", []):
            wt_pp = r.get("wt_pp") or 0
            hl = 'background:#dbeafe' if wt_pp >= 3 else ('background:#fff3cd' if wt_pp <= -3 else '')
            cat_rows_html += f"""<tr>
              <td>{r['cat']}</td>
              <td class="r">{fmt_M(r.get('rev_26'))}</td>
              <td class="r">{fmt_M(r.get('rev_25')) if not is_new else '-'}</td>
              <td class="r">{yoy_badge(r.get('yoy_pct'), is_new)}</td>
              <td class="r">{fmt_pct(r.get('wt_25')) if not is_new else '-'}</td>
              <td class="r">{fmt_pct(r.get('wt_26'))}</td>
              <td class="r" style="{hl};color:{'#16a34a' if wt_pp>=0 else '#dc2626'};font-weight:600">{fmt_pp(wt_pp) if not is_new else '-'}</td>
            </tr>"""

        brd_rows_html = ""
        for r in af_data.get("brd_rows", []):
            brd_rows_html += f"""<tr>
              <td>{r['brand']}</td>
              <td class="r">{fmt_M(r.get('rev_26'))}</td>
              <td class="r">{fmt_M(r.get('rev_25')) if not is_new else '-'}</td>
              <td class="r">{yoy_badge(r.get('yoy_pct'), is_new)}</td>
            </tr>"""

        blocks_html += f"""
        <div class="af3-block" id="af3_{i}" style="display:{'block' if i==0 else 'none'}">
          <div class="stitle">{af_name} 핵심 KPI</div>
          <div style="display:flex;gap:8px;flex-wrap:wrap">{cards}</div>
          <div class="stitle">카테고리</div>
          <div style="overflow-x:auto">
          <table class="tbl" style="width:100%;border-collapse:collapse;font-size:.76rem">
            <thead><tr style="background:#f8fafc">
              <th>카테고리</th><th class="r">2026(M)</th><th class="r">2025(M)</th><th class="r">YoY</th>
              <th class="r">비중 2025</th><th class="r">비중 2026</th><th class="r">비중△%p</th>
            </tr></thead><tbody>{cat_rows_html}</tbody>
          </table></div>
          <div class="stitle">브랜드 TOP7</div>
          <div style="overflow-x:auto">
          <table class="tbl" style="width:100%;border-collapse:collapse;font-size:.76rem">
            <thead><tr style="background:#f8fafc">
              <th>브랜드</th><th class="r">2026(M)</th><th class="r">2025(M)</th><th class="r">YoY</th>
            </tr></thead><tbody>{brd_rows_html}</tbody>
          </table></div>
        </div>"""

    return f"""
    <label style="font-size:.85rem;font-weight:600;margin-right:8px">제휴사 선택</label>
    <select onchange="document.querySelectorAll('.af3-block').forEach(function(el){{el.style.display='none'}});document.getElementById(this.value).style.display='block'"
            style="padding:6px 10px;border:1px solid #e5e7eb;border-radius:6px;font-size:.85rem;margin-bottom:12px">
      {options_html}
    </select>
    {blocks_html}
    """


# ─────────────────────────────────────────────────────────────
# 탭4: 카테고리 전년비 + 역행 제휴사
# ─────────────────────────────────────────────────────────────
def _build_tab4(data):
    t4 = data.get("tab4_category", {})
    cat_rows = t4.get("cat_rows", [])
    rev_cards = t4.get("reverse_cards", [])
    out = [_section("카테고리별 당월인증거래액 YoY")]

    if cat_rows:
        top_up = sorted([r for r in cat_rows if (r.get("yoy_pct") or 0) > 0], key=lambda x: x.get("yoy_pct") or 0, reverse=True)[:2]
        top_dn = sorted([r for r in cat_rows if (r.get("yoy_pct") or 0) < 0], key=lambda x: x.get("yoy_pct") or 0)[:2]
        parts = []
        if top_up:
            parts.append("📈 급성장: " + ", ".join(r["cat"] + " ({:+.1f}%)".format(r["yoy_pct"]) for r in top_up))
        if top_dn:
            parts.append("📉 급락: " + ", ".join(r["cat"] + " ({:+.1f}%)".format(r["yoy_pct"]) for r in top_dn))
        if parts:
            out.append(_info_box("<br>".join(parts)))

        rows_html = ""
        for r in cat_rows:
            wt_pp = r.get("wt_pp") or 0
            hl = "background:#dbeafe" if wt_pp >= 3 else ("background:#fff3cd" if wt_pp <= -3 else "")
            dc = "#16a34a" if wt_pp >= 0 else "#dc2626"
            rows_html += (f"<tr><td style='padding:6px 8px;border-bottom:1px solid #f1f5f9'>{r['cat']}</td>"
                          f"<td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right'>{fmt_M(r.get('rev_26'))}</td>"
                          f"<td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right'>{fmt_M(r.get('rev_25'))}</td>"
                          f"<td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right'>{yoy_badge(r.get('yoy_pct'))}</td>"
                          f"<td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right'>{fmt_pct(r.get('wt_26'))}</td>"
                          f"<td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right'>{fmt_pct(r.get('wt_25'))}</td>"
                          f"<td style='padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:right;{hl};color:{dc};font-weight:600'>{fmt_pp(wt_pp)}</td></tr>")
        out.append(f"""<div style="overflow-x:auto;background:white;border-radius:8px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,.07)">
        <table style="width:100%;border-collapse:collapse;font-size:.76rem">
        <thead><tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb">
        <th style="padding:7px 8px;text-align:left">카테고리</th><th style="padding:7px 8px;text-align:right">2026(M)</th>
        <th style="padding:7px 8px;text-align:right">2025(M)</th><th style="padding:7px 8px;text-align:right">YoY</th>
        <th style="padding:7px 8px;text-align:right">비중 2026</th><th style="padding:7px 8px;text-align:right">비중 2025</th>
        <th style="padding:7px 8px;text-align:right">비중△%p</th></tr></thead>
        <tbody>{rows_html}</tbody></table></div>""")

    out.append(_section("전체 추세 역행 제휴사 특이점"))
    out.append(_info_box("전체 카테고리 YoY 방향과 반대로 움직인 제휴사 탐지 결과입니다."))
    if rev_cards:
        cards_html = ""
        for card in rev_cards:
            total_yoy = card.get("total_yoy") or 0
            yoy_dir = "↑" if total_yoy > 0 else "↓"
            yoy_color = "#16a34a" if total_yoy > 0 else "#dc2626"
            afs_html = ""
            for af in card.get("affiliates", []):
                cause = "".join(f"<br>&nbsp;&nbsp;📌 {cb['brand']} {yoy_badge(cb.get('yoy_pct'))}" for cb in af.get("cause_brands", []))
                afs_html += f"<div style='margin:6px 0;padding:8px;background:#fef2f2;border-radius:6px;font-size:.76rem'><b>{af['name']}</b> {yoy_badge(af.get('af_yoy') or 0)}{cause}</div>"
            cards_html += f"""<div style="flex:1;min-width:260px;background:white;border-radius:8px;padding:12px;
                box-shadow:0 1px 3px rgba(0,0,0,.08);border-top:3px solid #ef4444;margin-bottom:10px">
                <div style="font-weight:700;font-size:.85rem;margin-bottom:8px">{card['cat']}&nbsp;
                <span style="color:{yoy_color}">전체 {yoy_dir}{abs(total_yoy):.1f}%</span></div>{afs_html}</div>"""
        out.append(f'<div style="display:flex;gap:10px;flex-wrap:wrap">{cards_html}</div>')
    else:
        out.append(_info_box("역행 제휴사가 없습니다."))
    return "".join(out)


# ─────────────────────────────────────────────────────────────
# 탭5: 브랜드 전년비
# ─────────────────────────────────────────────────────────────
def _build_tab5(data):
    t5 = data.get("tab5_brand", {})
    t3 = data.get("tab3_affiliate", {})
    out = [_section("브랜드 거래액 TOP10")]

    brd_agg = {}
    for af, af_data in t3.items():
        for row in af_data.get("brd_rows", []):
            b = row["brand"]
            brd_agg.setdefault(b, {"rev_26": 0, "rev_25": 0})
            brd_agg[b]["rev_26"] += row.get("rev_26") or 0
            brd_agg[b]["rev_25"] += row.get("rev_25") or 0

    top10_all = sorted(brd_agg.items(), key=lambda x: x[1]["rev_26"], reverse=True)[:10]
    tot26 = sum(v["rev_26"] for v in brd_agg.values()) or 1
    tot25 = sum(v["rev_25"] for v in brd_agg.values()) or 1

    if top10_all:
        rows_html = ""
        for i, (b, v) in enumerate(top10_all, 1):
            r26, r25 = v["rev_26"], v["rev_25"]
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
        out.append(f"""<div style="overflow-x:auto;background:white;border-radius:8px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,.07)">
        <table style="width:100%;border-collapse:collapse;font-size:.76rem">
        <thead><tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb">
        <th style="padding:7px 8px;text-align:center">순위</th><th style="padding:7px 8px;text-align:left">브랜드</th>
        <th style="padding:7px 8px;text-align:right">2026(M)</th><th style="padding:7px 8px;text-align:right">2025(M)</th>
        <th style="padding:7px 8px;text-align:right">YoY</th><th style="padding:7px 8px;text-align:right">제휴내 비중</th>
        <th style="padding:7px 8px;text-align:right">비중△%p</th></tr></thead><tbody>{rows_html}</tbody></table></div>""")

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
        return f"""<div style="flex:1;min-width:320px">
        <div style="font-size:.82rem;font-weight:600;color:{color};margin-bottom:6px">{title}</div>
        <div style="overflow-x:auto;background:white;border-radius:8px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,.07)">
        <table style="width:100%;border-collapse:collapse;font-size:.75rem">
        <thead><tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb">
        <th style="padding:6px 8px;text-align:left">브랜드</th><th style="padding:6px 8px;text-align:right">2026(M)</th>
        <th style="padding:6px 8px;text-align:right">2025(M)</th><th style="padding:6px 8px;text-align:right">YoY</th>
        <th style="padding:6px 8px;text-align:right">비중△%p</th></tr></thead><tbody>{rows_html}</tbody></table></div></div>"""

    out.append(_section("브랜드 상승/하락 TOP10 (전년 5M 이상)"))
    out.append(f'<div style="display:flex;gap:12px;flex-wrap:wrap">{_tbl(t5.get("top10_up", []), "▲ 상승 TOP10", "#166534")}{_tbl(t5.get("top10_dn", []), "▼ 하락 TOP10", "#991b1b")}</div>')

    out.append(_section("전체 추세 역행 브랜드 특이점"))
    rev_cards = t5.get("reverse_cards", [])
    if rev_cards:
        cards_html = ""
        for card in rev_cards:
            total_yoy = card.get("total_yoy") or 0
            brds_html = ""
            for b in card.get("brands", []):
                small = " <span style='color:#9ca3af'>(소량)</span>" if b.get("is_small") else ""
                brds_html += f"""<div style="margin:4px 0;padding:6px 8px;background:#fef2f2;border-radius:4px;font-size:.75rem">
                  {b['brand']}{small} {yoy_badge(b.get('yoy_pct'))}
                  <span style="color:#9ca3af;font-size:.7rem"> {fmt_M(b.get('rev_25'))}→{fmt_M(b.get('rev_26'))}</span>
                </div>"""
            cards_html += f"""<div style="flex:1;min-width:260px;background:white;border-radius:8px;padding:12px;
                box-shadow:0 1px 3px rgba(0,0,0,.08);border-top:3px solid #ef4444;margin-bottom:10px">
                <div style="font-weight:700;font-size:.85rem;margin-bottom:8px">{card['cat']} &nbsp;
                <span style="color:{'#16a34a' if total_yoy>0 else '#dc2626'}">전체 {'↑' if total_yoy>0 else '↓'}{abs(total_yoy):.1f}%</span></div>{brds_html}</div>"""
        out.append(f'<div style="display:flex;gap:10px;flex-wrap:wrap">{cards_html}</div>')
    else:
        out.append(_info_box("역행 브랜드 없음"))
    return "".join(out)


# ─────────────────────────────────────────────────────────────
# 탭6: 몰전체 비교
# ─────────────────────────────────────────────────────────────
def _build_tab6(data):
    import plotly.graph_objects as go
    t6 = data.get("tab6_mall", {})
    kpi = t6.get("kpi", {})
    cat_rows = t6.get("cat_signal_rows", [])
    out = [_warn_box("몰전체_26 시트는 MTD 집계 기준. 전년 전체와 직접 YoY 비교 시 주의."), _section("몰전체 vs 제휴 핵심 KPI")]

    pct_pp = kpi.get("af_mall_pct_pp") or 0
    pct_hl = "background:#dbeafe" if pct_pp > 0 else ("background:#fff3cd" if pct_pp < 0 else "")
    rows_html = f"""
    <tr><td>몰전체 거래액</td><td class="r">{fmt_M(kpi.get('mall_rev_25'))}</td><td class="r">{fmt_M(kpi.get('mall_rev_26'))}</td><td class="r">{yoy_badge(kpi.get('mall_rev_yoy'))}</td></tr>
    <tr><td>제휴 당월인증거래액</td><td class="r">{fmt_M(kpi.get('af_rev_25'))}</td><td class="r">{fmt_M(kpi.get('af_rev_26'))}</td><td class="r">{yoy_badge(kpi.get('af_rev_yoy'))}</td></tr>
    <tr style="{pct_hl}"><td><b>제휴/몰전체 비중</b></td><td class="r">{fmt_pct(kpi.get('af_mall_pct_25'))}</td><td class="r">{fmt_pct(kpi.get('af_mall_pct_26'))}</td>
        <td class="r" style="color:{'#16a34a' if pct_pp>=0 else '#dc2626'};font-weight:600">{fmt_pp(pct_pp)}</td></tr>
    <tr><td>몰전체 주문고객수</td><td class="r">{fmt_n(kpi.get('mall_cust_25'))}</td><td class="r">{fmt_n(kpi.get('mall_cust_26'))}</td><td class="r">-</td></tr>
    <tr><td>제휴 구매고객수</td><td class="r">{fmt_n(kpi.get('af_buyers_25'))}</td><td class="r">{fmt_n(kpi.get('af_buyers_26'))}</td><td class="r">-</td></tr>"""

    top8 = [r for r in cat_rows if r.get("mall_yoy") is not None][:8]
    chart_html = ""
    if top8:
        cats = [r["cat"][:6] for r in top8]
        mall_yoys = [r.get("mall_yoy") or 0 for r in top8]
        af_yoys = [r.get("af_yoy") or 0 for r in top8]
        fig = go.Figure()
        fig.add_trace(go.Bar(name="몰전체 YoY", x=cats, y=mall_yoys, marker_color=C["gray"]))
        fig.add_trace(go.Bar(name="제휴 YoY", x=cats, y=af_yoys, marker_color=C["primary"]))
        fig.update_layout(barmode="group", height=260, margin=dict(l=0,r=0,t=20,b=0),
                          legend=dict(orientation="h",y=1.15), plot_bgcolor="white", paper_bgcolor="white")
        fig.update_yaxes(gridcolor="#e5e7eb", ticksuffix="%")
        chart_html = _fig_div(fig)

    out.append(f"""<div style="display:flex;gap:16px;flex-wrap:wrap">
    <div style="flex:1.4;min-width:340px;overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:.76rem">
    <thead><tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb"><th style="padding:7px 8px;text-align:left">구분</th>
    <th style="padding:7px 8px;text-align:right">2025 MTD</th><th style="padding:7px 8px;text-align:right">2026 MTD</th>
    <th style="padding:7px 8px;text-align:right">YoY</th></tr></thead><tbody>{rows_html}</tbody></table></div>
    <div style="flex:1;min-width:300px">{chart_html}</div></div>""")

    out.append(_section("카테고리별 몰전체 vs 제휴 YoY 비교 (전체 카테고리)"))
    if cat_rows:
        rows_html2 = ""
        for r in cat_rows:
            rows_html2 += f"""<tr><td>{r['cat']}</td><td class="r">{fmt_M(r.get('mall_rev_26'))}</td>
              <td class="r">{fmt_M(r.get('mall_rev_25'))}</td><td class="r">{yoy_badge(r.get('mall_yoy'))}</td>
              <td class="r">{fmt_M(r.get('af_rev_26'))}</td><td class="r">{yoy_badge(r.get('af_yoy'))}</td>
              <td>{sig_badge(r.get('signal',''))}</td></tr>"""
        out.append(f"""<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:.75rem">
        <thead><tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb"><th style="padding:6px 8px;text-align:left">카테고리</th>
        <th style="padding:6px 8px;text-align:right">몰 2026(M)</th><th style="padding:6px 8px;text-align:right">몰 2025(M)</th>
        <th style="padding:6px 8px;text-align:right">몰 YoY</th><th style="padding:6px 8px;text-align:right">제휴 2026(M)</th>
        <th style="padding:6px 8px;text-align:right">제휴 YoY</th><th style="padding:6px 8px;text-align:left">시그널</th></tr></thead>
        <tbody>{rows_html2}</tbody></table></div>""")

    out.append(_section("브랜드 시그널"))
    def _brd_tbl(rows, title, color):
        rows_html = "".join(f"""<tr><td>{r['brand']}</td><td>{r.get('cat','-')}</td>
          <td class="r">{yoy_badge(r.get('mall_yoy'))}</td><td class="r">{yoy_badge(r.get('af_yoy'))}</td></tr>""" for r in rows)
        return f"""<div style="flex:1;min-width:320px"><div style="font-size:.82rem;font-weight:600;color:{color};margin-bottom:6px">{title}</div>
        <div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:.75rem">
        <thead><tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb"><th style="padding:6px 8px;text-align:left">브랜드</th>
        <th style="padding:6px 8px;text-align:left">카테고리</th><th style="padding:6px 8px;text-align:right">몰 YoY</th>
        <th style="padding:6px 8px;text-align:right">제휴 YoY</th></tr></thead><tbody>{rows_html}</tbody></table></div></div>"""
    out.append(f'<div style="display:flex;gap:12px;flex-wrap:wrap">{_brd_tbl(t6.get("brand_star",[]), "★ 몰↓ 제휴↑ — 제휴 노출 강화 대상", "#1e40af")}{_brd_tbl(t6.get("brand_warn",[]), "⚠ 몰↑ 제휴↓ — 제휴 고객 이탈, CRM 필요", "#991b1b")}</div>')
    return "".join(out)


# ─────────────────────────────────────────────────────────────
# 탭7: 주차 분석 (JSON에 저장된 기본 주차 기준으로 고정 렌더링)
# ─────────────────────────────────────────────────────────────
def _build_tab7(data):
    t7 = data.get("tab7_weekly", {})
    out = [_warn_box(f"이 HTML은 JSON에 저장된 기본 주차({t7.get('wk_cur','-')})만 고정 렌더링합니다. "
                      "다른 주차를 보려면 라이브 앱에서 주차를 선택해주세요."),
           _section("주차 KPI")]

    kpi_cur = t7.get("kpi_cur", {})
    kpi_wy = t7.get("kpi_prev_year", {})
    kpi_wp = t7.get("kpi_prev", {})
    items = [
        ("당월인증거래액", fmt_M(kpi_cur.get("revenue")), fmt_M(kpi_wy.get("revenue")), _yoy(kpi_cur.get("revenue"), kpi_wy.get("revenue"))),
        ("구매고객수", fmt_n(kpi_cur.get("buyers")), fmt_n(kpi_wy.get("buyers")), _yoy(kpi_cur.get("buyers"), kpi_wy.get("buyers"))),
        ("전주 거래액", fmt_M(kpi_wp.get("revenue")), None, _yoy(kpi_cur.get("revenue"), kpi_wp.get("revenue"))),
        ("전주 고객수", fmt_n(kpi_wp.get("buyers")), None, _yoy(kpi_cur.get("buyers"), kpi_wp.get("buyers"))),
    ]
    cards = "".join(f'<div style="flex:1;min-width:150px">{kpi_card(l, v, p, y)}</div>' for l, v, p, y in items)
    out.append(f'<div style="display:flex;gap:8px;flex-wrap:wrap">{cards}</div>')

    out.append(_section("일자별 거래액 추이"))
    daily_list = t7.get("daily_list", [])
    if daily_list:
        import plotly.graph_objects as go
        labels = [d["date"][-5:] for d in daily_list]
        vals = [d.get("rev") or 0 for d in daily_list]
        dows = [d.get("dow", 0) for d in daily_list]
        colors = [C["amber"] if dow == 5 else (C["red"] if dow == 6 else C["primary"]) for dow in dows]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=labels, y=[v/1e6 for v in vals], name="당주", marker_color=colors))
        fig.update_layout(height=280, margin=dict(l=0,r=0,t=20,b=0), plot_bgcolor="white", paper_bgcolor="white", yaxis_title="M원")
        fig.update_yaxes(gridcolor="#e5e7eb")
        out.append(_fig_div(fig))

    cat_rows = t7.get("cat_wk_rows", [])
    if cat_rows:
        out.append(_section("카테고리 편차"))
        rows_html = ""
        for r in cat_rows:
            diff26 = r.get("diff_26") or 0
            hl26 = "background:#dbeafe" if diff26 >= 3 else ("background:#fff3cd" if diff26 <= -3 else "")
            rows_html += (f"<tr><td style='padding:5px 7px;border-bottom:1px solid #f1f5f9'>{r['cat']}</td>"
                          f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right'>{fmt_M(r.get('rev_26'))}</td>"
                          f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right'>{fmt_M(r.get('rev_25'))}</td>"
                          f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right'>{yoy_badge(r.get('yoy_pct'))}</td>"
                          f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right'>{fmt_pct(r.get('af_wt_26'))}</td>"
                          f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right'>{fmt_pct(r.get('mall_wt_26'))}</td>"
                          f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right;{hl26};color:{'#16a34a' if diff26>=0 else '#dc2626'};font-weight:600'>{fmt_pp(diff26)}</td></tr>")
        out.append(f"""<div style="overflow-x:auto;background:white;border-radius:8px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,.07)">
        <table style="width:100%;border-collapse:collapse;font-size:.72rem"><thead><tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb">
        <th style="padding:6px 7px;text-align:left">카테고리</th><th style="padding:6px 7px;text-align:right">2026(M)</th>
        <th style="padding:6px 7px;text-align:right">2025(M)</th><th style="padding:6px 7px;text-align:right">YoY</th>
        <th style="padding:6px 7px;text-align:right">제휴비중</th><th style="padding:6px 7px;text-align:right">몰비중</th>
        <th style="padding:6px 7px;text-align:right">편차%p</th></tr></thead><tbody>{rows_html}</tbody></table></div>""")

        cats12 = [r["cat"][:6] for r in cat_rows[:12]]
        fig = diff_bar(cats12, [r.get("diff_26") or 0 for r in cat_rows[:12]], [r.get("diff_25") or 0 for r in cat_rows[:12]], height=380)
        out.append(_fig_div(fig))

    brd_rows = t7.get("brd_wk_rows", [])
    if brd_rows:
        out.append(_section("브랜드 TOP20 편차"))
        rows_html = ""
        for r in brd_rows:
            diff26 = r.get("diff_26") or 0
            hl26 = "background:#dbeafe" if diff26 >= 1.5 else ("background:#fff3cd" if diff26 <= -1.5 else "")
            rows_html += (f"<tr><td style='padding:5px 7px;border-bottom:1px solid #f1f5f9'>{r['brand']}</td>"
                          f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9'>{r.get('cat','-')[:5]}</td>"
                          f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right'>{fmt_M(r.get('rev_26'))}</td>"
                          f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right'>{yoy_badge(r.get('yoy_pct'))}</td>"
                          f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right;{hl26};color:{'#16a34a' if diff26>=0 else '#dc2626'};font-weight:600'>{fmt_pp(diff26)}</td></tr>")
        out.append(f"""<div style="overflow-x:auto;background:white;border-radius:8px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,.07)">
        <table style="width:100%;border-collapse:collapse;font-size:.72rem"><thead><tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb">
        <th style="padding:6px 7px;text-align:left">브랜드</th><th style="padding:6px 7px;text-align:left">카테</th>
        <th style="padding:6px 7px;text-align:right">2026(M)</th><th style="padding:6px 7px;text-align:right">YoY</th>
        <th style="padding:6px 7px;text-align:right">편차%p</th></tr></thead><tbody>{rows_html}</tbody></table></div>""")
        brds = [r["brand"][:8] for r in brd_rows]
        fig = diff_bar(brds, [r.get("diff_26") or 0 for r in brd_rows], [r.get("diff_25") or 0 for r in brd_rows], height=520)
        out.append(_fig_div(fig))
    return "".join(out)


# ─────────────────────────────────────────────────────────────
# 탭8: 회원구분 분석
# ─────────────────────────────────────────────────────────────
def _build_tab8(data):
    t8 = data.get("tab8_segment", {})
    seg_kpi = t8.get("seg_kpi", {})
    cat_rows = t8.get("cat_rows", [])
    brd_rows = t8.get("brd_rows", [])
    out = [_section("회원구분별 KPI")]

    colors = {"신규": "#1e40af", "WIN-BACK": "#7e22ce", "기존": "#166534"}
    cards_html = ""
    for seg, kpi in seg_kpi.items():
        cards_html += f"""<div style="flex:1;min-width:220px;background:white;border-radius:8px;padding:14px;
                    box-shadow:0 1px 3px rgba(0,0,0,.08);border-left:4px solid {colors.get(seg,'#4f46e5')}">
          <div style="font-size:.75rem;font-weight:700;color:{colors.get(seg,'#374151')};margin-bottom:8px">{seg}</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:.75rem">
            <div><span style="color:#9ca3af">거래액</span><br><b>{fmt_M(kpi.get('revenue'))}</b>
              <span style="color:#6b7280">({kpi.get('rev_pct',0):.1f}%)</span></div>
            <div><span style="color:#9ca3af">고객수</span><br><b>{fmt_n(kpi.get('buyers'))}</b></div>
            <div><span style="color:#9ca3af">CR</span><br><b>{fmt_pct(kpi.get('cr'))}</b></div>
            <div><span style="color:#9ca3af">객단가</span><br><b>{fmt_M(kpi.get('arpu'))}</b></div>
          </div></div>"""
    out.append(f'<div style="display:flex;gap:10px;flex-wrap:wrap">{cards_html}</div>')

    out.append(_section("카테고리별 회원구분 실적"))
    out.append(_info_box("편차(%p) = 해당 구분의 카테비중 − 제휴 전체 카테비중. ±3%p 이상 강조."))
    if cat_rows:
        def _seg_cells(r, seg):
            rev, wt, diff = r.get(f"rev_{seg}", 0), r.get(f"wt_{seg}", 0), r.get(f"diff_{seg}", 0)
            hl = "background:#dbeafe" if diff >= 3 else ("background:#fff3cd" if diff <= -3 else "")
            dc = "#16a34a" if diff >= 0 else "#dc2626"
            return (f'<td style="padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_M(rev)}</td>'
                    f'<td style="padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_pct(wt)}</td>'
                    f'<td style="padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right;{hl};color:{dc};font-weight:600">{fmt_pp(diff)}</td>')
        rows_html = ""
        for r in cat_rows:
            rows_html += f"""<tr><td style="padding:5px 7px;border-bottom:1px solid #f1f5f9">{r['cat']}</td>
              <td style="padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_M(r.get('rev_total'))}</td>
              <td style="padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_n(r.get('buyers_total'))}</td>
              <td style="padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_pct(r.get('wt_total'))}</td>
              {_seg_cells(r,'신규')}{_seg_cells(r,'WIN-BACK')}{_seg_cells(r,'기존')}</tr>"""
        out.append(f"""<div style="overflow-x:auto;background:white;border-radius:8px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,.07)">
        <table style="width:100%;border-collapse:collapse;font-size:.72rem"><thead>
        <tr><th rowspan="2" style="padding:6px 7px;text-align:left;border-bottom:2px solid #e5e7eb;background:#f8fafc">카테고리</th>
        <th colspan="3" style="padding:6px 7px;text-align:center;background:#4f46e5;color:white">제휴 전체</th>
        <th colspan="3" style="padding:6px 7px;text-align:center;background:#eff6ff;color:#1e40af">신규 고객</th>
        <th colspan="3" style="padding:6px 7px;text-align:center;background:#fdf4ff;color:#7e22ce">WIN-BACK</th>
        <th colspan="3" style="padding:6px 7px;text-align:center;background:#f0fdf4;color:#166534">기존 고객</th></tr>
        <tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb">
        <th style="padding:5px 7px;text-align:right">거래액</th><th style="padding:5px 7px;text-align:right">고객수</th><th style="padding:5px 7px;text-align:right">비중%</th>
        <th style="padding:5px 7px;text-align:right;background:#eff6ff">거래액</th><th style="padding:5px 7px;text-align:right;background:#eff6ff">비중%</th><th style="padding:5px 7px;text-align:right;background:#eff6ff">편차%p</th>
        <th style="padding:5px 7px;text-align:right;background:#fdf4ff">거래액</th><th style="padding:5px 7px;text-align:right;background:#fdf4ff">비중%</th><th style="padding:5px 7px;text-align:right;background:#fdf4ff">편차%p</th>
        <th style="padding:5px 7px;text-align:right;background:#f0fdf4">거래액</th><th style="padding:5px 7px;text-align:right;background:#f0fdf4">비중%</th><th style="padding:5px 7px;text-align:right;background:#f0fdf4">편차%p</th></tr>
        </thead><tbody>{rows_html}</tbody></table></div>""")

    out.append(_section("브랜드별 회원구분 실적 TOP15"))
    if brd_rows:
        def _seg_cells_brd(r, seg):
            rev, wt, diff = r.get(f"rev_{seg}", 0), r.get(f"wt_{seg}", 0), r.get(f"diff_{seg}", 0)
            hl = "background:#dbeafe" if diff >= 2 else ("background:#fff3cd" if diff <= -2 else "")
            dc = "#16a34a" if diff >= 0 else "#dc2626"
            return (f'<td style="padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_M(rev)}</td>'
                    f'<td style="padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_pct(wt)}</td>'
                    f'<td style="padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right;{hl};color:{dc};font-weight:600">{fmt_pp(diff)}</td>')
        rows_html = ""
        for r in brd_rows:
            rows_html += f"""<tr><td style="padding:5px 7px;border-bottom:1px solid #f1f5f9">{r['brand']}</td>
              <td style="padding:5px 7px;border-bottom:1px solid #f1f5f9">{r.get('cat','-')[:6]}</td>
              <td style="padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_M(r.get('rev_total'))}</td>
              <td style="padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_n(r.get('buyers_total'))}</td>
              <td style="padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right">{fmt_pct(r.get('wt_total'))}</td>
              {_seg_cells_brd(r,'신규')}{_seg_cells_brd(r,'WIN-BACK')}{_seg_cells_brd(r,'기존')}</tr>"""
        out.append(f"""<div style="overflow-x:auto;background:white;border-radius:8px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,.07)">
        <table style="width:100%;border-collapse:collapse;font-size:.72rem"><thead>
        <tr><th rowspan="2" style="padding:6px 7px;text-align:left;border-bottom:2px solid #e5e7eb;background:#f8fafc">브랜드</th>
        <th rowspan="2" style="padding:6px 7px;text-align:left;border-bottom:2px solid #e5e7eb;background:#f8fafc">카테</th>
        <th colspan="3" style="padding:6px 7px;text-align:center;background:#4f46e5;color:white">제휴 전체</th>
        <th colspan="3" style="padding:6px 7px;text-align:center;background:#eff6ff;color:#1e40af">신규</th>
        <th colspan="3" style="padding:6px 7px;text-align:center;background:#fdf4ff;color:#7e22ce">WIN-BACK</th>
        <th colspan="3" style="padding:6px 7px;text-align:center;background:#f0fdf4;color:#166534">기존</th></tr>
        <tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb">
        <th style="padding:5px 7px;text-align:right">거래액</th><th style="padding:5px 7px;text-align:right">고객수</th><th style="padding:5px 7px;text-align:right">비중%</th>
        <th style="padding:5px 7px;text-align:right;background:#eff6ff">거래액</th><th style="padding:5px 7px;text-align:right;background:#eff6ff">비중%</th><th style="padding:5px 7px;text-align:right;background:#eff6ff">편차%p</th>
        <th style="padding:5px 7px;text-align:right;background:#fdf4ff">거래액</th><th style="padding:5px 7px;text-align:right;background:#fdf4ff">비중%</th><th style="padding:5px 7px;text-align:right;background:#fdf4ff">편차%p</th>
        <th style="padding:5px 7px;text-align:right;background:#f0fdf4">거래액</th><th style="padding:5px 7px;text-align:right;background:#f0fdf4">비중%</th><th style="padding:5px 7px;text-align:right;background:#f0fdf4">편차%p</th></tr>
        </thead><tbody>{rows_html}</tbody></table></div>""")
    return "".join(out)


# ─────────────────────────────────────────────────────────────
# 탭9: 첫구매 분석
# ─────────────────────────────────────────────────────────────
def _build_tab9(data):
    t9 = data.get("tab9_first", {})
    kpi = t9.get("kpi", {})
    cat_rows = t9.get("cat_rows", [])
    brd_rows = t9.get("brd_rows", [])
    out = []

    fp_pct = kpi.get("fp_pct_af", 0)
    if fp_pct < 3 or fp_pct > 20:
        out.append(_warn_box(f"첫구매 비율 {fp_pct:.1f}% — 정상범위(3~20%) 이탈. 운영팀 확인 필요."))

    out.append(_section("전체 요약 KPI"))
    items = [
        ("첫구매 거래액", fmt_M(kpi.get("fp_rev_26")), fmt_M(kpi.get("fp_rev_25")), kpi.get("fp_rev_yoy")),
        ("첫구매 고객수", fmt_n(kpi.get("fp_buyers_26")), fmt_n(kpi.get("fp_buyers_25")), None),
        ("제휴채널 대비 비중①", fmt_pct(kpi.get("fp_pct_af")), None, None),
        ("몰전체 대비 제휴 첫구매④", fmt_pct(kpi.get("fp_pct_mall")), None, None),
    ]
    cards = "".join(f'<div style="flex:1;min-width:170px">{kpi_card(l, v, p, y)}</div>' for l, v, p, y in items)
    out.append(f'<div style="display:flex;gap:8px;flex-wrap:wrap">{cards}</div>')

    out.append("""
    <div style="background:#fff7ed;border-left:4px solid #f59e0b;padding:10px 14px;border-radius:0 6px 6px 0;font-size:.78rem;line-height:1.8;margin:8px 0">
    <b>📌 비중 컬럼 정의</b><br>
    ① 첫구매내 비중: 해당 카테/브랜드 첫구매 거래액 ÷ <b>제휴 전체 첫구매 거래액</b> (합=100%)<br>
    ② 카테/브랜드내 첫구매 비중: 해당 첫구매 거래액 ÷ <b>제휴채널 내 해당 카테/브랜드 전체 거래액</b> (★≥15% 강조)<br>
    ④ 몰전체 대비 제휴 첫구매: 해당 카테 제휴 첫구매 ÷ <b>몰전체 해당 카테 거래액</b>
    </div>""")

    out.append(_section("카테고리별 첫구매 실적"))
    if cat_rows:
        rows_html = ""
        for r in cat_rows:
            w2_hl = "background:#dcfce7;font-weight:700" if r.get("w2_star") else ""
            w2_star = " ★" if r.get("w2_star") else ""
            rows_html += f"""<tr><td>{r['cat']}</td><td class="r">{fmt_M(r.get('rev_26'))}</td>
              <td class="r">{fmt_pct(r.get('w1_fp_in_pct'))}</td>
              <td class="r" style="{w2_hl}">{fmt_pct(r.get('w2_fp_in_cat_pct'))}{w2_star}</td>
              <td class="r">{fmt_pct(r.get('w3_cat_in_af_pct'))}</td>
              <td class="r">{fmt_pct(r.get('w4_fp_vs_mall_pct'))}</td></tr>"""
        out.append(f"""<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:.76rem">
        <thead><tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb"><th style="padding:7px 8px;text-align:left">카테고리</th>
        <th style="padding:7px 8px;text-align:right">첫구매 거래액</th><th style="padding:7px 8px;text-align:right">①첫구매내 비중</th>
        <th style="padding:7px 8px;text-align:right">②카테내 비중(★≥15%)</th><th style="padding:7px 8px;text-align:right">③카테 전체비중</th>
        <th style="padding:7px 8px;text-align:right">④몰전체 대비</th></tr></thead><tbody>{rows_html}</tbody></table></div>""")

        import plotly.graph_objects as go
        cats = [r["cat"][:6] for r in cat_rows[:12]]
        w1s = [r.get("w1_fp_in_pct") or 0 for r in cat_rows[:12]]
        w2s = [r.get("w2_fp_in_cat_pct") or 0 for r in cat_rows[:12]]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=cats, y=w1s, name="①첫구매내 비중", marker_color=C["primary"]))
        fig.add_trace(go.Scatter(x=cats, y=w2s, name="②카테내 비중", mode="lines+markers", line=dict(color=C["amber"], width=2), yaxis="y2"))
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=30,b=0), legend=dict(orientation="h", y=1.15),
                          yaxis=dict(title="① 비중(%)", gridcolor="#e5e7eb"),
                          yaxis2=dict(title="② 비중(%)", overlaying="y", side="right"),
                          plot_bgcolor="white", paper_bgcolor="white")
        out.append(_fig_div(fig))

    out.append(_section("브랜드별 첫구매 TOP15"))
    if brd_rows:
        rows_html = ""
        for r in brd_rows:
            w2_hl = "background:#dcfce7;font-weight:700" if r.get("w2_star") else ""
            w2_star = " ★" if r.get("w2_star") else ""
            rows_html += f"""<tr><td>{r['brand']}</td><td>{r.get('cat','-')[:6]}</td>
              <td class="r">{fmt_M(r.get('rev_26'))}</td><td class="r">{fmt_pct(r.get('w1_fp_in_pct'))}</td>
              <td class="r" style="{w2_hl}">{fmt_pct(r.get('w2_fp_in_brd_pct'))}{w2_star}</td></tr>"""
        out.append(f"""<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:.76rem">
        <thead><tr style="background:#f8fafc;border-bottom:2px solid #e5e7eb"><th style="padding:7px 8px;text-align:left">브랜드</th>
        <th style="padding:7px 8px;text-align:left">카테고리</th><th style="padding:7px 8px;text-align:right">첫구매 거래액</th>
        <th style="padding:7px 8px;text-align:right">①첫구매내 비중</th><th style="padding:7px 8px;text-align:right">②브랜드내 비중(★≥20%)</th>
        </tr></thead><tbody>{rows_html}</tbody></table></div>""")
    return "".join(out)


# ─────────────────────────────────────────────────────────────
# 메인 진입점
# ─────────────────────────────────────────────────────────────
def build_html_report(data: dict) -> str:
    meta = data.get("meta", {})
    qc = meta.get("quality_check", {})
    warns = [(k, v) for k, v in qc.items() if not v.get("ok")]

    tabs_def = [
        ("tab1", "📊 전체 Overview", _build_tab1(data, meta)),
        ("tab2", "🔍 인증당거래액 분해", _build_tab2(data)),
        ("tab3", "🏢 제휴사별 전년비", _build_tab3(data)),
        ("tab4", "📦 카테고리 전년비", _build_tab4(data)),
        ("tab5", "🏷️ 브랜드 전년비", _build_tab5(data)),
        ("tab6", "🏬 몰전체 비교", _build_tab6(data)),
        ("tab7", "📅 주차 분석", _build_tab7(data)),
        ("tab8", "👥 회원구분", _build_tab8(data)),
        ("tab9", "🛍️ 첫구매", _build_tab9(data)),
    ]

    nav_html = "".join(
        f'<button class="navbtn{" active" if i==0 else ""}" onclick="showTab(\'{tid}\',this)">{label}</button>'
        for i, (tid, label, _) in enumerate(tabs_def)
    )
    panels_html = "".join(
        f'<div class="tab-panel" id="{tid}" style="display:{"block" if i==0 else "none"}">{html}</div>'
        for i, (tid, _, html) in enumerate(tabs_def)
    )

    warn_html = ""
    if warns:
        items = "".join(f'<div class="warn-box">⚠️ <b>{k}</b>: {v.get("msg","")}</div>' for k, v in warns)
        warn_html = f"""<details style="margin-bottom:14px"><summary style="cursor:pointer;font-size:.85rem;color:#92400e">
        ⚠️ 데이터 품질 경고 {len(warns)}건 (클릭하여 확인)</summary>{items}</details>"""

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>LF몰 제휴 실적 대시보드 — {meta.get('mtd_end_26','')[:7]} MTD</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>
  body{{font-family:-apple-system,'Segoe UI',Malgun Gothic,sans-serif;background:#f3f4f6;margin:0;padding:20px;color:#1e293b}}
  .wrap{{max-width:1280px;margin:0 auto}}
  .dash-hdr{{background:linear-gradient(135deg,#4f46e5,#7c3aed);padding:16px 24px;border-radius:10px;color:white;margin-bottom:16px}}
  .dash-hdr h1{{color:white;margin:0;font-size:1.3rem}}
  .dash-hdr p{{opacity:.85;margin:4px 0 0;font-size:.82rem}}
  .kcard{{background:white;border-radius:8px;padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,.08);border-left:4px solid #4f46e5}}
  .kcard .label{{font-size:.72rem;color:#9ca3af;margin-bottom:4px}}
  .kcard .val{{font-size:1.3rem;font-weight:700;color:#1e293b}}
  .kcard .yoy{{font-size:.75rem;margin-top:3px}}
  .info-box{{background:#eef2ff;border-left:4px solid #4f46e5;padding:10px 14px;border-radius:0 6px 6px 0;font-size:.82rem;line-height:1.7;margin:8px 0}}
  .warn-box{{background:#fff7ed;border-left:4px solid #f59e0b;padding:10px 14px;border-radius:0 6px 6px 0;font-size:.82rem;line-height:1.7;margin:8px 0}}
  .stitle{{font-size:.9rem;font-weight:700;color:#374151;border-left:3px solid #4f46e5;padding-left:8px;margin:16px 0 8px}}
  .badge-up{{background:#dcfce7;color:#166534;padding:2px 7px;border-radius:4px;font-size:.72rem;font-weight:600}}
  .badge-dn{{background:#fee2e2;color:#991b1b;padding:2px 7px;border-radius:4px;font-size:.72rem;font-weight:600}}
  .badge-new{{background:#dbeafe;color:#1e40af;padding:2px 7px;border-radius:4px;font-size:.72rem;font-weight:600}}
  table{{background:white}}
  .r{{text-align:right!important}}
  .tbl th,.tbl td{{padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:left}}
  .tbl th{{background:#f8fafc;font-size:.72rem;font-weight:600;color:#374151;border-bottom:2px solid #e5e7eb}}
  .navwrap{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px;position:sticky;top:0;background:#f3f4f6;padding:10px 0;z-index:10}}
  .navbtn{{background:white;border:1px solid #e5e7eb;padding:8px 14px;border-radius:6px;cursor:pointer;font-size:.82rem;font-weight:600;color:#374151}}
  .navbtn.active{{background:#4f46e5;color:white;border-color:#4f46e5}}
  .tab-panel{{background:transparent}}
  .footer-note{{font-size:.72rem;color:#9ca3af;margin-top:24px;text-align:center}}
</style>
</head>
<body>
<div class="wrap">
  <div class="dash-hdr">
    <h1>📊 LF몰 제휴 실적 대시보드 — {meta.get('mtd_end_26','')[:7]} MTD (전체 내보내기)</h1>
    <p>
      분석 기간: {meta.get('mtd_start_26','')} ~ {meta.get('mtd_end_26','')} &nbsp;|&nbsp;
      전년 동기: {meta.get('mtd_start_25','')} ~ {meta.get('mtd_end_25','')} &nbsp;|&nbsp;
      제휴사 {meta.get('affiliate_count',0)}개 &nbsp;|&nbsp; 생성 시각: {generated_at}
    </p>
  </div>
  {warn_html}
  <div class="navwrap">{nav_html}</div>
  {panels_html}
  <div class="footer-note">이 파일은 LF몰 제휴 실적 분석 대시보드에서 생성된 정적 내보내기본입니다. 탭7(주차)은 기본 주차만 고정 반영됩니다.</div>
</div>
<script>
function showTab(id, btn) {{
  document.querySelectorAll('.tab-panel').forEach(function(el){{ el.style.display = 'none'; }});
  document.getElementById(id).style.display = 'block';
  document.querySelectorAll('.navbtn').forEach(function(el){{ el.classList.remove('active'); }});
  btn.classList.add('active');
  window.scrollTo({{top:0, behavior:'smooth'}});
}}
</script>
</body>
</html>"""
