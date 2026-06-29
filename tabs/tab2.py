"""tabs/tab2.py — 인증당거래액 분해"""
import streamlit as st
from .utils import *
from .clipboard import copy_button, make_text_decomp


def render(data: dict, meta: dict):
    t2 = data.get("tab2_decomp", {})
    rows = t2.get("rows", [])

    section("인증당거래액 = CR × 객단가 분해")

    if rows:
        existing = [r for r in rows if not r.get("is_new")]
        new_afs  = [r for r in rows if r.get("is_new")]

        if existing:
            # 전체 평균
            avg_rpc26 = sum(r["rev_per_cert_26"] or 0 for r in existing) / len(existing)
            avg_rpc25 = sum(r["rev_per_cert_25"] or 0 for r in existing) / len(existing)
            avg_cr26  = sum(r["cr_26"] or 0 for r in existing) / len(existing)
            avg_cr25  = sum(r["cr_25"] or 0 for r in existing) / len(existing)
            avg_apu26 = sum(r["arpu_26"] or 0 for r in existing) / len(existing)
            avg_apu25 = sum(r["arpu_25"] or 0 for r in existing) / len(existing)

            rpc_yoy = _yoy(avg_rpc26, avg_rpc25)
            cr_pp   = round(avg_cr26 - avg_cr25, 2)
            apu_yoy = _yoy(avg_apu26, avg_apu25)

            # 자동 인사이트
            insight = []
            if rpc_yoy is not None:
                direction = "상승" if rpc_yoy > 0 else "하락"
                insight.append(f"인증당거래액 전체 {rpc_yoy:+.1f}% {direction}")
            if cr_pp is not None:
                if cr_pp < 0:
                    insight.append(f"CR {cr_pp:+.1f}%p 저하가 인증당거래액을 끌어내리는 주요 요인")
                else:
                    insight.append(f"CR {cr_pp:+.1f}%p 개선이 인증당거래액 상승을 견인")
            if apu_yoy is not None:
                if apu_yoy < 0:
                    insight.append(f"객단가도 {apu_yoy:+.1f}% 하락하며 복합 부진")
                else:
                    insight.append(f"객단가 {apu_yoy:+.1f}% 상승으로 부분 상쇄")
            if new_afs:
                low_cr_new = [r for r in new_afs if (r.get("cr_26") or 0) < avg_cr26]
                if low_cr_new:
                    insight.append(f"신규 제휴사({', '.join([r['name'] for r in low_cr_new[:2]])})의 낮은 CR이 전체 평균을 희석")

            if insight:
                st.markdown(f'<div class="info-box">💡 {"<br>".join(insight)}</div>', unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(kpi_card("인증당거래액(평균)", fmt_M(avg_rpc26), fmt_M(avg_rpc25), rpc_yoy), unsafe_allow_html=True)
            with c2:
                st.markdown(kpi_card("CR 효과(평균)", fmt_pct(avg_cr26), fmt_pct(avg_cr25), cr_pp), unsafe_allow_html=True)
            with c3:
                st.markdown(kpi_card("객단가 효과(평균)", fmt_M(avg_apu26), fmt_M(avg_apu25), apu_yoy), unsafe_allow_html=True)

    # 제휴사별 분해 테이블
    section("제휴사별 분해 (거래액 내림차순)")
    if rows:
        rows_html = ""
        for r in rows:
            is_new  = r.get("is_new", False)
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

        st.markdown(f"""
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
        </table></div>
        """, unsafe_allow_html=True)


def _yoy(v26, v25):
    try:
        if v25 and abs(v25) > 0:
            return round((v26 - v25) / abs(v25) * 100, 2)
    except Exception:
        pass
    return None

    st.markdown('---')
    copy_button(make_text_decomp(data), '📋 인증당거래액 분해 데이터 복사 → Claude에 붙여넣기', key='copy_tab2')
