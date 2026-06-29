"""
ai_insight.py
Claude API 호출 → 탭별 인사이트 생성
API 키 없으면 버튼 비활성화
"""

import streamlit as st
import json
import requests


def call_claude(prompt: str, api_key: str) -> str:
    """Claude API 호출"""
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]
    except requests.exceptions.Timeout:
        return "⚠️ 응답 시간 초과. 다시 시도해주세요."
    except Exception as e:
        return f"⚠️ API 오류: {str(e)}"


def render_insight_btn(label: str, prompt: str, key: str):
    """
    AI 인사이트 버튼 렌더링
    - API 키 있으면 → 버튼 클릭 시 Claude 호출
    - API 키 없으면 → 비활성화 안내
    """
    api_key = st.session_state.get("api_key", "")

    if not api_key:
        st.caption("🤖 AI 인사이트: 사이드바에서 Claude API 키를 입력하면 활성화됩니다")
        return

    if st.button(f"🤖 {label}", key=key):
        with st.spinner("Claude가 분석 중..."):
            result = call_claude(prompt, api_key)
        st.markdown(f"""
        <div style="background:#f0f9ff;border-left:4px solid #0ea5e9;
                    padding:12px 16px;border-radius:0 8px 8px 0;
                    font-size:.83rem;line-height:1.75;margin:8px 0">
        🤖 <b>Claude AI 인사이트</b><br><br>{result.replace(chr(10), '<br>')}
        </div>
        """, unsafe_allow_html=True)


def make_prompt_overview(data: dict) -> str:
    kpi = data.get("tab1_overview", {}).get("kpi_total", {})
    af_list = data.get("tab1_overview", {}).get("affiliate_summary", [])[:8]
    return f"""
LF몰 제휴 채널 MTD 실적을 분석해주세요.

[전체 KPI]
- 당월인증거래액: {kpi.get('revenue_26',0)/1e8:.2f}억 (전년: {kpi.get('revenue_25',0)/1e8:.2f}억, YoY: {kpi.get('revenue_yoy',0):+.1f}%)
- 인증수: {kpi.get('cert_26',0):,}명 (YoY: {kpi.get('cert_yoy',0):+.1f}%)
- CR: {kpi.get('cr_26',0):.1f}% (전년: {kpi.get('cr_25',0):.1f}%)
- 객단가: {kpi.get('arpu_26',0)/1e4:.1f}만원 (YoY: {kpi.get('arpu_yoy',0):+.1f}%)

[제휴사별 상위 실적]
{chr(10).join([f"- {r['name']}: {r['revenue_26']/1e6:.1f}M (YoY: {r['yoy_pct']:+.1f}%)" if r.get('yoy_pct') else f"- {r['name']}: {r['revenue_26']/1e6:.1f}M (신규)" for r in af_list])}

위 데이터를 바탕으로:
1. 전체 성과 평가 (2~3줄)
2. 주목할 제휴사 (성장/부진 각 1개씩 이유 포함)
3. 다음 달 중점 관리 포인트 1가지

간결하게 한국어로 답해주세요.
"""


def make_prompt_category(data: dict) -> str:
    cat_rows = data.get("tab4_category", {}).get("cat_rows", [])[:10]
    rev_cards = data.get("tab4_category", {}).get("reverse_cards", [])[:5]
    return f"""
LF몰 제휴 카테고리별 YoY 실적입니다.

[카테고리별 성장률 상위/하위]
{chr(10).join([f"- {r['cat']}: {r['rev_26']/1e6:.1f}M (YoY: {r['yoy_pct']:+.1f}% / 비중△: {r['wt_pp']:+.1f}%p)" if r.get('yoy_pct') else f"- {r['cat']}: {r['rev_26']/1e6:.1f}M (신규)" for r in cat_rows])}

[전체 추세 역행 제휴사]
{chr(10).join([f"- [{c['cat']}] 전체YoY {c['total_yoy']:+.1f}% 인데 역행: " + ", ".join([a['name'] for a in c['affiliates']]) for c in rev_cards]) if rev_cards else "없음"}

위 데이터 분석:
1. 핵심 성장/부진 카테고리 원인 해석
2. 역행 제휴사가 있다면 그 의미
3. MD/마케팅 액션 제안 1~2가지

간결하게 한국어로 답해주세요.
"""


def make_prompt_brand(data: dict) -> str:
    top_up = data.get("tab5_brand", {}).get("top10_up", [])[:5]
    top_dn = data.get("tab5_brand", {}).get("top10_dn", [])[:5]
    return f"""
LF몰 제휴 브랜드 YoY 실적입니다.

[상승 TOP5]
{chr(10).join([f"- {r['brand']}: {r['rev_26']/1e6:.1f}M (YoY: {r['yoy_pct']:+.1f}%)" for r in top_up])}

[하락 TOP5]
{chr(10).join([f"- {r['brand']}: {r['rev_26']/1e6:.1f}M (YoY: {r['yoy_pct']:+.1f}%)" for r in top_dn])}

위 데이터 분석:
1. 상승 브랜드 공통 특징
2. 하락 브랜드 긴급 대응 우선순위
3. 제휴 채널에서 집중 노출할 브랜드 추천 1~2개

간결하게 한국어로 답해주세요.
"""


