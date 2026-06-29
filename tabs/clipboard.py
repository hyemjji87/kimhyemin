"""tabs/clipboard.py - 탭별 클립보드 복사 버튼"""
import streamlit as st
import streamlit.components.v1 as components


def copy_button(text: str, label: str = "📋 이 데이터 Claude에 붙여넣기용 복사", key: str = "copy"):
    """클립보드 복사 버튼 + 복사할 텍스트 미리보기"""
    
    # JS로 클립보드 복사
    escaped = text.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
    
    components.html(f"""
    <div style="margin:12px 0">
      <button onclick="
        navigator.clipboard.writeText(`{escaped}`).then(()=>{{
          this.textContent='✅ 복사됐어요! Claude 채팅창에 붙여넣기 하세요';
          this.style.background='#16a34a';
          setTimeout(()=>{{
            this.textContent='{label}';
            this.style.background='#4f46e5';
          }}, 3000);
        }})
      " style="
        background:#4f46e5;color:white;border:none;
        padding:9px 18px;border-radius:6px;cursor:pointer;
        font-size:13px;font-weight:600;width:100%
      ">{label}</button>
      <details style="margin-top:8px">
        <summary style="font-size:.75rem;color:#6b7280;cursor:pointer">복사될 내용 미리보기</summary>
        <pre style="font-size:.72rem;background:#f8fafc;padding:10px;border-radius:6px;
                    margin-top:6px;overflow-x:auto;white-space:pre-wrap;color:#374151">{text[:800]}{"..." if len(text)>800 else ""}</pre>
      </details>
    </div>
    """, height=80)


def make_text_overview(data: dict) -> str:
    kpi = data.get("tab1_overview", {}).get("kpi_total", {})
    afs = data.get("tab1_overview", {}).get("affiliate_summary", [])
    meta = data.get("meta", {})
    
    lines = [
        f"[LF몰 제휴 실적 — {meta.get('mtd_end_26','')[:7]} MTD]",
        f"분석기간: {meta.get('mtd_start_26','')} ~ {meta.get('mtd_end_26','')}",
        f"전년동기: {meta.get('mtd_start_25','')} ~ {meta.get('mtd_end_25','')}",
        "",
        "■ 전체 KPI",
        f"당월인증거래액: {kpi.get('revenue_26',0)/1e8:.2f}억 (전년 {kpi.get('revenue_25',0)/1e8:.2f}억, YoY {kpi.get('revenue_yoy',0):+.1f}%)",
        f"인증수: {int(kpi.get('cert_26',0)):,}명 (YoY {kpi.get('cert_yoy',0):+.1f}%)",
        f"구매고객수: {int(kpi.get('buyers_26',0)):,}명",
        f"CR: {kpi.get('cr_26',0):.1f}% (전년 {kpi.get('cr_25',0):.1f}%, {(kpi.get('cr_26',0)-kpi.get('cr_25',0)):+.1f}%p)",
        f"객단가: {kpi.get('arpu_26',0)/1e4:.1f}만원 (YoY {kpi.get('arpu_yoy',0):+.1f}%)",
        f"인증당거래액: {kpi.get('rev_per_cert_26',0)/1e4:.1f}만원 (YoY {kpi.get('rev_per_cert_yoy',0):+.1f}%)",
        "",
        "■ 제휴사별 거래액",
    ]
    for r in afs:
        yoy = f"YoY {r['yoy_pct']:+.1f}%" if r.get('yoy_pct') is not None else "신규"
        lines.append(f"- {r['name']}: {r['revenue_26']/1e6:.1f}M ({yoy}), CR {r['cr_26']:.1f}%")
    return "\n".join(lines)


def make_text_decomp(data: dict) -> str:
    rows = data.get("tab2_decomp", {}).get("rows", [])
    lines = ["[인증당거래액 분해 — CR × 객단가]", ""]
    for r in rows:
        is_new = r.get("is_new", False)
        if is_new:
            lines.append(f"- {r['name']} (신규): 인증당거래액 {(r.get('rev_per_cert_26') or 0)/1e4:.1f}만원, CR {r.get('cr_26',0):.1f}%")
        else:
            lines.append(
                f"- {r['name']}: 인증당거래액 {(r.get('rev_per_cert_26') or 0)/1e4:.1f}만원 (YoY {r.get('rev_per_cert_yoy') or 0:+.1f}%), "
                f"CR {r.get('cr_26',0):.1f}%→{r.get('cr_25',0):.1f}% ({r.get('cr_pp') or 0:+.1f}%p), "
                f"객단가 {(r.get('arpu_26') or 0)/1e4:.1f}만원 (YoY {r.get('arpu_yoy') or 0:+.1f}%)"
            )
    return "\n".join(lines)


