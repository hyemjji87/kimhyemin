"""tabs/tab7.py — 주차 분析 (주차 선택 가능)"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
from collections import defaultdict
from .utils import *
from .clipboard import copy_button, make_text_weekly
from ai_insight import render_insight_btn, make_prompt_weekly


def _build_week_map(data: dict):
    """JSON meta에서 주차맵 재구성"""
    # preprocessor에서 pivot_week를 JSON에 넣지 않으므로
    # tab7_weekly의 wk_cur 등 기본 정보만 활용
    # 주차 선택은 session_state로 override
    pass


def _calc_week_kpi(df26, df25, wk_dates_cur, wk_dates_prev_year, wk_dates_prev,
                   mall26, mall25, exclude_ssng=True):
    """선택된 주차로 KPI/카테/브랜드 재계산"""
    from collections import defaultdict as dd

    def _filter(df, dates_set):
        date_set = {datetime.strptime(d, "%Y-%m-%d").date() for d in dates_set if d}
        return df[df["정산일시일"].dt.date.isin(date_set)]

    flt26 = _filter(df26[(df26["당월인증"]=="Y") & (df26["정산구분"]=="판매")], wk_dates_cur)
    flt25 = _filter(df25[(df25["당월인증"]=="Y") & (df25["정산구분"]=="판매")], wk_dates_prev_year) if df25 is not None and len(df25)>0 else pd.DataFrame()
    flt26_wp = _filter(df26[(df26["당월인증"]=="Y") & (df26["정산구분"]=="판매")], wk_dates_prev)

    def _kpi(df):
        if len(df) == 0:
            return dict(revenue=0, buyers=0)
        return dict(revenue=float(df["거래액_VAT제외"].sum()), buyers=int(df["고객번호"].nunique()))

    kpi_cur = _kpi(flt26)
    kpi_wy  = _kpi(flt25)
    kpi_wp  = _kpi(flt26_wp)

    # 일별
    daily = {}
    for _, row in flt26.iterrows():
        d = row["정산일시일"].strftime("%Y-%m-%d")
        daily[d] = daily.get(d, 0) + float(row["거래액_VAT제외"])
    daily_list = [dict(date=d, rev=v, dow=datetime.strptime(d,"%Y-%m-%d").weekday())
                  for d, v in sorted(daily.items())]

    # 카테 편차
    tot26 = float(flt26["거래액_VAT제외"].sum()) or 1
    tot25 = float(flt25["거래액_VAT제외"].sum()) if len(flt25)>0 else 1
    mall_tot26 = float(mall26["거래액"].sum()) if len(mall26)>0 else 1
    mall_tot25 = float(mall25["거래액"].sum()) if len(mall25)>0 else 1

    cat_af26 = flt26.groupby("물리대카테")["거래액_VAT제외"].sum() if len(flt26)>0 else pd.Series(dtype=float)
    cat_af25 = flt25.groupby("물리대카테")["거래액_VAT제외"].sum() if len(flt25)>0 else pd.Series(dtype=float)
    cat_mall26 = mall26.groupby("대카테고리명")["거래액"].sum() if "대카테고리명" in mall26.columns else pd.Series(dtype=float)
    cat_mall25 = mall25.groupby("대카테고리명")["거래액"].sum() if "대카테고리명" in mall25.columns else pd.Series(dtype=float)

    cat_rows = []
    for cat in sorted(set(cat_af26.index) | set(cat_af25.index)):
        r26 = float(cat_af26.get(cat, 0))
        r25 = float(cat_af25.get(cat, 0))
        mw26 = float(cat_mall26.get(cat, 0))
        mw25 = float(cat_mall25.get(cat, 0))
        af_w26 = round(r26/tot26*100, 2)
        mall_w26 = round(mw26/mall_tot26*100, 2)
        af_w25 = round(r25/tot25*100, 2) if tot25 > 1 else 0
        mall_w25 = round(mw25/mall_tot25*100, 2) if mall_tot25 > 1 else 0
        cat_rows.append(dict(
            cat=cat, rev_26=r26, rev_25=r25,
            yoy_pct=_yoy(r26, r25),
            af_wt_26=af_w26, mall_wt_26=mall_w26, diff_26=round(af_w26-mall_w26,2),
            af_wt_25=af_w25, mall_wt_25=mall_w25, diff_25=round(af_w25-mall_w25,2),
        ))
    cat_rows.sort(key=lambda x: x["rev_26"], reverse=True)

    # 브랜드 TOP20
    brd_af26 = flt26.groupby("Admin브랜드명")["거래액_VAT제외"].sum() if len(flt26)>0 else pd.Series(dtype=float)
    brd_af25 = flt25.groupby("Admin브랜드명")["거래액_VAT제외"].sum() if len(flt25)>0 else pd.Series(dtype=float)
    brd_mall26 = mall26.groupby("ADMIN브랜드명")["거래액"].sum() if "ADMIN브랜드명" in mall26.columns else pd.Series(dtype=float)
    brd_mall25 = mall25.groupby("ADMIN브랜드명")["거래액"].sum() if "ADMIN브랜드명" in mall25.columns else pd.Series(dtype=float)
    brd_cat_map = flt26.groupby("Admin브랜드명")["물리대카테"].agg(
        lambda x: x.value_counts().index[0] if len(x)>0 else "-"
    ).to_dict() if len(flt26)>0 else {}

    top20 = brd_af26.nlargest(20).index.tolist()
    brd_rows = []
    for b in top20:
        r26 = float(brd_af26.get(b,0)); r25 = float(brd_af25.get(b,0))
        mw26 = float(brd_mall26.get(b,0)); mw25 = float(brd_mall25.get(b,0))
        af_w26 = round(r26/tot26*100,2); mall_w26 = round(mw26/mall_tot26*100,2)
        af_w25 = round(r25/tot25*100,2) if tot25>1 else 0
        mall_w25 = round(mw25/mall_tot25*100,2) if mall_tot25>1 else 0
        brd_rows.append(dict(
            brand=b, cat=brd_cat_map.get(b,"-"),
            rev_26=r26, rev_25=r25, yoy_pct=_yoy(r26,r25),
            af_wt_26=af_w26, mall_wt_26=mall_w26, diff_26=round(af_w26-mall_w26,2),
            af_wt_25=af_w25, mall_wt_25=mall_w25, diff_25=round(af_w25-mall_w25,2),
        ))

    return dict(kpi_cur=kpi_cur, kpi_wy=kpi_wy, kpi_wp=kpi_wp,
                daily_list=daily_list, cat_rows=cat_rows, brd_rows=brd_rows)


def render(data: dict, meta: dict):
    t7 = data.get("tab7_weekly", {})

    # ── 주차 목록 구성 ──
    # preprocessor가 저장한 pivot_week_map 활용 (없으면 기본값)
    pivot_week = data.get("meta", {}).get("pivot_week", {})

    # pivot_week가 없으면 기본 t7 데이터 사용
    has_raw = "df26" in st.session_state and "df25" in st.session_state

    wk_cur_default = t7.get("wk_cur", "")
    wk_wy_default  = t7.get("wk_prev_year", "")
    wk_wp_default  = t7.get("wk_prev", "")

    # 주차 선택 UI
    st.markdown("### 📅 분析 주차 선택")
    col_sel1, col_sel2, col_sel3 = st.columns(3)

    if has_raw:
        # raw 데이터 있으면 실시간 주차 선택
        pw = st.session_state.get("pivot_week_map", {})
        wk26_list = sorted(set(v for v in pw.values() if str(v).startswith("26")),
                           key=lambda x: (int(x.split("_")[1]), int(x.split("_")[2])))
        wk25_list = sorted(set(v for v in pw.values() if str(v).startswith("25")),
                           key=lambda x: (int(x.split("_")[1]), int(x.split("_")[2])))
        wk_all_list = sorted(set(v for v in pw.values()),
                             key=lambda x: (x.split("_")[0], int(x.split("_")[1]), int(x.split("_")[2])))

        # 날짜 범위 레이블 생성
        wk_dates_map = defaultdict(list)
        for d, w in pw.items():
            wk_dates_map[w].append(d)

        def wk_label(wk):
            dates = sorted(wk_dates_map.get(wk, []))
            if dates:
                return f"{wk} ({dates[0][5:]} ~ {dates[-1][5:]})"
            return wk

        wk26_labels = [wk_label(w) for w in wk26_list]
        wk25_labels = [wk_label(w) for w in wk25_list]

        default_cur_idx = wk26_list.index(wk_cur_default) if wk_cur_default in wk26_list else 0
        default_wy_idx  = wk25_list.index(wk_wy_default)  if wk_wy_default  in wk25_list else 0

        with col_sel1:
            sel_cur = st.selectbox("당주 (26년)", wk26_labels, index=default_cur_idx, key="wk_sel_cur")
            wk_cur = wk26_list[wk26_labels.index(sel_cur)]
        with col_sel2:
            sel_wy = st.selectbox("전년 대응 주차 (25년)", wk25_labels, index=default_wy_idx, key="wk_sel_wy")
            wk_wy = wk25_list[wk25_labels.index(sel_wy)]
        with col_sel3:
            # 전주 자동 계산 (표시만)
            parts = wk_cur.split("_")
            if len(parts)==3 and int(parts[2])>1:
                wk_wp = f"{parts[0]}_{parts[1]}_{int(parts[2])-1}"
            else:
                wk_wp = wk_wp_default or "-"
            st.info(f"전주: **{wk_label(wk_wp) if wk_wp in wk_dates_map else wk_wp}**")

        # 선택 주차 날짜셋
        wk_dates_cur  = set(wk_dates_map.get(wk_cur, []))
        wk_dates_wy   = set(wk_dates_map.get(wk_wy, []))
        wk_dates_wp   = set(wk_dates_map.get(wk_wp, []))

        # 재계산
        result = _calc_week_kpi(
            st.session_state["df26"], st.session_state["df25"],
            wk_dates_cur, wk_dates_wy, wk_dates_wp,
            st.session_state["mall26"], st.session_state["mall25"],
        )
        kpi_cur = result["kpi_cur"]
        kpi_wy  = result["kpi_wy"]
        kpi_wp  = result["kpi_wp"]
        daily_list = result["daily_list"]
        cat_rows   = result["cat_rows"]
        brd_rows   = result["brd_rows"]
        day_count  = len(wk_dates_cur)

    else:
        # raw 없으면 전처리 결과 그대로 사용
        with col_sel1:
            st.info(f"분析 주차: **{wk_cur_default}** (기본값)")
        with col_sel2:
            st.info(f"전년 대응: **{wk_wy_default}**")
        with col_sel3:
            st.info(f"전주: **{wk_wp_default or '-'}**")

        wk_cur = wk_cur_default
        kpi_cur = t7.get("kpi_cur", {})
        kpi_wy  = t7.get("kpi_prev_year", {})
        kpi_wp  = t7.get("kpi_prev", {})
        daily_list = t7.get("daily_list", [])
        cat_rows   = t7.get("cat_wk_rows", [])
        brd_rows   = t7.get("brd_wk_rows", [])
        day_count  = t7.get("wk_day_count", 0)

    # ── 경고 배너 ──
    warn_box(f"분析 주차: {wk_cur} ({day_count}일) | "
             f"전년: {wk_wy_default if not has_raw else ''} | "
             "※ raw 데이터 로드 시 주차 변경 가능")

    # ── KPI 카드 ──
    section("주차 KPI")
    cols = st.columns(4)
    items = [
        ("당월인증거래액", fmt_M(kpi_cur.get("revenue")), fmt_M(kpi_wy.get("revenue")),
         _yoy(kpi_cur.get("revenue"), kpi_wy.get("revenue"))),
        ("구매고객수", fmt_n(kpi_cur.get("buyers")), fmt_n(kpi_wy.get("buyers")),
         _yoy(kpi_cur.get("buyers"), kpi_wy.get("buyers"))),
        ("전주 거래액", fmt_M(kpi_wp.get("revenue")), None,
         _yoy(kpi_cur.get("revenue"), kpi_wp.get("revenue"))),
        ("전주 고객수", fmt_n(kpi_wp.get("buyers")), None,
         _yoy(kpi_cur.get("buyers"), kpi_wp.get("buyers"))),
    ]
    for col, (label, val, prev, yoy) in zip(cols, items):
        with col:
            st.markdown(kpi_card(label, val, prev, yoy), unsafe_allow_html=True)

    # ── 일별 추이 ──
    section("일자별 거래액 추이")
    if daily_list:
        labels = [d["date"][-5:] for d in daily_list]
        vals   = [d.get("rev") or 0 for d in daily_list]
        dows   = [d.get("dow", 0) for d in daily_list]
        colors = [C["amber"] if dow==5 else (C["red"] if dow==6 else C["primary"]) for dow in dows]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=labels, y=[v/1e6 for v in vals], name="당주", marker_color=colors))
        fig.update_layout(height=280, margin=dict(l=0,r=0,t=20,b=0),
                          plot_bgcolor="white", paper_bgcolor="white", yaxis_title="M원")
        fig.update_yaxes(gridcolor="#e5e7eb")
        st.plotly_chart(fig, use_container_width=True)

    # ── 카테/브랜드 서브탭 ──
    sub = st.tabs(["📦 카테고리 편차", "🏷️ 브랜드 TOP20 편차"])

    with sub[0]:
        if cat_rows:
            rows_html = ""
            for r in cat_rows:
                diff26 = r.get("diff_26") or 0
                diff25 = r.get("diff_25") or 0
                hl26 = "background:#dbeafe" if diff26>=3 else ("background:#fff3cd" if diff26<=-3 else "")
                rows_html += (
                    "<tr>"
                    f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9'>{r['cat']}</td>"
                    f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right'>{fmt_M(r.get('rev_26'))}</td>"
                    f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right'>{fmt_M(r.get('rev_25'))}</td>"
                    f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right'>{yoy_badge(r.get('yoy_pct'))}</td>"
                    f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right'>{fmt_pct(r.get('af_wt_26'))}</td>"
                    f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right'>{fmt_pct(r.get('mall_wt_26'))}</td>"
                    f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right;{hl26};color:{'#16a34a' if diff26>=0 else '#dc2626'};font-weight:600'>{fmt_pp(diff26)}</td>"
                    f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right'>{fmt_pct(r.get('af_wt_25'))}</td>"
                    f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right'>{fmt_pct(r.get('mall_wt_25'))}</td>"
                    f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right;color:#6b7280;font-size:.7rem'>{fmt_pp(diff25)}</td>"
                    "</tr>"
                )
            st.markdown(
                "<div style='overflow-x:auto;background:white;border-radius:8px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,.07)'>"
                "<table style='width:100%;border-collapse:collapse;font-size:.72rem'>"
                "<thead><tr>"
                "<th rowspan='2' style='padding:6px 7px;text-align:left;border-bottom:2px solid #e5e7eb;background:#f8fafc'>카테고리</th>"
                "<th rowspan='2' style='padding:6px 7px;text-align:right;border-bottom:2px solid #e5e7eb;background:#f8fafc'>2026(M)</th>"
                "<th rowspan='2' style='padding:6px 7px;text-align:right;border-bottom:2px solid #e5e7eb;background:#f8fafc'>2025(M)</th>"
                "<th rowspan='2' style='padding:6px 7px;text-align:right;border-bottom:2px solid #e5e7eb;background:#f8fafc'>YoY</th>"
                "<th colspan='3' style='padding:6px 7px;text-align:center;background:#eef2ff;color:#3730a3;border-bottom:1px solid #c7d2fe'>[당년] 비중 편차</th>"
                "<th colspan='3' style='padding:6px 7px;text-align:center;background:#f9fafb;color:#6b7280;border-bottom:1px solid #e5e7eb'>[전년] 비중 편차</th>"
                "</tr>"
                "<tr style='background:#f8fafc;border-bottom:2px solid #e5e7eb'>"
                "<th style='padding:5px 7px;text-align:right;background:#eef2ff;color:#3730a3'>제휴비중</th>"
                "<th style='padding:5px 7px;text-align:right;background:#eef2ff;color:#3730a3'>몰비중</th>"
                "<th style='padding:5px 7px;text-align:right;background:#eef2ff;color:#3730a3'>편차%p</th>"
                "<th style='padding:5px 7px;text-align:right;background:#f9fafb;color:#6b7280'>제휴비중</th>"
                "<th style='padding:5px 7px;text-align:right;background:#f9fafb;color:#6b7280'>몰비중</th>"
                "<th style='padding:5px 7px;text-align:right;background:#f9fafb;color:#6b7280'>편차%p</th>"
                "</tr></thead>"
                "<tbody>" + rows_html + "</tbody></table></div>"
                "<p style='font-size:.7rem;color:#9ca3af;margin-top:4px'>* 편차 ±3%p 이상 강조</p>",
                unsafe_allow_html=True
            )

            cats12 = [r["cat"][:6] for r in cat_rows[:12]]
            fig = diff_bar(cats12, [r.get("diff_26") or 0 for r in cat_rows[:12]],
                           [r.get("diff_25") or 0 for r in cat_rows[:12]], height=380)
            st.plotly_chart(fig, use_container_width=True)

    with sub[1]:
        if brd_rows:
            rows_html = ""
            for r in brd_rows:
                diff26 = r.get("diff_26") or 0
                hl26 = "background:#dbeafe" if diff26>=1.5 else ("background:#fff3cd" if diff26<=-1.5 else "")
                rows_html += (
                    "<tr>"
                    f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9'>{r['brand']}</td>"
                    f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9'>{r.get('cat','-')[:5]}</td>"
                    f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right'>{fmt_M(r.get('rev_26'))}</td>"
                    f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right'>{fmt_M(r.get('rev_25'))}</td>"
                    f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right'>{yoy_badge(r.get('yoy_pct'))}</td>"
                    f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right'>{fmt_pct(r.get('af_wt_26'))}</td>"
                    f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right'>{fmt_pct(r.get('mall_wt_26'))}</td>"
                    f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right;{hl26};color:{'#16a34a' if diff26>=0 else '#dc2626'};font-weight:600'>{fmt_pp(diff26)}</td>"
                    f"<td style='padding:5px 7px;border-bottom:1px solid #f1f5f9;text-align:right;color:#6b7280;font-size:.7rem'>{fmt_pp(r.get('diff_25') or 0)}</td>"
                    "</tr>"
                )
            st.markdown(
                "<div style='overflow-x:auto;background:white;border-radius:8px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,.07)'>"
                "<table style='width:100%;border-collapse:collapse;font-size:.72rem'>"
                "<thead><tr style='background:#f8fafc;border-bottom:2px solid #e5e7eb'>"
                "<th style='padding:6px 7px;text-align:left'>브랜드</th>"
                "<th style='padding:6px 7px;text-align:left'>카테</th>"
                "<th style='padding:6px 7px;text-align:right'>2026(M)</th>"
                "<th style='padding:6px 7px;text-align:right'>2025(M)</th>"
                "<th style='padding:6px 7px;text-align:right'>YoY</th>"
                "<th style='padding:6px 7px;text-align:right'>제휴비중</th>"
                "<th style='padding:6px 7px;text-align:right'>몰비중</th>"
                "<th style='padding:6px 7px;text-align:right'>편차%p(당년)</th>"
                "<th style='padding:6px 7px;text-align:right'>편차%p(전년)</th>"
                "</tr></thead>"
                "<tbody>" + rows_html + "</tbody></table></div>"
                "<p style='font-size:.7rem;color:#9ca3af;margin-top:4px'>* 편차 ±1.5%p 이상 강조</p>",
                unsafe_allow_html=True
            )
            brds = [r["brand"][:8] for r in brd_rows]
            fig = diff_bar(brds, [r.get("diff_26") or 0 for r in brd_rows],
                           [r.get("diff_25") or 0 for r in brd_rows], height=520)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    copy_button(make_text_weekly(data), "📋 주차 데이터 복사 → Claude에 붙여넣기", key="copy_tab7")
    render_insight_btn("주차 인사이트 생성", make_prompt_weekly(data), key="ai_tab7")


def _yoy(v26, v25):
    try:
        if v25 and abs(v25) > 0:
            return round((v26 - v25) / abs(v25) * 100, 2)
    except Exception:
        pass
    return None