def make_prompt_mall(data: dict) -> str:
    kpi = data.get("tab6_mall", {}).get("kpi", {})
    stars = data.get("tab6_mall", {}).get("brand_star", [])[:5]
    warns = data.get("tab6_mall", {}).get("brand_warn", [])[:5]
    return f"""
LF몰 전체 vs 제휴 채널 비교 데이터입니다.

[KPI 비교]
- 몰전체 거래액: {kpi.get('mall_rev_26',0)/1e8:.1f}억 (YoY: {kpi.get('mall_rev_yoy',0):+.1f}%)
- 제휴 거래액: {kpi.get('af_rev_26',0)/1e8:.1f}억 (YoY: {kpi.get('af_rev_yoy',0):+.1f}%)
- 제휴/몰 비중: {kpi.get('af_mall_pct_26',0):.2f}% (전년: {kpi.get('af_mall_pct_25',0):.2f}%, {kpi.get('af_mall_pct_pp',0):+.2f}%p)

[★ 몰↓ 제휴↑ 브랜드 (제휴 강화 대상)]
{chr(10).join([f"- {b['brand']}: 몰 {b['mall_yoy']:+.1f}% / 제휴 {b['af_yoy']:+.1f}%" for b in stars]) if stars else "없음"}

[⚠ 몰↑ 제휴↓ 브랜드 (CRM 긴급 대응)]
{chr(10).join([f"- {b['brand']}: 몰 {b['mall_yoy']:+.1f}% / 제휴 {b['af_yoy']:+.1f}%" for b in warns]) if warns else "없음"}

분석:
1. 제휴 채널 기여도 변화 평가
2. ★ 브랜드 제휴 강화 전략
3. ⚠ 브랜드 CRM 대응 방안

간결하게 한국어로 답해주세요.
"""


def make_prompt_weekly(data: dict) -> str:
    t7 = data.get("tab7_weekly", {})
    kpi = t7.get("kpi_cur", {})
    kpi_y = t7.get("kpi_prev_year", {})
    top_cats = t7.get("cat_wk_rows", [])[:6]
    return f"""
LF몰 제휴 {t7.get('wk_cur','')} 주차 실적입니다.

[주차 KPI]
- 거래액: {kpi.get('revenue',0)/1e6:.1f}M (전년동주: {kpi_y.get('revenue',0)/1e6:.1f}M, YoY: {(kpi.get('revenue',0)/kpi_y.get('revenue',1)-1)*100:+.1f}%)
- 구매고객: {kpi.get('buyers',0):,}명

[카테고리별 편차 상위]
{chr(10).join([f"- {r['cat']}: 제휴비중 {r['af_wt_26']:.1f}% / 몰비중 {r['mall_wt_26']:.1f}% / 편차 {r['diff_26']:+.1f}%p" for r in top_cats])}

분석:
1. 이번 주 주요 특이점
2. 편차가 큰 카테고리 원인 해석
3. 다음 주 집중 관리 포인트

간결하게 한국어로 답해주세요.
"""


def make_prompt_segment(data: dict) -> str:
    seg = data.get("tab8_segment", {}).get("seg_kpi", {})
    top_cats = data.get("tab8_segment", {}).get("cat_rows", [])[:6]
    return f"""
LF몰 제휴 회원구분별 실적입니다.

[회원구분 KPI]
{chr(10).join([f"- {k}: 거래액 {v['revenue']/1e6:.1f}M ({v['rev_pct']:.1f}%) / CR {v['cr']:.1f}% / 객단가 {v['arpu']/1e4:.1f}만원" for k, v in seg.items()])}

[카테고리별 신규 고객 편차 상위]
{chr(10).join([f"- {r['cat']}: 신규편차 {r.get('diff_신규',0):+.1f}%p / WIN-BACK편차 {r.get('diff_WIN-BACK',0):+.1f}%p" for r in top_cats[:5]])}

분석:
1. 신규/WIN-BACK/기존 고객 구조 평가
2. 신규 고객 유입이 강한 카테고리 활용 방안
3. WIN-BACK CRM 전략 제안

간결하게 한국어로 답해주세요.
"""


def make_prompt_first(data: dict) -> str:
    kpi = data.get("tab9_first", {}).get("kpi", {})
    top_cats = data.get("tab9_first", {}).get("cat_rows", [])[:6]
    top_brds = data.get("tab9_first", {}).get("brd_rows", [])[:5]
    return f"""
LF몰 제휴 첫구매 분석입니다.

[KPI]
- 첫구매 거래액: {kpi.get('fp_rev_26',0)/1e6:.1f}M
- 제휴 전체 대비: {kpi.get('fp_pct_af',0):.1f}%
- 몰전체 대비: {kpi.get('fp_pct_mall',0):.1f}%

[카테고리별 첫구매 비중]
{chr(10).join([f"- {r['cat']}: 카테내비중 {r['w2_fp_in_cat_pct']:.1f}%{'★' if r.get('w2_star') else ''}" for r in top_cats])}

[첫구매 앵커 브랜드]
{chr(10).join([f"- {r['brand']}: 브랜드내 {r['w2_fp_in_brd_pct']:.1f}%{'★' if r.get('w2_star') else ''}" for r in top_brds])}

분석:
1. 첫구매 비율 수준 평가
2. 신규 고객 획득 앵커 브랜드/카테고리
3. 첫구매 후 재구매 유도 CRM 방향

간결하게 한국어로 답해주세요.
"""