def make_text_category(data: dict) -> str:
    cat_rows = data.get("tab4_category", {}).get("cat_rows", [])
    rev_cards = data.get("tab4_category", {}).get("reverse_cards", [])
    lines = ["[카테고리별 당월인증거래액 YoY]", ""]
    for r in cat_rows:
        yoy = f"{r['yoy_pct']:+.1f}%" if r.get('yoy_pct') is not None else "신규"
        lines.append(f"- {r['cat']}: {r['rev_26']/1e6:.1f}M (YoY {yoy}, 비중△ {r.get('wt_pp') or 0:+.1f}%p)")
    
    if rev_cards:
        lines += ["", "■ 전체 추세 역행 제휴사"]
        for card in rev_cards:
            lines.append(f"\n[{card['cat']}] 전체 YoY {card['total_yoy']:+.1f}%")
            for af in card.get("affiliates", []):
                lines.append(f"  - {af['name']}: {af['af_yoy']:+.1f}% (역행)")
                for cb in af.get("cause_brands", []):
                    yoy = f"{cb['yoy_pct']:+.1f}%" if cb.get('yoy_pct') is not None else "N/A"
                    lines.append(f"    📌 원인 브랜드: {cb['brand']} {yoy}")
    return "\n".join(lines)


def make_text_brand(data: dict) -> str:
    t5 = data.get("tab5_brand", {})
    top_up = t5.get("top10_up", [])[:10]
    top_dn = t5.get("top10_dn", [])[:10]
    lines = ["[브랜드 전년비]", "", "■ 상승 TOP10 (전년 5M 이상)"]
    for r in top_up:
        lines.append(f"- {r['brand']}: {r['rev_26']/1e6:.1f}M (YoY {r.get('yoy_pct') or 0:+.1f}%, 비중△ {r.get('wt_pp') or 0:+.1f}%p)")
    lines += ["", "■ 하락 TOP10"]
    for r in top_dn:
        lines.append(f"- {r['brand']}: {r['rev_26']/1e6:.1f}M (YoY {r.get('yoy_pct') or 0:+.1f}%, 비중△ {r.get('wt_pp') or 0:+.1f}%p)")
    return "\n".join(lines)


def make_text_mall(data: dict) -> str:
    kpi = data.get("tab6_mall", {}).get("kpi", {})
    cat_rows = data.get("tab6_mall", {}).get("cat_signal_rows", [])
    stars = data.get("tab6_mall", {}).get("brand_star", [])
    warns = data.get("tab6_mall", {}).get("brand_warn", [])
    lines = [
        "[몰전체 vs 제휴 비교]", "",
        f"몰전체 거래액: {kpi.get('mall_rev_26',0)/1e8:.1f}억 (YoY {kpi.get('mall_rev_yoy') or 0:+.1f}%)",
        f"제휴 거래액: {kpi.get('af_rev_26',0)/1e8:.1f}억 (YoY {kpi.get('af_rev_yoy') or 0:+.1f}%)",
        f"제휴/몰 비중: {kpi.get('af_mall_pct_26',0):.2f}% (전년 {kpi.get('af_mall_pct_25',0):.2f}%, {kpi.get('af_mall_pct_pp') or 0:+.2f}%p)",
        "", "■ 카테고리 시그널",
    ]
    for r in cat_rows:
        sig = r.get('signal','')
        if sig in ['star','warn']:
            lines.append(f"- {r['cat']}: 몰 {r.get('mall_yoy') or 0:+.1f}% / 제휴 {r.get('af_yoy') or 0:+.1f}% [{sig}]")
    lines += ["", "■ ★ 몰↓ 제휴↑ 브랜드 (노출 강화 대상)"]
    for b in stars:
        lines.append(f"- {b['brand']}: 몰 {b.get('mall_yoy') or 0:+.1f}% / 제휴 {b.get('af_yoy') or 0:+.1f}%")
    lines += ["", "■ ⚠ 몰↑ 제휴↓ 브랜드 (CRM 필요)"]
    for b in warns:
        lines.append(f"- {b['brand']}: 몰 {b.get('mall_yoy') or 0:+.1f}% / 제휴 {b.get('af_yoy') or 0:+.1f}%")
    return "\n".join(lines)


