"""tabs/utils.py — 공통 헬퍼"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd


# ── 색상 팔레트 ──
C = dict(
    primary="rgba(79,70,229,0.75)",
    primary_l="rgba(79,70,229,0.25)",
    green="rgba(16,185,129,0.70)",
    red="rgba(239,68,68,0.75)",
    amber="#f59e0b",
    gray="#9ca3af",
    pos_dark="rgba(79,70,229,0.85)",
    pos_lite="rgba(79,70,229,0.25)",
    neg_dark="rgba(239,68,68,0.85)",
    neg_lite="rgba(239,68,68,0.25)",
)


def fmt_M(v, d=1):
    if v is None: return "-"
    return f"{v/1e6:.{d}f}M"

def fmt_pct(v, d=1):
    if v is None: return "-"
    return f"{v:.{d}f}%"

def fmt_pp(v, d=1):
    if v is None: return "-"
    return f"{v:+.{d}f}%p"

def fmt_yoy(v):
    if v is None: return "-"
    sign = "▲" if v > 0 else "▼"
    color = "#16a34a" if v > 0 else "#dc2626"
    return f'<span style="color:{color};font-weight:600">{sign}{abs(v):.1f}%</span>'

def fmt_n(v):
    if v is None: return "-"
    return f"{int(v):,}"


def kpi_card(label, val, prev=None, yoy=None, unit=""):
    """KPI 카드 HTML"""
    yoy_html = ""
    if yoy is not None:
        color = "#16a34a" if yoy >= 0 else "#dc2626"
        sign = "▲" if yoy >= 0 else "▼"
        yoy_html = f'<div class="yoy"><span style="color:{color};font-weight:600">{sign}{abs(yoy):.1f}%</span>'
        if prev is not None:
            yoy_html += f' <span style="color:#9ca3af">(전년 {prev})</span>'
        yoy_html += '</div>'
    return f"""
    <div class="kcard">
      <div class="label">{label}</div>
      <div class="val">{val}{unit}</div>
      {yoy_html}
    </div>
    """


def section(title):
    st.markdown(f'<div class="stitle">{title}</div>', unsafe_allow_html=True)


def info_box(text):
    st.markdown(f'<div class="info-box">💡 {text}</div>', unsafe_allow_html=True)


def warn_box(text):
    st.markdown(f'<div class="warn-box">⚠️ {text}</div>', unsafe_allow_html=True)


def bar_line_chart(labels, bar_vals, line_vals,
                   bar_name="2026", line_name="2025",
                   bar_color=None, line_color=None,
                   y_title="거래액(M)", height=320):
    """bar(당년) + line(전년) 복합 차트"""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=[v/1e6 if v else 0 for v in bar_vals],
        name=bar_name,
        marker_color=bar_color or C["primary"],
    ))
    fig.add_trace(go.Scatter(
        x=labels, y=[v/1e6 if v else 0 for v in line_vals],
        name=line_name, mode="lines+markers",
        line=dict(color=line_color or C["gray"], width=2, dash="dot"),
    ))
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", y=1.12),
        yaxis_title=y_title,
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#e5e7eb")
    return fig


def grouped_bar(labels, series_dict, height=340):
    """복수 계열 grouped bar"""
    fig = go.Figure()
    colors = [C["primary"], C["green"], C["amber"], C["red"]]
    for i, (name, vals) in enumerate(series_dict.items()):
        fig.add_trace(go.Bar(
            name=name, x=labels,
            y=vals, marker_color=colors[i % len(colors)],
        ))
    fig.update_layout(
        barmode="group", height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", y=1.12),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    fig.update_yaxes(gridcolor="#e5e7eb")
    return fig


def diff_bar(labels, vals_cur, vals_prev=None, height=400, threshold=0):
    """편차 가로 bar (양수=파랑, 음수=빨강)"""
    fig = go.Figure()
    colors_cur = [C["pos_dark"] if v >= threshold else C["neg_dark"] for v in vals_cur]
    fig.add_trace(go.Bar(
        y=labels, x=vals_cur, orientation="h",
        name="당년 편차", marker_color=colors_cur,
    ))
    if vals_prev:
        colors_prev = [C["pos_lite"] if v >= threshold else C["neg_lite"] for v in vals_prev]
        fig.add_trace(go.Bar(
            y=labels, x=vals_prev, orientation="h",
            name="전년 편차", marker_color=colors_prev,
        ))
    fig.add_vline(x=0, line_color="#374151", line_width=1.5)
    fig.update_layout(
        barmode="group", height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", y=1.06),
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis_title="%p",
    )
    return fig


def yoy_badge(v, is_new=False):
    if is_new:
        return '<span class="badge-new">신규</span>'
    if v is None:
        return "-"
    if v >= 0:
        return f'<span class="badge-up">▲{abs(v):.1f}%</span>'
    return f'<span class="badge-dn">▼{abs(v):.1f}%</span>'


def sig_badge(sig):
    MAP = {
        "star": ('<span style="background:#dbeafe;color:#1e40af;padding:2px 6px;border-radius:3px;font-size:.72rem">★몰↓제휴↑</span>', ""),
        "warn": ('<span style="background:#fff3cd;color:#92400e;padding:2px 6px;border-radius:3px;font-size:.72rem">⚠몰↑제휴↓</span>', ""),
        "over": ('<span style="background:#dcfce7;color:#166534;padding:2px 6px;border-radius:3px;font-size:.72rem">제휴초과↑</span>', ""),
        "up":   ('<span style="background:#e5e7eb;color:#374151;padding:2px 6px;border-radius:3px;font-size:.72rem">동반↑</span>', ""),
        "dn":   ('<span style="background:#fee2e2;color:#991b1b;padding:2px 6px;border-radius:3px;font-size:.72rem">동반↓</span>', ""),
        "fl":   ('<span style="background:#f3f4f6;color:#6b7280;padding:2px 6px;border-radius:3px;font-size:.72rem">보합</span>', ""),
        "제휴없음": ('<span style="background:#f3f4f6;color:#9ca3af;padding:2px 6px;border-radius:3px;font-size:.72rem">제휴없음</span>', ""),
    }
    return MAP.get(sig, (sig, ""))[0]
