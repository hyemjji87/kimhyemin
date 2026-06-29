"""
LF몰 제휴 실적 분석 앱 (통합본)
=================================
① Raw 엑셀 업로드 → 전처리
② 바로 대시보드 9탭 출력
③ 탭마다 Claude AI 인사이트 버튼
"""

import streamlit as st
import json
from datetime import date, timedelta

st.set_page_config(
    page_title="LF몰 제휴 실적 분석",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 전역 CSS ──
st.markdown("""
<style>
.dash-hdr {
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    padding: 16px 24px; border-radius: 10px;
    color: white; margin-bottom: 16px;
}
.dash-hdr h1 { color: white; margin: 0; font-size: 1.3rem; }
.dash-hdr p  { opacity: .75; margin: 4px 0 0; font-size: .82rem; }
.kcard {
    background: white; border-radius: 8px; padding: 14px 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,.08);
    border-left: 4px solid #4f46e5; margin-bottom: 10px;
}
.kcard .label { font-size: .72rem; color: #9ca3af; margin-bottom: 4px; }
.kcard .val   { font-size: 1.3rem; font-weight: 700; color: #1e293b; }
.kcard .yoy   { font-size: .75rem; margin-top: 3px; }
.info-box {
    background: #eef2ff; border-left: 4px solid #4f46e5;
    padding: 10px 14px; border-radius: 0 6px 6px 0;
    font-size: .82rem; line-height: 1.7; margin: 8px 0;
}
.warn-box {
    background: #fff7ed; border-left: 4px solid #f59e0b;
    padding: 10px 14px; border-radius: 0 6px 6px 0;
    font-size: .82rem; line-height: 1.7; margin: 8px 0;
}
.stitle {
    font-size: .9rem; font-weight: 700; color: #374151;
    border-left: 3px solid #4f46e5; padding-left: 8px;
    margin: 14px 0 8px;
}
.badge-up  { background:#dcfce7;color:#166534;padding:2px 7px;border-radius:4px;font-size:.72rem;font-weight:600; }
.badge-dn  { background:#fee2e2;color:#991b1b;padding:2px 7px;border-radius:4px;font-size:.72rem;font-weight:600; }
.badge-new { background:#dbeafe;color:#1e40af;padding:2px 7px;border-radius:4px;font-size:.72rem;font-weight:600; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
# 사이드바
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 LF몰 제휴 실적 분석")
    st.markdown("---")

    # ── 파일 업로드 ──
    st.markdown("### 📁 Step 1. 파일 업로드")
    file_cur = st.file_uploader(
        "① 당년 Raw 파일",
        type=["xlsx"], key="cur",
        help="2606_제휴_실적_raw.xlsx"
    )
    file_25_ui = st.file_uploader(
        "② 2025 유입·인증 파일",
        type=["xlsx"], key="ui25",
        help="2025_실적_raw_유입인증.xlsx"
    )
    file_25_sale = st.file_uploader(
        "③ 2025 매출 분기 파일",
        type=["xlsx"], key="sale25",
        help="2025_실적_raw_매출_2Q.xlsx"
    )

    st.markdown("---")
    st.markdown("### ⚙️ Step 2. 분석 설정")
    mtd_end = st.date_input(
        "당년 MTD 마감일",
        value=None,
        help="예: 2026-06-23"
    )
    exclude_ssng = st.checkbox("SSNGCD03 UV 제외", value=True)

    st.markdown("---")
    st.markdown("### 🤖 Step 3. AI 인사이트 (선택)")
    api_key = st.text_input(
        "Claude API 키",
        type="password",
        placeholder="sk-ant-... (없어도 됩니다)",
    )
    if api_key:
        st.session_state["api_key"] = api_key
        st.success("API 키 저장됨 ✅")

    st.markdown("---")
    run_btn = st.button("🚀 분석 실행", type="primary", use_container_width=True)




# ─────────────────────────────────────────
# 초기 화면
# ─────────────────────────────────────────
if "dash_data" not in st.session_state and not run_btn:
    st.markdown("""
    <div class="dash-hdr">
      <h1>📊 LF몰 제휴 실적 분석 대시보드</h1>
      <p>왼쪽 사이드바에서 파일을 업로드하고 분석 실행 버튼을 눌러주세요</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("**Step 1**\n\n엑셀 파일 3개 업로드")
    with c2:
        st.info("**Step 2**\n\nMTD 날짜 입력 후\n분석 실행")
    with c3:
        st.info("**Step 3** (선택)\n\nAPI 키 입력 시\nAI 인사이트 활성화")
    st.stop()


# ─────────────────────────────────────────
# 분석 실행
# ─────────────────────────────────────────
if run_btn:
    errors = []
    if not file_cur:    errors.append("① 당년 Raw 파일을 업로드해주세요")
    if not file_25_ui:  errors.append("② 2025 유입·인증 파일을 업로드해주세요")
    if not file_25_sale: errors.append("③ 2025 매출 분기 파일을 업로드해주세요")
    if not mtd_end:     errors.append("MTD 마감일을 입력해주세요")

    if errors:
        for e in errors:
            st.error(e)
        st.stop()

    with st.spinner("🔄 전처리 중... (30~90초 소요)"):
        try:
            from preprocessor import Preprocessor
            prep = Preprocessor(
                file_cur=file_cur,
                file_25_ui=file_25_ui,
                file_25_sale=file_25_sale,
                mtd_end=str(mtd_end),
                exclude_ssng=exclude_ssng,
            )
            data = prep.run()
            st.session_state["dash_data"] = data
            st.session_state["mtd_end_str"] = str(mtd_end)
            # 주차 선택을 위해 raw 데이터 및 pivot_week 보존
            st.session_state["df26"] = prep.df26
            st.session_state["df25"] = prep.df25
            st.session_state["mall26"] = prep.mall26
            st.session_state["mall25"] = prep.mall25
            st.session_state["pivot_week_map"] = prep.pivot_week
            st.success("✅ 전처리 완료! 대시보드를 확인하세요.")
        except Exception as ex:
            import traceback
            st.error(f"오류 발생: {ex}")
            st.code(traceback.format_exc())
            st.stop()


# ─────────────────────────────────────────
# 대시보드 렌더링
# ─────────────────────────────────────────
if "dash_data" not in st.session_state:
    st.stop()

data = st.session_state["dash_data"]
meta = data.get("meta", {})

# ── 헤더 ──
qc = meta.get("quality_check", {})
warns = [(k, v) for k, v in qc.items() if not v.get("ok")]

st.markdown(f"""
<div class="dash-hdr">
  <h1>📊 LF몰 제휴 실적 대시보드 — {meta.get('mtd_end_26','')[:7]} MTD</h1>
  <p>
    분석 기간: {meta.get('mtd_start_26','')} ~ {meta.get('mtd_end_26','')} &nbsp;|&nbsp;
    전년 동기: {meta.get('mtd_start_25','')} ~ {meta.get('mtd_end_25','')} &nbsp;|&nbsp;
    제휴사 {meta.get('affiliate_count',0)}개
    {'&nbsp;|&nbsp; ⚠️ SSNGCD03 UV 제외' if meta.get('exclude_ssng') else ''}
    {'&nbsp;|&nbsp; ⚠️ 데이터 품질 경고 ' + str(len(warns)) + '건' if warns else ''}
  </p>
</div>
""", unsafe_allow_html=True)

# JSON 다운로드 버튼 (헤더 바로 아래)
if "dash_data" in st.session_state:
    json_bytes = json.dumps(
        st.session_state["dash_data"],
        ensure_ascii=False, default=str, indent=2
    ).encode("utf-8")
    mtd_str = str(st.session_state.get("mtd_end_str","")).replace("-","")
    col_dl1, col_dl2 = st.columns([4, 1])
    with col_dl2:
        st.download_button(
            "⬇️ 전체 JSON 다운로드",
            data=json_bytes,
            file_name=f"dashboard_data_{mtd_str}.json",
            mime="application/json",
            use_container_width=True,
            help="Claude에게 전체 데이터 분석 요청 시 사용"
        )

# 품질 경고
if warns:
    with st.expander(f"⚠️ 데이터 품질 경고 {len(warns)}건 (클릭하여 확인)", expanded=False):
        for k, v in warns:
            st.markdown(
                f'<div class="warn-box">⚠️ <b>{k}</b>: {v.get("msg","")}</div>',
                unsafe_allow_html=True
            )

# ── 9탭 ──
from tabs import tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9

tabs = st.tabs([
    "📊 전체 Overview",
    "🔍 인증당거래액 분해",
    "🏢 제휴사별 전년비",
    "📦 카테고리 전년비",
    "🏷️ 브랜드 전년비",
    "🏬 몰전체 비교",
    "📅 주차 분석",
    "👥 회원구분",
    "🛍️ 첫구매",
])

with tabs[0]: tab1.render(data, meta)
with tabs[1]: tab2.render(data, meta)
with tabs[2]: tab3.render(data, meta)
with tabs[3]: tab4.render(data, meta)
with tabs[4]: tab5.render(data, meta)
with tabs[5]: tab6.render(data, meta)
with tabs[6]: tab7.render(data, meta)
with tabs[7]: tab8.render(data, meta)
with tabs[8]: tab9.render(data, meta)