def make_text_weekly(data: dict) -> str:
    t7 = data.get("tab7_weekly", {})
    kpi = t7.get("kpi_cur", {})
    kpi_y = t7.get("kpi_prev_year", {})
    cat_rows = t7.get("cat_wk_rows", [])
    brd_rows = t7.get("brd_wk_rows", [])
    
    rev_yoy = (kpi.get('revenue',0)/kpi_y.get('revenue',1)-1)*100 if kpi_y.get('revenue') else 0
    lines = [
        f"[주차 분석 — {t7.get('wk_cur','')}주차]",
        f"당주 거래액: {kpi.get('revenue',0)/1e6:.1f}M (전년동주 {kpi_y.get('revenue',0)/1e6:.1f}M, YoY {rev_yoy:+.1f}%)",
        f"당주 고객수: {kpi.get('buyers',0):,}명",
        "", "■ 카테고리 편차 (제휴비중-몰전체비중)",
    ]
    for r in cat_rows:
        diff = r.get('diff_26') or 0
        lines.append(f"- {r['cat']}: {r['rev_26']/1e6:.1f}M (YoY {r.get('yoy_pct') or 0:+.1f}%, 편차 {diff:+.1f}%p)")
    lines += ["", "■ 브랜드 TOP20 편차"]
    for r in brd_rows[:20]:
        diff = r.get('diff_26') or 0
        lines.append(f"- {r['brand']}({r.get('cat','-')}): {r['rev_26']/1e6:.1f}M (YoY {r.get('yoy_pct') or 0:+.1f}%, 편차 {diff:+.1f}%p)")
    return "\n".join(lines)


def make_text_segment(data: dict) -> str:
    seg_kpi = data.get("tab8_segment", {}).get("seg_kpi", {})
    cat_rows = data.get("tab8_segment", {}).get("cat_rows", [])
    lines = ["[회원구분 분석]", ""]
    for seg, kpi in seg_kpi.items():
        lines.append(f"■ {seg}: 거래액 {kpi['revenue']/1e6:.1f}M ({kpi['rev_pct']:.1f}%), CR {kpi['cr']:.1f}%, 객단가 {kpi['arpu']/1e4:.1f}만원")
    lines += ["", "■ 카테고리별 회원구분 편차"]
    for r in cat_rows:
        lines.append(
            f"- {r['cat']}: 신규 편차 {r.get('diff_신규') or 0:+.1f}%p / "
            f"WIN-BACK {r.get('diff_WIN-BACK') or 0:+.1f}%p / "
            f"기존 {r.get('diff_기존') or 0:+.1f}%p"
        )
    return "\n".join(lines)


def make_text_first(data: dict) -> str:
    kpi = data.get("tab9_first", {}).get("kpi", {})
    cat_rows = data.get("tab9_first", {}).get("cat_rows", [])
    brd_rows = data.get("tab9_first", {}).get("brd_rows", [])
    lines = [
        "[첫구매 분석]",
        f"첫구매 거래액: {kpi.get('fp_rev_26',0)/1e6:.1f}M (제휴채널 대비 {kpi.get('fp_pct_af',0):.1f}%)",
        f"첫구매 고객수: {kpi.get('fp_buyers_26',0):,}명",
        "", "■ 카테고리별 첫구매",
    ]
    for r in cat_rows:
        star = "★" if r.get('w2_star') else ""
        lines.append(f"- {r['cat']}: {r['rev_26']/1e6:.1f}M, 카테내비중 {r['w2_fp_in_cat_pct']:.1f}%{star}")
    lines += ["", "■ 브랜드 TOP15"]
    for r in brd_rows:
        star = "★" if r.get('w2_star') else ""
        lines.append(f"- {r['brand']}({r.get('cat','-')}): {r['rev_26']/1e6:.1f}M, 브랜드내비중 {r['w2_fp_in_brd_pct']:.1f}%{star}")
    return "\n".join(lines)


def make_text_affiliate(data: dict, af_name: str) -> str:
    t3 = data.get("tab3_affiliate", {}).get(af_name, {})
    cat_rows = t3.get("cat_rows", [])
    brd_rows = t3.get("brd_rows", [])
    t1_af = data.get("tab1_overview", {}).get("affiliate_summary", [])
    af_meta = next((r for r in t1_af if r["name"] == af_name), {})
    
    lines = [
        f"[{af_name} 상세 실적]",
        f"거래액: {af_meta.get('revenue_26',0)/1e6:.1f}M (YoY {af_meta.get('yoy_pct') or 0:+.1f}%)",
        f"인증수: {af_meta.get('cert_26',0):,}명 / CR: {af_meta.get('cr_26',0):.1f}%",
        "", "■ 카테고리별",
    ]
    for r in cat_rows:
        yoy = f"{r['yoy_pct']:+.1f}%" if r.get('yoy_pct') is not None else "신규"
        lines.append(f"- {r['cat']}: {r['rev_26']/1e6:.1f}M (YoY {yoy}, 비중△ {r.get('wt_pp') or 0:+.1f}%p)")
    lines += ["", "■ 브랜드 TOP7"]
    for r in brd_rows:
        yoy = f"{r['yoy_pct']:+.1f}%" if r.get('yoy_pct') is not None else "신규"
        lines.append(f"- {r['brand']}: {r['rev_26']/1e6:.1f}M (YoY {yoy})")
    return "\n".join(lines)
