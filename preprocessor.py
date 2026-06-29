"""
preprocessor.py
===============
LF몰 제휴 실적 Raw → 대시보드용 JSON 전처리 엔진
운영가이드 v4 기준
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import io
import warnings
warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────────────────────
# 유틸
# ─────────────────────────────────────────────────────────────
def _safe(v):
    """None/NaN → None 변환 (JSON 직렬화 안전)"""
    if v is None:
        return None
    try:
        if np.isnan(float(v)):
            return None
        return v
    except Exception:
        return v


def _yoy(v26, v25):
    """YoY % 계산"""
    try:
        if v25 and abs(v25) > 0:
            return round((v26 - v25) / abs(v25) * 100, 2)
    except Exception:
        pass
    return None


def _pp(v26, v25):
    """%p 차이"""
    try:
        if v26 is not None and v25 is not None:
            return round(v26 - v25, 2)
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────────────────────
# 메인 Preprocessor 클래스
# ─────────────────────────────────────────────────────────────
class Preprocessor:
    """
    Parameters
    ----------
    file_cur      : 당년 raw xlsx (Streamlit UploadedFile)
    file_25_ui    : 2025 유입·인증 xlsx
    file_25_sale  : 2025 매출 분기 xlsx
    mtd_end       : MTD 마감일 문자열 "YYYY-MM-DD"
    exclude_ssng  : SSNGCD03 UV 제외 여부
    """

    SSNG_EXCLUDE = "SSNGCD03"

    def __init__(self, file_cur, file_25_ui, file_25_sale, mtd_end, exclude_ssng=True):
        self.file_cur = file_cur
        self.file_25_ui = file_25_ui
        self.file_25_sale = file_25_sale
        self.mtd_end = pd.to_datetime(mtd_end)
        self.exclude_ssng = exclude_ssng
        self.mtd_start_26 = self.mtd_end.replace(day=1)
        self.mtd_start_25 = self.mtd_start_26 - pd.DateOffset(years=1)
        self.mtd_end_25 = self.mtd_end - pd.DateOffset(years=1)

    # ─────────────────────────────────────────────────────────
    # 데이터 로딩
    # ─────────────────────────────────────────────────────────
    def _load_excel(self, f, sheet, header=0, skiprows=None):
        """Streamlit UploadedFile or path → DataFrame"""
        if hasattr(f, "read"):
            f.seek(0)
        kw = dict(engine="openpyxl", header=header)
        if skiprows:
            kw["skiprows"] = skiprows
        return pd.read_excel(f, sheet_name=sheet, **kw)

    def _load_all(self):
        """모든 시트 로딩 + 기본 전처리"""

        # ── Step 1: 피벗 먼저 로드 (제휴사명 정제 코드맵 + 주차코드) ──
        piv_raw = self._load_excel(self.file_cur, "피벗", header=None)
        self.pivot_af = {}   # "930014-신한탑스" → "신한카드 TOPS"
        self.pivot_week = {} # "2026-06-03" → "26_6_1"
        for _, row in piv_raw.iterrows():
            code = row.iloc[1]
            name = row.iloc[2]
            dt   = row.iloc[4]
            wk   = row.iloc[6]
            if pd.notna(code) and pd.notna(name) and str(code).startswith(("0","9")):
                self.pivot_af[str(code).strip()] = str(name).strip()
            if pd.notna(dt) and pd.notna(wk):
                try:
                    self.pivot_week[pd.to_datetime(dt).strftime("%Y-%m-%d")] = str(wk).strip()
                except Exception:
                    pass

        # 코드→정제명 함수
        def _resolve_af_name(code_str):
            if pd.isna(code_str):
                return None
            s = str(code_str).strip()
            if s in self.pivot_af:
                return self.pivot_af[s]
            if "-" in s:
                return s.split("-", 1)[-1].strip()
            return s

        self._resolve_af_name = _resolve_af_name

        # ── Step 2: 당년 인증거래액 ──
        df26 = self._load_excel(self.file_cur, "인증거래액_26")
        df26.columns = [str(c).strip() for c in df26.columns]
        df26["정산일시일"] = pd.to_datetime(df26["정산일시일"], errors="coerce")
        df26["거래액_VAT제외"] = pd.to_numeric(df26["거래액_VAT제외"], errors="coerce")
        df26["제휴사명"] = df26["제휴처구분3"].apply(self._resolve_af_name)
        self.df26 = df26[df26["정산일시일"] <= self.mtd_end].copy()

        # ── Step 3: 2025 인증거래액 ──
        df25 = self._load_excel(self.file_25_sale, "인증거래액_4-6월")
        df25.columns = [str(c).strip() for c in df25.columns]
        df25["정산일시일"] = pd.to_datetime(df25["정산일시일"], errors="coerce")
        df25["거래액_VAT제외"] = pd.to_numeric(df25["거래액_VAT제외"], errors="coerce")
        df25["제휴사명"] = df25["제휴처구분3"].apply(self._resolve_af_name)
        mask_25 = (df25["정산일시일"] >= self.mtd_start_25) & \
                  (df25["정산일시일"] <= self.mtd_end_25)
        self.df25 = df25[mask_25].copy()

        # ── 당년 인증회원 ──
        cert26 = self._load_excel(self.file_cur, "인증회원_26")
        cert26.columns = [str(c).strip() for c in cert26.columns]
        cert26["인증일시일"] = pd.to_datetime(cert26["인증일시일"], errors="coerce")
        mask_c26 = (cert26["인증일시일"] >= self.mtd_start_26) & \
                   (cert26["인증일시일"] <= self.mtd_end)
        self.cert26 = cert26[mask_c26].copy()

        # ── 2025 인증회원 ──
        cert25 = self._load_excel(self.file_25_ui, "인증_25")
        cert25.columns = [str(c).strip() for c in cert25.columns]
        cert25["인증일시일"] = pd.to_datetime(cert25["인증일시일"], errors="coerce")
        # 제휴사 컬럼: 수식이면 None → 제휴처구분3에서 재추출
        cert25["제휴사명_raw"] = cert25.get("제휴사", cert25.get("제휴처구분4", ""))
        cert25["제휴사명_raw"] = cert25["제휴사명_raw"].apply(
            lambda x: str(x).split("-", 1)[-1].strip() if pd.notna(x) and "-" in str(x) else str(x)
        )
        mask_c25 = (cert25["인증일시일"] >= self.mtd_start_25) & \
                   (cert25["인증일시일"] <= self.mtd_end_25)
        self.cert25 = cert25[mask_c25].copy()

        # ── 당년 유입 ──
        uv26 = self._load_excel(self.file_cur, "유입실적_26")
        uv26.columns = [str(c).strip() for c in uv26.columns]
        uv26["★일자일"] = pd.to_datetime(uv26["★일자일"], errors="coerce")
        mask_uv26 = (uv26["★일자일"] >= self.mtd_start_26) & \
                    (uv26["★일자일"] <= self.mtd_end)
        self.uv26 = uv26[mask_uv26].copy()

        # ── 2025 유입 ──
        uv25 = self._load_excel(self.file_25_ui, "유입_25")
        uv25.columns = [str(c).strip() for c in uv25.columns]
        uv25["★일자일"] = pd.to_datetime(uv25["★일자일"], errors="coerce")
        mask_uv25 = (uv25["★일자일"] >= self.mtd_start_25) & \
                    (uv25["★일자일"] <= self.mtd_end_25)
        self.uv25 = uv25[mask_uv25].copy()

        # ── 몰전체 ──
        mall26 = self._load_excel(self.file_cur, "몰전체_26", header=1)
        mall26.columns = [str(c).strip() for c in mall26.columns]
        mall26 = mall26[mall26["결제_연월(YYYYMM)"] == int(self.mtd_end.strftime("%Y%m"))].copy()
        self.mall26 = mall26

        mall25_raw = self._load_excel(self.file_25_ui, "LF몰_25")
        mall25_raw.columns = [str(c).strip() for c in mall25_raw.columns]
        self.mall25 = mall25_raw[
            mall25_raw["결제_연월(YYYYMM)"] == int(self.mtd_end_25.strftime("%Y%m"))
        ].copy()

    # ─────────────────────────────────────────────────────────
    # 핵심 집계 함수
    # ─────────────────────────────────────────────────────────
    def _af_revenue(self, df, col_af="제휴사명"):
        """당월인증=Y + 판매 + VAT제외 거래액 제휴사별 집계"""
        flt = df[
            (df["당월인증"] == "Y") &
            (df["정산구분"] == "판매")
        ].copy()
        return flt.groupby(col_af)["거래액_VAT제외"].sum()

    def _af_buyers(self, df, col_af="제휴사명"):
        """당월인증=Y + 판매 구매고객 unique count"""
        flt = df[
            (df["당월인증"] == "Y") &
            (df["정산구분"] == "판매")
        ].copy()
        return flt.groupby(col_af)["고객번호"].nunique()

    def _af_cert(self, cert_df, col_af="제휴사명"):
        """인증수 제휴사별 합계"""
        return cert_df.groupby(col_af)["총합계"].sum()

    def _af_uv(self, uv_df, col_af="제휴사명", exclude_ssng=True):
        """UV 제휴사별 합계 (SSNGCD03 제외 옵션)"""
        df = uv_df.copy()
        if exclude_ssng:
            df = df[df.get("AF코드", df.get("AF코드", "")) != self.SSNG_EXCLUDE]
        col = "제휴사명" if "제휴사명" in df.columns else df.columns[0]
        return df.groupby(col)["★UV"].sum()

    def _get_affiliate_list(self):
        """분석 대상 제휴사 목록 결정 (운영가이드 §3)"""
        rev26 = self._af_revenue(self.df26)
        rev25 = self._af_revenue(self.df25)
        cert26 = self._af_cert(self.cert26, col_af=self._cert26_af_col())
        cert25 = self._af_cert(self.cert25, col_af="제휴사명_raw")

        all_afs = set(rev26.index) | set(rev25.index) | set(cert26.index) | set(cert25.index)
        result = []
        for af in sorted(all_afs):
            r26 = rev26.get(af, 0)
            r25 = rev25.get(af, 0)
            c26 = cert26.get(af, 0)
            c25 = cert25.get(af, 0)
            if (r26 + r25) >= 5_000_000 or (c26 + c25) >= 20:
                result.append(af)
        return result

    def _cert26_af_col(self):
        """인증회원_26에서 제휴사명 컬럼 반환"""
        cols = self.cert26.columns.tolist()
        for c in ["제휴사", "제휴처구분3", "제휴처구분4"]:
            if c in cols:
                return c
        return cols[-1]

    # ─────────────────────────────────────────────────────────
    # 탭별 집계
    # ─────────────────────────────────────────────────────────
    def _tab1(self, af_list):
        """탭1: 전체 Overview"""

        # 전체 KPI
        def _total_kpi(df, cert_df, uv_df, cert_af_col):
            flt = df[(df["당월인증"] == "Y") & (df["정산구분"] == "판매")]
            rev   = float(flt["거래액_VAT제외"].sum())
            buyers = int(flt["고객번호"].nunique())
            cert  = int(cert_df["총합계"].sum())
            uv_df2 = uv_df.copy()
            if self.exclude_ssng and "AF코드" in uv_df2.columns:
                uv_df2 = uv_df2[uv_df2["AF코드"] != self.SSNG_EXCLUDE]
            uv    = int(uv_df2["★UV"].sum()) if "★UV" in uv_df2.columns else 0
            cr    = round(buyers / cert * 100, 2) if cert > 0 else 0
            apu   = round(rev / buyers, 0) if buyers > 0 else 0
            rpca  = round(rev / cert, 0) if cert > 0 else 0
            return dict(revenue=rev, buyers=buyers, cert=cert, uv=uv,
                        cr=cr, arpu=apu, rev_per_cert=rpca)

        cert26_af_col = self._cert26_af_col()
        cert25_af_col = "제휴사명_raw"

        kpi26 = _total_kpi(self.df26, self.cert26, self.uv26, cert26_af_col)
        kpi25 = _total_kpi(self.df25, self.cert25, self.uv25, cert25_af_col)

        kpi_total = {}
        for k in kpi26:
            kpi_total[f"{k}_26"] = _safe(kpi26[k])
            kpi_total[f"{k}_25"] = _safe(kpi25[k])
            kpi_total[f"{k}_yoy"] = _safe(_yoy(kpi26[k], kpi25[k]))

        # 제휴사별 요약
        rev26s  = self._af_revenue(self.df26)
        rev25s  = self._af_revenue(self.df25)
        cert26s = self._af_cert(self.cert26, col_af=cert26_af_col)
        cert25s = self._af_cert(self.cert25, col_af=cert25_af_col)
        uv26s   = self._af_uv(self.uv26, exclude_ssng=self.exclude_ssng)
        uv25s   = self._af_uv(self.uv25, exclude_ssng=self.exclude_ssng)
        buy26s  = self._af_buyers(self.df26)
        buy25s  = self._af_buyers(self.df25)

        af_summary = []
        for af in af_list:
            r26  = float(rev26s.get(af, 0))
            r25  = float(rev25s.get(af, 0))
            c26  = int(cert26s.get(af, 0))
            c25  = int(cert25s.get(af, 0))
            uv26v = int(uv26s.get(af, 0))
            uv25v = int(uv25s.get(af, 0))
            b26  = int(buy26s.get(af, 0))
            b25  = int(buy25s.get(af, 0))
            cr26 = round(b26/c26*100,2) if c26 > 0 else 0
            cr25 = round(b25/c25*100,2) if c25 > 0 else 0
            af_summary.append(dict(
                name=af,
                revenue_26=r26, revenue_25=r25, yoy_pct=_yoy(r26, r25),
                cert_26=c26, cert_25=c25,
                buyers_26=b26, buyers_25=b25,
                cr_26=cr26, cr_25=cr25,
                uv_26=uv26v, uv_25=uv25v,
                is_new=(r25 == 0 and c25 == 0),
            ))
        af_summary.sort(key=lambda x: x["revenue_26"], reverse=True)

        # 일자별 거래액 추이
        flt26 = self.df26[(self.df26["당월인증"]=="Y") & (self.df26["정산구분"]=="판매")]
        flt25 = self.df25[(self.df25["당월인증"]=="Y") & (self.df25["정산구분"]=="판매")]
        daily26 = flt26.groupby(flt26["정산일시일"].dt.date)["거래액_VAT제외"].sum()
        daily25 = flt25.groupby(flt25["정산일시일"].dt.date)["거래액_VAT제외"].sum()

        # 일자 정렬
        days26 = sorted(daily26.index)
        daily_trend = []
        for d in days26:
            d_str = str(d)
            d25 = (datetime.strptime(d_str, "%Y-%m-%d") - pd.DateOffset(years=1)).strftime("%Y-%m-%d")
            daily_trend.append(dict(
                date_26=d_str,
                date_25=d25,
                rev_26=_safe(float(daily26.get(d, 0))),
                rev_25=_safe(float(daily25.get(
                    (datetime.strptime(d_str,"%Y-%m-%d") - pd.DateOffset(years=1)).date(),
                    0
                ))),
            ))

        return dict(
            kpi_total=kpi_total,
            affiliate_summary=af_summary,
            daily_trend=daily_trend,
        )

    def _tab2(self, af_list):
        """탭2: 인증당거래액 분해 (CR × 객단가)"""
        cert26_af_col = self._cert26_af_col()
        cert25_af_col = "제휴사명_raw"

        rev26s  = self._af_revenue(self.df26)
        rev25s  = self._af_revenue(self.df25)
        cert26s = self._af_cert(self.cert26, col_af=cert26_af_col)
        cert25s = self._af_cert(self.cert25, col_af=cert25_af_col)
        buy26s  = self._af_buyers(self.df26)
        buy25s  = self._af_buyers(self.df25)

        rows = []
        for af in af_list:
            r26, r25 = float(rev26s.get(af,0)), float(rev25s.get(af,0))
            c26, c25 = int(cert26s.get(af,0)), int(cert25s.get(af,0))
            b26, b25 = int(buy26s.get(af,0)), int(buy25s.get(af,0))
            cr26 = round(b26/c26*100,2) if c26>0 else 0
            cr25 = round(b25/c25*100,2) if c25>0 else 0
            apu26 = round(r26/b26,0) if b26>0 else 0
            apu25 = round(r25/b25,0) if b25>0 else 0
            rpc26 = round(r26/c26,0) if c26>0 else 0
            rpc25 = round(r25/c25,0) if c25>0 else 0
            rows.append(dict(
                name=af,
                rev_per_cert_26=rpc26, rev_per_cert_25=rpc25,
                rev_per_cert_yoy=_yoy(rpc26, rpc25),
                cr_26=cr26, cr_25=cr25, cr_pp=_pp(cr26, cr25),
                arpu_26=apu26, arpu_25=apu25, arpu_yoy=_yoy(apu26, apu25),
                is_new=(r25==0 and c25==0),
            ))
        rows.sort(key=lambda x: x["rev_per_cert_26"] or 0, reverse=True)
        return dict(rows=rows)

    def _tab3(self, af_list):
        """탭3: 제휴사별 카테고리·브랜드"""
        data = {}

        flt26 = self.df26[(self.df26["당월인증"]=="Y") & (self.df26["정산구분"]=="판매")].copy()
        flt25 = self.df25[(self.df25["당월인증"]=="Y") & (self.df25["정산구분"]=="판매")].copy()
        tot26 = float(flt26["거래액_VAT제외"].sum())
        tot25 = float(flt25["거래액_VAT제외"].sum())

        for af in af_list:
            af26 = flt26[flt26["제휴사명"] == af]
            af25 = flt25[flt25["제휴사명"] == af]
            af_tot26 = float(af26["거래액_VAT제외"].sum())
            af_tot25 = float(af25["거래액_VAT제외"].sum())

            # 카테고리별
            cat26 = af26.groupby("물리대카테")["거래액_VAT제외"].sum()
            cat25 = af25.groupby("물리대카테")["거래액_VAT제외"].sum()
            all_cats = sorted(set(cat26.index) | set(cat25.index))
            cat_rows = []
            for cat in all_cats:
                r26 = float(cat26.get(cat, 0))
                r25 = float(cat25.get(cat, 0))
                w26 = round(r26/af_tot26*100,1) if af_tot26>0 else 0
                w25 = round(r25/af_tot25*100,1) if af_tot25>0 else 0
                cat_rows.append(dict(
                    cat=cat, rev_26=r26, rev_25=r25,
                    yoy_pct=_yoy(r26, r25),
                    wt_26=w26, wt_25=w25, wt_pp=_pp(w26, w25),
                ))
            cat_rows.sort(key=lambda x: x["rev_26"], reverse=True)

            # 브랜드 TOP7
            brd26 = af26.groupby("Admin브랜드명")["거래액_VAT제외"].sum()
            brd25 = af25.groupby("Admin브랜드명")["거래액_VAT제외"].sum()
            top7 = brd26.nlargest(7).index.tolist()
            brd_rows = []
            for b in top7:
                r26 = float(brd26.get(b, 0))
                r25 = float(brd25.get(b, 0))
                brd_rows.append(dict(
                    brand=b, rev_26=r26, rev_25=r25, yoy_pct=_yoy(r26, r25)
                ))

            data[af] = dict(
                af_total_26=af_tot26, af_total_25=af_tot25,
                is_new=(af_tot25==0),
                cat_rows=cat_rows, brd_rows=brd_rows,
            )

        return data

    def _tab4(self, af_list):
        """탭4: 카테고리 전년비 + 역행 제휴사"""
        flt26 = self.df26[(self.df26["당월인증"]=="Y") & (self.df26["정산구분"]=="판매")]
        flt25 = self.df25[(self.df25["당월인증"]=="Y") & (self.df25["정산구분"]=="판매")]
        tot26 = float(flt26["거래액_VAT제외"].sum())
        tot25 = float(flt25["거래액_VAT제외"].sum())

        cat26 = flt26.groupby("물리대카테")["거래액_VAT제외"].sum()
        cat25 = flt25.groupby("물리대카테")["거래액_VAT제외"].sum()
        all_cats = sorted(set(cat26.index) | set(cat25.index))

        cat_rows = []
        cat_yoy_map = {}  # 역행 판단용
        for cat in all_cats:
            r26 = float(cat26.get(cat, 0))
            r25 = float(cat25.get(cat, 0))
            w26 = round(r26/tot26*100,1) if tot26>0 else 0
            w25 = round(r25/tot25*100,1) if tot25>0 else 0
            yoy = _yoy(r26, r25)
            cat_yoy_map[cat] = yoy
            cat_rows.append(dict(
                cat=cat, rev_26=r26, rev_25=r25,
                yoy_pct=yoy, wt_26=w26, wt_25=w25, wt_pp=_pp(w26, w25),
            ))
        cat_rows.sort(key=lambda x: x["rev_26"], reverse=True)

        # 역행 제휴사 탐지
        reverse_cards = []
        for cat, total_yoy in cat_yoy_map.items():
            if total_yoy is None:
                continue
            card_afs = []
            for af in af_list:
                af26 = flt26[(flt26["물리대카테"]==cat) & (flt26["제휴사명"]==af)]
                af25 = flt25[(flt25["물리대카테"]==cat) & (flt25["제휴사명"]==af)]
                r26 = float(af26["거래액_VAT제외"].sum())
                r25 = float(af25["거래액_VAT제외"].sum())
                if r26 == 0 and r25 == 0:
                    continue
                af_yoy = _yoy(r26, r25)
                if af_yoy is None:
                    continue
                # 역행 조건
                is_reverse = (total_yoy > 0 and af_yoy < 0) or \
                             (total_yoy < 0 and af_yoy > 0)
                if not is_reverse:
                    continue

                # 원인 브랜드 추출 (해당 제휴사×카테 내 최대 변화 브랜드)
                brd26 = af26.groupby("Admin브랜드명")["거래액_VAT제외"].sum()
                brd25 = af25.groupby("Admin브랜드명")["거래액_VAT제외"].sum()
                all_brds = set(brd26.index) | set(brd25.index)
                brd_chg = []
                for b in all_brds:
                    d = float(brd26.get(b,0)) - float(brd25.get(b,0))
                    brd_chg.append((b, d, float(brd26.get(b,0)), float(brd25.get(b,0))))
                brd_chg.sort(key=lambda x: x[1])  # 가장 크게 감소한 순
                cause_brands = []
                for b, chg, r26b, r25b in brd_chg[:2]:
                    y = _yoy(r26b, r25b)
                    cause_brands.append(dict(
                        brand=b, chg=chg,
                        rev_26=r26b, rev_25=r25b,
                        yoy_pct=y,
                    ))

                card_afs.append(dict(
                    name=af, af_yoy=af_yoy,
                    rev_26=r26, rev_25=r25,
                    cause_brands=cause_brands,
                ))

            if card_afs:
                reverse_cards.append(dict(
                    cat=cat, total_yoy=total_yoy, affiliates=card_afs
                ))

        return dict(cat_rows=cat_rows, reverse_cards=reverse_cards)

    def _tab5(self, af_list):
        """탭5: 브랜드 상승/하락 TOP10 + 역행 브랜드"""
        flt26 = self.df26[(self.df26["당월인증"]=="Y") & (self.df26["정산구분"]=="판매")]
        flt25 = self.df25[(self.df25["당월인증"]=="Y") & (self.df25["정산구분"]=="판매")]
        tot26 = float(flt26["거래액_VAT제외"].sum())
        tot25 = float(flt25["거래액_VAT제외"].sum())

        brd26 = flt26.groupby("Admin브랜드명")["거래액_VAT제외"].sum()
        brd25 = flt25.groupby("Admin브랜드명")["거래액_VAT제외"].sum()

        # 전년 5M 이상 브랜드만
        eligible = {b for b, v in brd25.items() if v >= 5_000_000}
        all_brds = sorted(set(brd26.index) | set(brd25.index))

        brd_rows = []
        for b in all_brds:
            if b not in eligible:
                continue
            r26 = float(brd26.get(b, 0))
            r25 = float(brd25.get(b, 0))
            w26 = round(r26/tot26*100, 2) if tot26 > 0 else 0
            w25 = round(r25/tot25*100, 2) if tot25 > 0 else 0
            yoy = _yoy(r26, r25)
            brd_rows.append(dict(
                brand=b, rev_26=r26, rev_25=r25,
                yoy_pct=yoy, wt_26=w26, wt_25=w25, wt_pp=_pp(w26, w25),
            ))

        brd_rows.sort(key=lambda x: x["yoy_pct"] or -999, reverse=True)
        top10_up = brd_rows[:10]
        top10_dn = sorted(brd_rows, key=lambda x: x["yoy_pct"] or 999)[:10]

        # 역행 브랜드 (카테 기준)
        cat26 = flt26.groupby("물리대카테")["거래액_VAT제외"].sum()
        cat25 = flt25.groupby("물리대카테")["거래액_VAT제외"].sum()
        cat_yoy_map = {}
        for cat in set(cat26.index) | set(cat25.index):
            cat_yoy_map[cat] = _yoy(float(cat26.get(cat,0)), float(cat25.get(cat,0)))

        # 브랜드별 카테 매핑
        brd_cat_map = flt26.groupby("Admin브랜드명")["물리대카테"].agg(
            lambda x: x.value_counts().index[0]
        ).to_dict()
        for b in flt25["Admin브랜드명"].unique():
            if b not in brd_cat_map:
                s = flt25[flt25["Admin브랜드명"]==b]["물리대카테"]
                if len(s) > 0:
                    brd_cat_map[b] = s.value_counts().index[0]

        rev_brd_cards = {}
        for b in all_brds:
            r26 = float(brd26.get(b, 0))
            r25 = float(brd25.get(b, 0))
            if r25 < 1_000_000:  # 전년 1M 미만 제외
                continue
            cat = brd_cat_map.get(b)
            if cat is None:
                continue
            total_cat_yoy = cat_yoy_map.get(cat)
            if total_cat_yoy is None:
                continue
            brd_yoy = _yoy(r26, r25)
            if brd_yoy is None:
                continue
            is_reverse = (total_cat_yoy > 0 and brd_yoy < 0) or \
                         (total_cat_yoy < 0 and brd_yoy > 0)
            if not is_reverse:
                continue
            if cat not in rev_brd_cards:
                rev_brd_cards[cat] = dict(cat=cat, total_yoy=total_cat_yoy, brands=[])
            rev_brd_cards[cat]["brands"].append(dict(
                brand=b, yoy_pct=brd_yoy,
                rev_25=r25, rev_26=r26,
                is_small=(r25 < 5_000_000),
            ))

        return dict(
            top10_up=top10_up,
            top10_dn=top10_dn,
            reverse_cards=list(rev_brd_cards.values()),
        )

    def _tab6(self, af_list):
        """탭6: 몰전체 비교"""
        flt26 = self.df26[(self.df26["당월인증"]=="Y") & (self.df26["정산구분"]=="판매")]
        flt25 = self.df25[(self.df25["당월인증"]=="Y") & (self.df25["정산구분"]=="판매")]

        # 전체 KPI
        af_rev26 = float(flt26["거래액_VAT제외"].sum())
        af_rev25 = float(flt25["거래액_VAT제외"].sum())
        af_buy26 = int(flt26["고객번호"].nunique())
        af_buy25 = int(flt25["고객번호"].nunique())

        mall_rev26 = float(self.mall26["거래액"].sum()) if "거래액" in self.mall26.columns else 0
        mall_rev25 = float(self.mall25["거래액"].sum()) if "거래액" in self.mall25.columns else 0
        mall_cust26 = float(self.mall26["주문고객수"].sum()) if "주문고객수" in self.mall26.columns else 0
        mall_cust25 = float(self.mall25["주문고객수"].sum()) if "주문고객수" in self.mall25.columns else 0

        af_mall_pct26 = round(af_rev26/mall_rev26*100,2) if mall_rev26>0 else 0
        af_mall_pct25 = round(af_rev25/mall_rev25*100,2) if mall_rev25>0 else 0

        kpi = dict(
            mall_rev_26=mall_rev26, mall_rev_25=mall_rev25, mall_rev_yoy=_yoy(mall_rev26, mall_rev25),
            af_rev_26=af_rev26, af_rev_25=af_rev25, af_rev_yoy=_yoy(af_rev26, af_rev25),
            af_mall_pct_26=af_mall_pct26, af_mall_pct_25=af_mall_pct25,
            af_mall_pct_pp=_pp(af_mall_pct26, af_mall_pct25),
            mall_cust_26=mall_cust26, mall_cust_25=mall_cust25,
            af_buyers_26=af_buy26, af_buyers_25=af_buy25,
        )

        # 카테고리별 시그널
        cat_af26 = flt26.groupby("물리대카테")["거래액_VAT제외"].sum()
        cat_af25 = flt25.groupby("물리대카테")["거래액_VAT제외"].sum()

        mall_col_cat = "대카테고리명" if "대카테고리명" in self.mall26.columns else "대카테고리명"
        cat_mall26 = self.mall26.groupby(mall_col_cat)["거래액"].sum() if mall_col_cat in self.mall26.columns else pd.Series(dtype=float)
        cat_mall25 = self.mall25.groupby(mall_col_cat)["거래액"].sum() if mall_col_cat in self.mall25.columns else pd.Series(dtype=float)

        all_cats = sorted(set(cat_af26.index) | set(cat_af25.index) |
                         set(cat_mall26.index) | set(cat_mall25.index))

        def _signal(mall_yoy, af_yoy):
            if af_yoy is None: return "제휴없음"
            if mall_yoy is None: return "제휴만"
            if mall_yoy < 0 and af_yoy > 0: return "star"
            if mall_yoy > 0 and af_yoy < 0: return "warn"
            if mall_yoy > 0 and af_yoy > mall_yoy: return "over"
            if mall_yoy > 0 and af_yoy > 0: return "up"
            if mall_yoy < 0 and af_yoy < 0: return "dn"
            return "fl"

        cat_signal_rows = []
        for cat in all_cats:
            mr26 = float(cat_mall26.get(cat, 0))
            mr25 = float(cat_mall25.get(cat, 0))
            ar26 = float(cat_af26.get(cat, 0))
            ar25 = float(cat_af25.get(cat, 0))
            mall_yoy = _yoy(mr26, mr25)
            af_yoy   = _yoy(ar26, ar25) if (ar26>0 or ar25>0) else None
            cat_signal_rows.append(dict(
                cat=cat,
                mall_rev_26=mr26, mall_rev_25=mr25, mall_yoy=mall_yoy,
                af_rev_26=ar26, af_rev_25=ar25, af_yoy=af_yoy,
                signal=_signal(mall_yoy, af_yoy),
            ))
        cat_signal_rows.sort(key=lambda x: x["mall_rev_26"], reverse=True)

        # 브랜드 시그널
        brd_col = "ADMIN브랜드명" if "ADMIN브랜드명" in self.mall26.columns else "Admin브랜드명"
        brd_mall26 = self.mall26.groupby(brd_col)["거래액"].sum() if brd_col in self.mall26.columns else pd.Series(dtype=float)
        brd_mall25 = self.mall25.groupby(brd_col)["거래액"].sum() if brd_col in self.mall25.columns else pd.Series(dtype=float)
        brd_af26 = flt26.groupby("Admin브랜드명")["거래액_VAT제외"].sum()
        brd_af25 = flt25.groupby("Admin브랜드명")["거래액_VAT제외"].sum()

        # 전년·당년 몰 1M 이상 브랜드
        eligible_brds = {b for b, v in brd_mall26.items() if v >= 1_000_000} | \
                        {b for b, v in brd_mall25.items() if v >= 1_000_000}

        star_brds, warn_brds = [], []
        for b in eligible_brds:
            mr26 = float(brd_mall26.get(b,0))
            mr25 = float(brd_mall25.get(b,0))
            ar26 = float(brd_af26.get(b,0))
            ar25 = float(brd_af25.get(b,0))
            mall_yoy = _yoy(mr26, mr25)
            af_yoy   = _yoy(ar26, ar25)
            # 카테 매핑 (몰전체 기준)
            cat_m = self.mall26[self.mall26[brd_col]==b][mall_col_cat].iloc[0] \
                    if len(self.mall26[self.mall26[brd_col]==b]) > 0 else "-"
            item = dict(brand=b, cat=cat_m, mall_yoy=mall_yoy, af_yoy=af_yoy,
                        mall_rev_26=mr26, mall_rev_25=mr25, af_rev_26=ar26, af_rev_25=ar25)
            if mall_yoy is not None and af_yoy is not None:
                if mall_yoy < 0 and af_yoy > 0:
                    star_brds.append(item)
                elif mall_yoy > 0 and af_yoy < 0:
                    warn_brds.append(item)

        star_brds.sort(key=lambda x: x["af_yoy"] or 0, reverse=True)
        warn_brds.sort(key=lambda x: x["af_yoy"] or 0)

        return dict(
            kpi=kpi,
            cat_signal_rows=cat_signal_rows,
            brand_star=star_brds[:10],
            brand_warn=warn_brds[:10],
        )

    def _tab7(self):
        """탭7: 주차 분석"""
        # 분析 주차 결정
        max_date = self.df26["정산일시일"].max()
        max_date_str = max_date.strftime("%Y-%m-%d") if pd.notna(max_date) else None
        wk_cur = self.pivot_week.get(max_date_str)

        # 당주 날짜 범위
        wk_dates = {d for d, w in self.pivot_week.items() if w == wk_cur} if wk_cur else set()
        wk_dates_dt = sorted([datetime.strptime(d, "%Y-%m-%d") for d in wk_dates])

        # 전년 동주차 코드 (동월 동순번)
        wk_prev_year = None
        if wk_cur:
            parts = wk_cur.split("_")  # e.g. 26_6_2
            if len(parts) == 3:
                wk_prev_year = f"25_{parts[1]}_{parts[2]}"

        wy_dates = {d for d, w in self.pivot_week.items() if w == wk_prev_year} if wk_prev_year else set()

        # 전주 코드
        wk_prev = None
        if wk_cur:
            parts = wk_cur.split("_")
            if len(parts) == 3:
                n = int(parts[2])
                if n > 1:
                    wk_prev = f"{parts[0]}_{parts[1]}_{n-1}"
        wp_dates = {d for d, w in self.pivot_week.items() if w == wk_prev} if wk_prev else set()

        def _filter_wk(df, dates_set):
            date_dts = {datetime.strptime(d, "%Y-%m-%d").date() for d in dates_set if d}
            return df[df["정산일시일"].dt.date.isin(date_dts)]

        flt26_wk = _filter_wk(
            self.df26[(self.df26["당월인증"]=="Y") & (self.df26["정산구분"]=="판매")],
            wk_dates
        )
        flt25_wk = _filter_wk(
            self.df25[(self.df25["당월인증"]=="Y") & (self.df25["정산구분"]=="판매")],
            wy_dates
        )
        flt26_wp = _filter_wk(
            self.df26[(self.df26["당월인증"]=="Y") & (self.df26["정산구분"]=="판매")],
            wp_dates
        )

        def _wk_kpi(df):
            r = float(df["거래액_VAT제외"].sum())
            b = int(df["고객번호"].nunique())
            return dict(revenue=r, buyers=b)

        kpi_wk = _wk_kpi(flt26_wk)
        kpi_wy = _wk_kpi(flt25_wk)
        kpi_wp = _wk_kpi(flt26_wp)

        # 일별 추이
        daily = {}
        for _, row in flt26_wk.iterrows():
            d = row["정산일시일"].strftime("%Y-%m-%d")
            daily[d] = daily.get(d, 0) + float(row["거래액_VAT제외"])
        daily_list = [dict(date=d, rev=v, dow=datetime.strptime(d,"%Y-%m-%d").weekday())
                      for d, v in sorted(daily.items())]

        # 카테고리 편차
        tot26_wk = float(flt26_wk["거래액_VAT제외"].sum())
        mall_tot26 = float(self.mall26["거래액"].sum()) if "거래액" in self.mall26.columns else 0
        cat_af26_wk = flt26_wk.groupby("물리대카테")["거래액_VAT제외"].sum()
        cat_mall26 = self.mall26.groupby("대카테고리명")["거래액"].sum() \
                     if "대카테고리명" in self.mall26.columns else pd.Series(dtype=float)

        cat_af25_wk = flt25_wk.groupby("물리대카테")["거래액_VAT제외"].sum() if len(flt25_wk)>0 else pd.Series(dtype=float)
        tot25_wk = float(flt25_wk["거래액_VAT제외"].sum())
        mall_tot25 = float(self.mall25["거래액"].sum()) if "거래액" in self.mall25.columns else 0
        cat_mall25 = self.mall25.groupby("대카테고리명")["거래액"].sum() \
                     if "대카테고리명" in self.mall25.columns else pd.Series(dtype=float)

        all_cats = sorted(set(cat_af26_wk.index) | set(cat_af25_wk.index))
        cat_wk_rows = []
        for cat in all_cats:
            r26 = float(cat_af26_wk.get(cat, 0))
            r25 = float(cat_af25_wk.get(cat, 0))
            mw26 = float(cat_mall26.get(cat, 0))
            mw25 = float(cat_mall25.get(cat, 0))
            af_w26 = round(r26/tot26_wk*100,2) if tot26_wk>0 else 0
            mall_w26 = round(mw26/mall_tot26*100,2) if mall_tot26>0 else 0
            af_w25 = round(r25/tot25_wk*100,2) if tot25_wk>0 else 0
            mall_w25 = round(mw25/mall_tot25*100,2) if mall_tot25>0 else 0
            cat_wk_rows.append(dict(
                cat=cat, rev_26=r26, rev_25=r25, yoy_pct=_yoy(r26, r25),
                af_wt_26=af_w26, mall_wt_26=mall_w26, diff_26=round(af_w26-mall_w26,2),
                af_wt_25=af_w25, mall_wt_25=mall_w25, diff_25=round(af_w25-mall_w25,2),
            ))
        cat_wk_rows.sort(key=lambda x: x["rev_26"], reverse=True)

        # 브랜드 TOP20 편차
        brd_af26_wk = flt26_wk.groupby("Admin브랜드명")["거래액_VAT제외"].sum()
        brd_mall26 = self.mall26.groupby("ADMIN브랜드명")["거래액"].sum() \
                     if "ADMIN브랜드명" in self.mall26.columns else pd.Series(dtype=float)
        brd_af25_wk = flt25_wk.groupby("Admin브랜드명")["거래액_VAT제외"].sum() if len(flt25_wk)>0 else pd.Series(dtype=float)
        brd_mall25 = self.mall25.groupby("ADMIN브랜드명")["거래액"].sum() \
                     if "ADMIN브랜드명" in self.mall25.columns else pd.Series(dtype=float)

        top20_brds = brd_af26_wk.nlargest(20).index.tolist()
        brd_cat_map = flt26_wk.groupby("Admin브랜드명")["물리대카테"].agg(
            lambda x: x.value_counts().index[0] if len(x)>0 else "-"
        ).to_dict()

        brd_wk_rows = []
        for b in top20_brds:
            r26 = float(brd_af26_wk.get(b, 0))
            r25 = float(brd_af25_wk.get(b, 0))
            mw26 = float(brd_mall26.get(b, 0))
            mw25 = float(brd_mall25.get(b, 0))
            af_w26 = round(r26/tot26_wk*100,2) if tot26_wk>0 else 0
            mall_w26 = round(mw26/mall_tot26*100,2) if mall_tot26>0 else 0
            af_w25 = round(r25/tot25_wk*100,2) if tot25_wk>0 else 0
            mall_w25 = round(mw25/mall_tot25*100,2) if mall_tot25>0 else 0
            brd_wk_rows.append(dict(
                brand=b, cat=brd_cat_map.get(b, "-"),
                rev_26=r26, rev_25=r25, yoy_pct=_yoy(r26, r25),
                af_wt_26=af_w26, mall_wt_26=mall_w26, diff_26=round(af_w26-mall_w26,2),
                af_wt_25=af_w25, mall_wt_25=mall_w25, diff_25=round(af_w25-mall_w25,2),
            ))

        return dict(
            wk_cur=wk_cur, wk_prev_year=wk_prev_year, wk_prev=wk_prev,
            wk_day_count=len(wk_dates),
            kpi_cur=kpi_wk, kpi_prev_year=kpi_wy, kpi_prev=kpi_wp,
            daily_list=daily_list,
            cat_wk_rows=cat_wk_rows,
            brd_wk_rows=brd_wk_rows,
        )

    def _tab8(self, af_list):
        """탭8: 회원구분 분석"""
        flt26 = self.df26[(self.df26["당월인증"]=="Y") & (self.df26["정산구분"]=="판매")].copy()
        seg_col = "기존/win-back/신규"

        tot26 = float(flt26["거래액_VAT제외"].sum())

        # 전체 KPI by 구분
        seg_kpi = {}
        for seg in ["신규", "WIN-BACK", "기존"]:
            seg_key = {"신규":"신규","WIN-BACK":"win-back","기존":"기존"}[seg]
            # 대소문자 매칭
            flt_seg = flt26[flt26[seg_col].str.lower() == seg_key.lower()]
            r = float(flt_seg["거래액_VAT제외"].sum())
            b = int(flt_seg["고객번호"].nunique())
            # 인증수는 인증회원_26에서
            cert_col = self._cert26_af_col()
            c_seg_map = {"신규":"신규","WIN-BACK":"WIN-BACK","기존":"기존"}
            c = int(self.cert26[c_seg_map[seg]].sum()) if c_seg_map[seg] in self.cert26.columns else 0
            cr = round(b/c*100,2) if c>0 else 0
            apu = round(r/b,0) if b>0 else 0
            seg_kpi[seg] = dict(revenue=r, buyers=b, cert=c, cr=cr, arpu=apu,
                                 rev_pct=round(r/tot26*100,1) if tot26>0 else 0)

        # 카테고리별 회원구분 실적
        cat_rows = []
        cat26_tot = flt26.groupby("물리대카테")["거래액_VAT제외"].sum()
        all_cats = sorted(cat26_tot.index)

        for cat in all_cats:
            row = dict(cat=cat)
            cat_tot = float(cat26_tot.get(cat, 0))
            cat_tot_all_pct = round(cat_tot/tot26*100,1) if tot26>0 else 0
            flt_cat = flt26[flt26["물리대카테"]==cat]
            buy_cat = int(flt_cat["고객번호"].nunique())
            row["rev_total"] = cat_tot
            row["buyers_total"] = buy_cat
            row["wt_total"] = cat_tot_all_pct

            for seg in ["신규","WIN-BACK","기존"]:
                seg_key = {"신규":"신규","WIN-BACK":"win-back","기존":"기존"}[seg]
                flt_seg = flt_cat[flt_cat[seg_col].str.lower() == seg_key.lower()]
                r = float(flt_seg["거래액_VAT제외"].sum())
                seg_tot = seg_kpi[seg]["revenue"]
                wt = round(r/seg_tot*100,1) if seg_tot>0 else 0
                diff = round(wt - cat_tot_all_pct, 1)
                row[f"rev_{seg}"] = r
                row[f"wt_{seg}"] = wt
                row[f"diff_{seg}"] = diff
            cat_rows.append(row)
        cat_rows.sort(key=lambda x: x["rev_total"], reverse=True)

        # 브랜드 TOP15 회원구분
        brd26_tot = flt26.groupby("Admin브랜드명")["거래액_VAT제외"].sum()
        top15_brds = brd26_tot.nlargest(15).index.tolist()
        brd_cat_map = flt26.groupby("Admin브랜드명")["물리대카테"].agg(
            lambda x: x.value_counts().index[0] if len(x)>0 else "-"
        ).to_dict()

        brd_rows = []
        for b in top15_brds:
            brd_tot = float(brd26_tot.get(b, 0))
            brd_tot_pct = round(brd_tot/tot26*100,1) if tot26>0 else 0
            flt_brd = flt26[flt26["Admin브랜드명"]==b]
            buy_brd = int(flt_brd["고객번호"].nunique())
            row = dict(brand=b, cat=brd_cat_map.get(b,"-"),
                       rev_total=brd_tot, buyers_total=buy_brd, wt_total=brd_tot_pct)
            for seg in ["신규","WIN-BACK","기존"]:
                seg_key = {"신규":"신규","WIN-BACK":"win-back","기존":"기존"}[seg]
                flt_seg = flt_brd[flt_brd[seg_col].str.lower() == seg_key.lower()]
                r = float(flt_seg["거래액_VAT제외"].sum())
                seg_tot = seg_kpi[seg]["revenue"]
                wt = round(r/seg_tot*100,1) if seg_tot>0 else 0
                diff = round(wt - brd_tot_pct, 1)
                row[f"rev_{seg}"] = r
                row[f"wt_{seg}"] = wt
                row[f"diff_{seg}"] = diff
            brd_rows.append(row)

        return dict(seg_kpi=seg_kpi, cat_rows=cat_rows, brd_rows=brd_rows)

    def _tab9(self):
        """탭9: 첫구매 분석 (당월인증 YN 무관, 판매, VAT제외)"""
        flt26 = self.df26[
            (self.df26["첫구매주문건여부"] == "Y") &
            (self.df26["정산구분"] == "판매")
        ].copy()
        flt25 = self.df25[
            (self.df25["첫구매주문건여부"] == "Y") &
            (self.df25["정산구분"] == "판매")
        ].copy() if "첫구매주문건여부" in self.df25.columns else pd.DataFrame()

        # 제휴 전체 (당월인증 YN무관, 판매, VAT제외) - 분모용
        af_all26 = self.df26[self.df26["정산구분"]=="판매"]["거래액_VAT제외"].sum()
        mall_rev26 = float(self.mall26["거래액"].sum()) if "거래액" in self.mall26.columns else 0

        # KPI
        fp_rev26 = float(flt26["거래액_VAT제외"].sum())
        fp_cnt26 = int(flt26["주문번호"].nunique()) if "주문번호" in flt26.columns else 0
        fp_buy26 = int(flt26["고객번호"].nunique())
        fp_apu26 = round(fp_rev26/fp_buy26,0) if fp_buy26>0 else 0
        fp_rev25 = float(flt25["거래액_VAT제외"].sum()) if len(flt25)>0 else 0
        fp_buy25 = int(flt25["고객번호"].nunique()) if len(flt25)>0 else 0

        fp_pct_af = round(fp_rev26/float(af_all26)*100,1) if af_all26>0 else 0
        fp_pct_mall = round(fp_rev26/mall_rev26*100,1) if mall_rev26>0 else 0

        kpi = dict(
            fp_rev_26=fp_rev26, fp_rev_25=fp_rev25, fp_rev_yoy=_yoy(fp_rev26, fp_rev25),
            fp_cnt_26=fp_cnt26, fp_buyers_26=fp_buy26, fp_buyers_25=fp_buy25,
            fp_arpu_26=fp_apu26,
            fp_pct_af=fp_pct_af, fp_pct_mall=fp_pct_mall,
        )

        # ① 제휴 전체 거래액 by 카테 (당월인증 YN 무관, 판매)
        af_cat_all26 = self.df26[self.df26["정산구분"]=="판매"].groupby("물리대카테")["거래액_VAT제외"].sum()
        mall_cat26 = self.mall26.groupby("대카테고리명")["거래액"].sum() \
                     if "대카테고리명" in self.mall26.columns else pd.Series(dtype=float)

        cat26 = flt26.groupby("물리대카테")["거래액_VAT제외"].sum()
        cat25 = flt25.groupby("물리대카테")["거래액_VAT제외"].sum() if len(flt25)>0 else pd.Series(dtype=float)
        all_cats = sorted(cat26.index)

        cat_rows = []
        for cat in all_cats:
            r26 = float(cat26.get(cat, 0))
            r25 = float(cat25.get(cat, 0)) if len(flt25)>0 else 0
            # ① 첫구매내 비중 (분모=첫구매 전체 거래액)
            w1 = round(r26/fp_rev26*100,1) if fp_rev26>0 else 0
            # ② 카테내 첫구매 비중 (분모=제휴채널 카테 전체 거래액)
            cat_all = float(af_cat_all26.get(cat, 0))
            w2 = round(r26/cat_all*100,1) if cat_all>0 else 0
            # ③ 카테 전체비중 (분모=제휴채널 전체 거래액)
            w3 = round(cat_all/float(af_all26)*100,1) if af_all26>0 else 0
            # ④ 몰전체 대비 제휴 첫구매 비중
            cat_mall = float(mall_cat26.get(cat, 0))
            w4 = round(r26/cat_mall*100,1) if cat_mall>0 else 0
            cat_rows.append(dict(
                cat=cat, rev_26=r26, rev_25=r25,
                w1_fp_in_pct=w1,
                w2_fp_in_cat_pct=w2, w2_star=(w2>=15),
                w3_cat_in_af_pct=w3,
                w4_fp_vs_mall_pct=w4,
            ))
        cat_rows.sort(key=lambda x: x["rev_26"], reverse=True)

        # 브랜드 TOP15
        af_brd_all26 = self.df26[self.df26["정산구분"]=="판매"].groupby("Admin브랜드명")["거래액_VAT제외"].sum()
        brd26 = flt26.groupby("Admin브랜드명")["거래액_VAT제외"].sum()
        top15 = brd26.nlargest(15).index.tolist()
        brd_cat_map = flt26.groupby("Admin브랜드명")["물리대카테"].agg(
            lambda x: x.value_counts().index[0] if len(x)>0 else "-"
        ).to_dict()

        brd_rows = []
        for b in top15:
            r26 = float(brd26.get(b, 0))
            w1 = round(r26/fp_rev26*100,1) if fp_rev26>0 else 0
            brd_all = float(af_brd_all26.get(b,0))
            w2 = round(r26/brd_all*100,1) if brd_all>0 else 0
            brd_rows.append(dict(
                brand=b, cat=brd_cat_map.get(b,"-"),
                rev_26=r26, w1_fp_in_pct=w1,
                w2_fp_in_brd_pct=w2, w2_star=(w2>=20),
            ))

        return dict(kpi=kpi, cat_rows=cat_rows, brd_rows=brd_rows)

    def _quality_check(self):
        """데이터 품질 체크 (운영가이드 §6)"""
        qc = {}

        # 1. 인증회원 합계 일치
        try:
            c = self.cert26
            col_map = {"기존":"기존","WIN-BACK":"WIN-BACK","신규":"신규","총합계":"총합계"}
            avail = [v for v in col_map.values() if v in c.columns]
            if "총합계" in c.columns and all(k in c.columns for k in ["기존","WIN-BACK","신규"]):
                diff = ((c["기존"]+c["WIN-BACK"]+c["신규"]) - c["총합계"]).abs().max()
                ok = diff == 0
                qc["인증회원_합계검증"] = dict(ok=ok, msg=f"최대 차이={diff}" if not ok else "OK")
            else:
                qc["인증회원_합계검증"] = dict(ok=True, msg="컬럼 확인 불가 (스킵)")
        except Exception as e:
            qc["인증회원_합계검증"] = dict(ok=False, msg=str(e))

        # 2. VAT 역산 체크
        try:
            s = self.df26[(self.df26["당월인증"]=="Y") & (self.df26["정산구분"]=="판매")]
            vat_ratio = (s["거래액_VAT제외"] / s["거래액"]).median()
            ok = 0.88 <= vat_ratio <= 0.94
            qc["VAT_역산_체크"] = dict(ok=ok, msg=f"중앙값 비율={vat_ratio:.3f} (정상범위 0.88~0.94)")
        except Exception as e:
            qc["VAT_역산_체크"] = dict(ok=False, msg=str(e))

        # 3. 첫구매 비율
        try:
            total = len(self.df26[self.df26["정산구분"]=="판매"])
            fp = len(self.df26[(self.df26["정산구분"]=="판매") & (self.df26["첫구매주문건여부"]=="Y")])
            pct = fp/total*100 if total>0 else 0
            ok = 3 <= pct <= 20
            qc["첫구매_비율"] = dict(ok=ok, msg=f"{pct:.1f}% (정상범위 3~20%)")
        except Exception as e:
            qc["첫구매_비율"] = dict(ok=False, msg=str(e))

        # 4. SSNGCD03 UV 스파이크
        try:
            if "AF코드" in self.uv26.columns:
                ssng = self.uv26[self.uv26["AF코드"]==self.SSNG_EXCLUDE]["★UV"].sum()
                others = self.uv26[self.uv26["AF코드"]!=self.SSNG_EXCLUDE]["★UV"].mean()
                ratio = ssng / others if others > 0 else 0
                ok = ratio < 10
                qc["SSNGCD03_스파이크"] = dict(ok=ok,
                    msg=f"SSNGCD03 UV={int(ssng):,} / 평균AF UV={int(others):,} / 배율={ratio:.1f}x" +
                        ("  ⚠️ 제외 처리됨" if not ok else ""))
            else:
                qc["SSNGCD03_스파이크"] = dict(ok=True, msg="AF코드 컬럼 없음 (스킵)")
        except Exception as e:
            qc["SSNGCD03_스파이크"] = dict(ok=False, msg=str(e))

        # 5. 몰전체 연월 확인
        try:
            yr_months = self.mall26["결제_연월(YYYYMM)"].unique().tolist() if "결제_연월(YYYYMM)" in self.mall26.columns else []
            ok = len(yr_months) <= 1
            qc["몰전체_연월_확인"] = dict(ok=ok,
                msg=f"확인된 연월: {yr_months}" + ("" if ok else "  ⚠️ 복수 연월 — 필터 확인 필요"))
        except Exception as e:
            qc["몰전체_연월_확인"] = dict(ok=False, msg=str(e))

        # 6. MTD 데이터 존재 확인
        try:
            max26 = self.df26["정산일시일"].max()
            max25 = self.df25["정산일시일"].max()
            ok = pd.notna(max26) and pd.notna(max25)
            qc["MTD_데이터_존재"] = dict(ok=ok,
                msg=f"당년 최대={max26.date() if pd.notna(max26) else 'None'} / "
                    f"전년 최대={max25.date() if pd.notna(max25) else 'None'}")
        except Exception as e:
            qc["MTD_데이터_존재"] = dict(ok=False, msg=str(e))

        return qc

    # ─────────────────────────────────────────────────────────
    # 메인 실행
    # ─────────────────────────────────────────────────────────
    def run(self):
        # 1. 데이터 로딩
        self._load_all()

        # 2. 제휴사 목록 결정
        af_list = self._get_affiliate_list()
        # #N/A, 수식 오류 제거
        af_list = [a for a in af_list if a and str(a) not in ("#N/A", "nan", "", "None")]

        # 3. 품질 체크
        qc = self._quality_check()

        # 4. 탭별 집계
        t1 = self._tab1(af_list)
        t2 = self._tab2(af_list)
        t3 = self._tab3(af_list)
        t4 = self._tab4(af_list)
        t5 = self._tab5(af_list)
        t6 = self._tab6(af_list)
        t7 = self._tab7()
        t8 = self._tab8(af_list)
        t9 = self._tab9()

        return dict(
            meta=dict(
                year_cur=int(self.mtd_end.year),
                year_prev=int(self.mtd_end.year - 1),
                mtd_start_26=self.mtd_start_26.strftime("%Y-%m-%d"),
                mtd_end_26=self.mtd_end.strftime("%Y-%m-%d"),
                mtd_start_25=self.mtd_start_25.strftime("%Y-%m-%d"),
                mtd_end_25=self.mtd_end_25.strftime("%Y-%m-%d"),
                exclude_ssng=self.exclude_ssng,
                affiliate_count=len(af_list),
                affiliate_list=af_list,
                quality_check=qc,
            ),
            tab1_overview=t1,
            tab2_decomp=t2,
            tab3_affiliate=t3,
            tab4_category=t4,
            tab5_brand=t5,
            tab6_mall=t6,
            tab7_weekly=t7,
            tab8_segment=t8,
            tab9_first=t9,
        )
