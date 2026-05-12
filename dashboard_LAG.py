import ast

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ARL_data_cleaning import ArlModel

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="LAG Report Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------------------
st.markdown(
    "<style>"
    "[data-testid='stAppViewContainer']{background:#f4f6fb;}"
    "[data-testid='stSidebar']{background:#0f2040;}"
    "[data-testid='stSidebar'] *{color:#c8d6f0 !important;}"
    ".block-container{padding:1.8rem 2.4rem 3rem;max-width:1400px;}"
    "#MainMenu{visibility:hidden;}"
    "footer{visibility:hidden;}"
    "h1,h2,h3{font-family:'Segoe UI',sans-serif;}"
    "</style>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
BLUE   = "#2E6FDB"
GREEN  = "#1A9E6A"
RED    = "#D94F4F"
AMBER  = "#E0963A"
PURPLE = "#7E57C2"
NAVY   = "#0f2040"
GREY   = "#64748b"

CHART_BLUE   = "#3a7fdb"
CHART_RED    = "#d94f4f"
CHART_ORANGE = "#f0883e"
CHART_AMBER  = "#f0bf3e"
CHART_GREEN  = "#1a9e6a"

# Visits that are still open / data-being-collected for the 2026 Intervention cohort
ONGOING_VISITS_2026 = {"2 Months", "3 Months", "4 Months", "5 Months", "6 Months"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_ids(df, id_col="infant_id"):
    if df is not None and id_col in df.columns:
        return set(df[id_col].dropna().astype(str).unique())
    return set()


def filter_df_by_ids(df, ids, id_col="infant_id"):
    if df is None or df.empty or not ids:
        return df
    return df[df[id_col].astype(str).isin(ids)]


def summarize_withdrawal_reasons_layperson(df, reason_col="wd_reason",
                                           other_col="wd_reason_other",
                                           other_specific_col="wd_oth_spc"):
    reason_map = {
        "1": "there are too many visits",
        "2": "they were unable to get to the health center",
        "3": "it was too expensive to get to the health center",
        "4": "the mother died",
        "5": "the child died",
        "6": "they preferred not to say",
        "77": "Other",
    }
    reasons_expanded = []
    if reason_col in df.columns:
        for _, row in df.iterrows():
            raw = row[reason_col]
            if pd.isna(raw):
                continue
            if isinstance(raw, str):
                try:
                    parsed = ast.literal_eval(raw)
                    if not isinstance(parsed, list):
                        parsed = [str(parsed)]
                except Exception:
                    parsed = [s.strip() for s in raw.split(",")]
            else:
                parsed = list(raw) if isinstance(raw, (list, set)) else [str(raw)]
            for code in parsed:
                code = str(code).strip()
                if code == "77":
                    other_text = ""
                    if other_specific_col in df.columns and pd.notna(row.get(other_specific_col)):
                        other_text = str(row[other_specific_col])
                    elif other_col in df.columns and pd.notna(row.get(other_col)):
                        other_text = str(row[other_col])
                    reasons_expanded.append(
                        f"other reason: {other_text}" if other_text else "other reason (not specified)"
                    )
                elif code in reason_map:
                    reasons_expanded.append(reason_map[code])
    if not reasons_expanded:
        return []
    summary = pd.Series(reasons_expanded).value_counts().reset_index()
    summary.columns = ["Reason", "Count"]
    return [f"{r['Count']} person(s) withdrew because {r['Reason']}." for _, r in summary.iterrows()]


def style_chart(fig, title="", height=380):
    fig.update_layout(
        paper_bgcolor="white", plot_bgcolor="white", height=height,
        margin=dict(l=36, r=36, t=56, b=36),
        title=dict(text=f"<b>{title}</b>" if title else "", x=0.5,
                   font=dict(size=14, color=NAVY)),
        font=dict(family="Segoe UI, Arial, sans-serif", size=12, color="#333"),
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5,
                    bgcolor="rgba(255,255,255,0.85)", bordercolor="#e0e6f0", borderwidth=1),
    )
    fig.update_xaxes(showgrid=False, linecolor="#e0e6f0", linewidth=1,
                     tickfont=dict(size=11), title_font=dict(size=12, color=GREY))
    fig.update_yaxes(gridcolor="#f0f4fa", linecolor="#e0e6f0",
                     tickfont=dict(size=11), title_font=dict(size=12, color=GREY))
    return fig


def metric_card(label, value, color=BLUE, icon=""):
    """Return a compact single-string HTML card (no embedded newlines that confuse st.markdown)."""
    return (
        f'<div style="background:#fff;border-radius:12px;padding:18px 20px;border:1px solid #e4eaf5;'
        f'box-shadow:0 2px 8px rgba(30,50,100,0.07);display:flex;align-items:center;gap:14px;">'
        f'<div style="width:44px;height:44px;border-radius:10px;background:{color}18;'
        f'display:flex;align-items:center;justify-content:center;font-size:1.4rem;flex:0 0 44px;">{icon}</div>'
        f'<div><div style="font-size:0.72rem;color:{GREY};font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.06em;margin-bottom:3px;">{label}</div>'
        f'<div style="font-size:1.55rem;font-weight:800;color:{color};line-height:1.1;">{value}</div>'
        f'</div></div>'
    )


def section_header(title, color=BLUE, icon=""):
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;margin:2rem 0 0.8rem;'
        f'padding-bottom:8px;border-bottom:2px solid {color}30;">'
        f'<span style="font-size:1.3rem;">{icon}</span>'
        f'<h3 style="margin:0;color:{NAVY};font-size:1.05rem;font-weight:700;'
        f'letter-spacing:-0.01em;">{title}</h3></div>',
        unsafe_allow_html=True,
    )


def insight_box(text, color=BLUE):
    st.markdown(
        f'<div style="background:{color}0d;border-left:4px solid {color};border-radius:0 8px 8px 0;'
        f'padding:10px 14px;font-size:0.85rem;color:#334;margin-top:6px;line-height:1.6;">{text}</div>',
        unsafe_allow_html=True,
    )


def ongoing_banner(visits_list, year):
    pills = "".join(
        f'<span style="background:#fff3cd;border:1px solid #ffc107;color:#7c5600;'
        f'border-radius:20px;padding:3px 11px;font-size:0.78rem;font-weight:600;">&#9203; {v}</span>'
        for v in visits_list
    )
    st.markdown(
        f'<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:10px;'
        f'padding:13px 16px;margin-bottom:4px;display:flex;align-items:flex-start;gap:12px;">'
        f'<span style="font-size:1.3rem;flex:none;">&#128276;</span>'
        f'<div><div style="font-weight:700;color:#92400e;font-size:0.9rem;margin-bottom:6px;">'
        f'Intervention arm ({year}) — follow-up visits still in progress</div>'
        f'<div style="display:flex;flex-wrap:wrap;gap:6px;">{pills}</div>'
        f'<div style="font-size:0.8rem;color:#a16207;margin-top:7px;line-height:1.5;">'
        f'Charts show <strong>Pending</strong> (amber) for these '
        f'visits — data collection is still ongoing.</div></div></div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Data loading (cached)
# ---------------------------------------------------------------------------
@st.cache_data
def load_data():
    arl = ArlModel()
    return arl.get_data()

df_all = load_data()
st.write(df_all.head())
st.write(df_all.columns)
st.write(type(df_all))

_baseline_raw = df_all[df_all["redcap_event_name"] == "baseline_arm_1"].copy()
_day14_raw    = df_all[df_all["redcap_event_name"] == "day_14_arm_1"].copy()
_month1_raw   = df_all[df_all["redcap_event_name"] == "1st_month_arm_1"].copy()
_month2_raw   = df_all[df_all["redcap_event_name"] == "2nd_month_arm_1"].copy()
_month3_raw   = df_all[df_all["redcap_event_name"] == "3rd_month_arm_1"].copy()
_month4_raw   = df_all[df_all["redcap_event_name"] == "4th_month_arm_1"].copy()
_month5_raw   = df_all[df_all["redcap_event_name"] == "5th_month_arm_1"].copy()
_month6_raw   = df_all[df_all["redcap_event_name"] == "6th_month_arm_1"].copy()
_withd_raw    = df_all[df_all["redcap_event_name"] == "withdrawal_arm_1"].copy()

_enrol_col_exists = "enrollment_date" in _baseline_raw.columns
_enrol_years = []
if _enrol_col_exists:
    _enrol_years = sorted(
        pd.to_datetime(_baseline_raw["enrollment_date"], errors="coerce")
        .dt.year.dropna().astype(int).unique().tolist()
    )

YEAR_OPTIONS = ["All"] + [str(y) for y in _enrol_years]

# Map year → arm label
ARM_LABELS = {"2025": "Control", "2026": "Intervention"}

# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        '<div style="padding:8px 0 18px;">'
        '<div style="font-size:1.1rem;font-weight:800;color:#fff;letter-spacing:-0.02em;">LAG Report</div>'
        '<div style="font-size:0.72rem;color:#8fb0d8;margin-top:2px;">Participant Tracking Dashboard</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div style="font-size:0.68rem;color:#8fb0d8;text-transform:uppercase;'
        'letter-spacing:0.08em;margin-bottom:8px;font-weight:600;">Filter by Enrolment Year</div>',
        unsafe_allow_html=True,
    )

    selected_year = st.radio(
        label="year_filter",
        options=YEAR_OPTIONS,
        index=0,
        horizontal=True,
        label_visibility="collapsed",
    )

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    is_2026    = selected_year == "2026"
    is_2025    = selected_year == "2025"
    arm_label  = ARM_LABELS.get(selected_year, "All Arms")
    year_label = "All Years" if selected_year == "All" else f"{selected_year} — {arm_label}"

    badge_color  = "#4ade80" if selected_year == "All" else ("#f0a843" if is_2026 else "#60a5fa")
    status_extra = " · Follow-ups ongoing" if is_2026 else (" · All complete" if is_2025 else "")

    st.markdown(
        f'<div style="background:rgba(255,255,255,0.06);border-radius:8px;padding:8px 12px;'
        f'margin-bottom:4px;display:flex;align-items:center;gap:8px;">'
        f'<div style="width:8px;height:8px;border-radius:50%;background:{badge_color};flex:none;"></div>'
        f'<span style="font-size:0.78rem;color:#c8d6f0;">'
        f'<strong style="color:#fff;">{year_label}</strong>'
        f'<span style="opacity:0.7;">{status_extra}</span></span></div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    sidebar_stats_placeholder = st.empty()
    st.markdown("---")

    st.markdown(
        '<div style="font-size:0.68rem;color:#8fb0d8;text-transform:uppercase;'
        'letter-spacing:0.07em;margin-bottom:8px;">Sections</div>',
        unsafe_allow_html=True,
    )
    for s in [
        "Recruitment & Withdrawals",
        "Recruitment Timeline",
        "Follow-up Attendance",
        "Missed Visit Rates",
        "Attendance Trends",
        "Participant Flow & Retention",
        "Key Takeaways",
    ]:
        st.markdown(
            f'<div style="font-size:0.82rem;padding:5px 6px;border-radius:5px;'
            f'color:#c8d6f0;margin-bottom:2px;">· {s}</div>',
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# Apply year filter
# ---------------------------------------------------------------------------
if selected_year == "All" or not _enrol_col_exists:
    baseline = _baseline_raw.copy()
else:
    yr = int(selected_year)
    _enrol_dates = pd.to_datetime(_baseline_raw["enrollment_date"], errors="coerce")
    baseline = _baseline_raw[_enrol_dates.dt.year == yr].copy()

year_ids = safe_ids(baseline)

day14  = filter_df_by_ids(_day14_raw,  year_ids)
month1 = filter_df_by_ids(_month1_raw, year_ids)
month2 = filter_df_by_ids(_month2_raw, year_ids)
month3 = filter_df_by_ids(_month3_raw, year_ids)
month4 = filter_df_by_ids(_month4_raw, year_ids)
month5 = filter_df_by_ids(_month5_raw, year_ids)
month6 = filter_df_by_ids(_month6_raw, year_ids)
withd  = filter_df_by_ids(_withd_raw,  year_ids)

# ── Core metrics ──
baseline_ids      = safe_ids(baseline)
withdrawn_ids     = safe_ids(withd)
active_ids        = baseline_ids - withdrawn_ids
n_recruited       = len(baseline_ids)
retention         = len(active_ids)
withdrawals_count = len(withdrawn_ids)
retention_pct     = (retention / n_recruited * 100) if n_recruited > 0 else 0

# ── Ongoing visits (only active for Intervention / 2026) ──
ongoing_visits = ONGOING_VISITS_2026 if is_2026 else set()

# ── Build visit attendance table ──
visits = [
    ("Baseline", baseline),
    ("Day 14",   day14),
    ("1 Month",  month1),
    ("2 Months", month2),
    ("3 Months", month3),
    ("4 Months", month4),
    ("5 Months", month5),
    ("6 Months", month6),
]
attendance       = {lbl: safe_ids(dfv) for lbl, dfv in visits}
completed_counts = {lbl: len(attendance[lbl]) for lbl in attendance}

rows = []
for lbl in attendance:
    is_ongoing = lbl in ongoing_visits
    attended   = completed_counts[lbl]
    if lbl == "Baseline":
        missed = pending = 0
    elif is_ongoing:
        pending = max(0, len(active_ids) - attended)
        missed  = 0
    else:
        pending = 0
        missed  = max(0, len(active_ids) - attended)
    rows.append({"Visit": lbl, "Completed": attended,
                 "Missed": missed, "Pending": pending, "Ongoing": is_ongoing})

follow_df = pd.DataFrame(rows)
visit_order = list(follow_df["Visit"])

# Worst missed visit (completed timepoints only)
complete_only = follow_df[~follow_df["Ongoing"]]
if not complete_only.empty and complete_only["Missed"].max() > 0:
    max_row            = complete_only.loc[complete_only["Missed"].idxmax()]
    missed_visit_label = max_row["Visit"]
    missed_visit_count = int(max_row["Missed"])
else:
    missed_visit_label = "N/A"
    missed_visit_count = 0

withdraw_explanations = summarize_withdrawal_reasons_layperson(withd)

# ── Sidebar stats ──
ongoing_count = len(ongoing_visits)
extra_stat = (
    f'<div style="background:rgba(240,191,62,0.15);border-radius:8px;padding:12px 14px;">'
    f'<div style="font-size:0.67rem;color:#8fb0d8;text-transform:uppercase;letter-spacing:0.07em;">Ongoing Visits</div>'
    f'<div style="font-size:1.6rem;font-weight:800;color:#f0bf3e;">{ongoing_count}</div></div>'
) if is_2026 else ""

sidebar_stats_placeholder.markdown(
    f'<div style="display:flex;flex-direction:column;gap:10px;padding:4px 0;">'
    f'<div style="background:rgba(255,255,255,0.08);border-radius:8px;padding:12px 14px;">'
    f'<div style="font-size:0.67rem;color:#8fb0d8;text-transform:uppercase;letter-spacing:0.07em;">Total Recruited</div>'
    f'<div style="font-size:1.6rem;font-weight:800;color:#fff;">{n_recruited}</div></div>'
    f'<div style="background:rgba(26,158,106,0.18);border-radius:8px;padding:12px 14px;">'
    f'<div style="font-size:0.67rem;color:#8fb0d8;text-transform:uppercase;letter-spacing:0.07em;">Still Active</div>'
    f'<div style="font-size:1.6rem;font-weight:800;color:#4ade80;">{retention}</div></div>'
    f'<div style="background:rgba(217,79,79,0.18);border-radius:8px;padding:12px 14px;">'
    f'<div style="font-size:0.67rem;color:#8fb0d8;text-transform:uppercase;letter-spacing:0.07em;">Withdrawals</div>'
    f'<div style="font-size:1.6rem;font-weight:800;color:#f87171;">{withdrawals_count}</div></div>'
    f'{extra_stat}</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# PAGE HEADER
# ---------------------------------------------------------------------------
year_dot     = "#4ade80" if selected_year == "All" else ("#f0bf3e" if is_2026 else "#60a5fa")
arm_chip_col = "#f0bf3e" if is_2026 else ("#60a5fa" if is_2025 else "#4ade80")
study_status = "Follow-ups ongoing" if is_2026 else ("All visits complete" if is_2025 else "Combined view")
arm_chip     = (
    f'<div style="display:inline-flex;align-items:center;gap:7px;background:rgba(255,255,255,0.07);'
    f'border:1px solid rgba(255,255,255,0.14);border-radius:20px;padding:5px 14px;">'
    f'<div style="width:7px;height:7px;border-radius:50%;background:{arm_chip_col};flex:none;"></div>'
    f'<span style="font-size:0.78rem;font-weight:600;color:#c8d6f0;letter-spacing:0.03em;">'
    f'{arm_label} arm · {study_status}</span></div>'
) if selected_year != "All" else ""

st.markdown(
    f'<div style="background:linear-gradient(135deg,{NAVY} 0%,#1a3a6e 100%);border-radius:14px;'
    f'padding:28px 32px;margin-bottom:24px;display:flex;align-items:center;'
    f'justify-content:space-between;box-shadow:0 4px 20px rgba(15,32,64,0.18);">'
    f'<div>'
    f'<div style="font-size:1.5rem;font-weight:800;color:#fff;letter-spacing:-0.03em;line-height:1.1;">'
    f'Participant Tracking Report</div>'
    f'<div style="font-size:0.85rem;color:#8fb0d8;margin-top:6px;margin-bottom:10px;">'
    f'Recruitment, retention and follow-up attendance across all study visits</div>'
    f'<div style="display:flex;gap:8px;flex-wrap:wrap;">'
    f'<div style="display:inline-flex;align-items:center;gap:7px;background:rgba(255,255,255,0.10);'
    f'border:1px solid rgba(255,255,255,0.18);border-radius:20px;padding:5px 14px;">'
    f'<div style="width:7px;height:7px;border-radius:50%;background:{year_dot};flex:none;"></div>'
    f'<span style="font-size:0.78rem;font-weight:700;color:#fff;letter-spacing:0.04em;">'
    f'Viewing: {year_label}</span></div>'
    f'{arm_chip}</div></div>'
    f'<div style="display:flex;gap:24px;text-align:center;">'
    f'<div><div style="font-size:2rem;font-weight:800;color:#fff;">{n_recruited}</div>'
    f'<div style="font-size:0.68rem;color:#8fb0d8;text-transform:uppercase;letter-spacing:0.06em;">Recruited</div></div>'
    f'<div style="width:1px;background:rgba(255,255,255,0.12);"></div>'
    f'<div><div style="font-size:2rem;font-weight:800;color:#4ade80;">{retention_pct:.0f}%</div>'
    f'<div style="font-size:0.68rem;color:#8fb0d8;text-transform:uppercase;letter-spacing:0.06em;">Retained</div></div>'
    f'<div style="width:1px;background:rgba(255,255,255,0.12);"></div>'
    f'<div><div style="font-size:2rem;font-weight:800;color:#f87171;">{withdrawals_count}</div>'
    f'<div style="font-size:0.68rem;color:#8fb0d8;text-transform:uppercase;letter-spacing:0.06em;">Withdrawn</div></div>'
    f'</div></div>',
    unsafe_allow_html=True,
)

if n_recruited == 0:
    st.markdown(
        f'<div style="background:#fff;border-radius:12px;padding:48px 32px;text-align:center;'
        f'border:1px solid #e4eaf5;box-shadow:0 2px 8px rgba(30,50,100,0.07);">'
        f'<div style="font-size:2.5rem;margin-bottom:12px;">&#128269;</div>'
        f'<div style="font-size:1.1rem;font-weight:700;color:{NAVY};margin-bottom:6px;">'
        f'No participants found for {year_label}</div>'
        f'<div style="font-size:0.88rem;color:{GREY};">Try a different year or choose <strong>All</strong>.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.stop()

# ── Ongoing banner ──
if ongoing_visits:
    sorted_ongoing = sorted(ongoing_visits, key=lambda v: visit_order.index(v))
    ongoing_banner(sorted_ongoing, selected_year)

# ---------------------------------------------------------------------------
# Section 1 – Recruitment & Withdrawals
# ---------------------------------------------------------------------------
section_header("Recruitment & Withdrawals", color=BLUE, icon="👥")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(metric_card("Total Recruited", n_recruited, color=BLUE, icon="🧪"), unsafe_allow_html=True)
with col2:
    st.markdown(metric_card("Still in Study", f"{retention} ({retention_pct:.1f}%)", color=GREEN, icon="✅"), unsafe_allow_html=True)
with col3:
    st.markdown(metric_card("Withdrawals", withdrawals_count, color=RED, icon="⚠️"), unsafe_allow_html=True)

st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

_, col_chart, _ = st.columns([0.5, 2, 0.5])
with col_chart:
    fig_donut = go.Figure(go.Pie(
        labels=["Active", "Withdrawn"],
        values=[retention, withdrawals_count],
        hole=0.58,
        marker=dict(colors=[CHART_BLUE, CHART_RED]),
        textfont=dict(size=13),
        hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
    ))
    fig_donut.update_layout(
        annotations=[dict(text=f"<b>{retention_pct:.0f}%</b><br><span style='font-size:10px'>Active</span>",
                          x=0.5, y=0.5, font_size=18, showarrow=False)],
        legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.05),
    )
    st.plotly_chart(
        style_chart(fig_donut, f"Active vs Withdrawn — {year_label}", height=300),
        use_container_width=True,
    )

insight_box("Most participants remain active in the study. Withdrawals are a small fraction of total recruitment.", color=BLUE)

# ---------------------------------------------------------------------------
# Section 2 – Recruitment Timeline
# ---------------------------------------------------------------------------
if "enrollment_date" in baseline.columns:
    section_header("Recruitment Over Time", color=GREEN, icon="📅")

    df_dates = baseline.copy()
    df_dates["enrollment_date"] = pd.to_datetime(df_dates["enrollment_date"], errors="coerce").dt.normalize()
    df_dates = df_dates.dropna(subset=["enrollment_date"])

    weekly = (
        df_dates.groupby(pd.Grouper(key="enrollment_date", freq="W"))["infant_id"]
        .nunique().reset_index().rename(columns={"infant_id": "weekly_recruits"})
    )
    weekly["cumulative"] = weekly["weekly_recruits"].cumsum()

    fig_recruit = go.Figure()
    fig_recruit.add_trace(go.Scatter(
        x=weekly["enrollment_date"], y=weekly["cumulative"],
        mode="lines+markers", line=dict(color=CHART_BLUE, width=3),
        fill="tozeroy", fillcolor="rgba(46,110,219,0.08)",
        marker=dict(size=7, color=CHART_BLUE),
        hovertemplate="Week of %{x|%b %d, %Y}<br>Cumulative: <b>%{y}</b><extra></extra>",
    ))
    st.plotly_chart(
        style_chart(fig_recruit, f"Cumulative Recruitment by Week — {year_label}", height=380),
        use_container_width=True,
    )
    insight_box("Recruitment grew steadily over the study period.", color=GREEN)

# ---------------------------------------------------------------------------
# Section 3 – Follow-up Attendance
# ---------------------------------------------------------------------------
section_header("Follow-up Attendance", color=PURPLE, icon="🔄")

fig_follow = go.Figure()
fig_follow.add_trace(go.Bar(
    x=follow_df["Visit"], y=follow_df["Completed"], name="Attended",
    marker_color=CHART_BLUE,
    hovertemplate="%{x}: <b>%{y}</b> attended<extra></extra>",
))
if ongoing_visits:
    fig_follow.add_trace(go.Bar(
        x=follow_df["Visit"], y=follow_df["Pending"], name="Pending (ongoing)",
        marker_color=CHART_AMBER,
        hovertemplate="%{x}: <b>%{y}</b> yet to attend — visit still open<extra></extra>",
    ))
fig_follow.add_trace(go.Bar(
    x=follow_df["Visit"], y=follow_df["Missed"], name="Missed",
    marker_color=CHART_RED,
    hovertemplate="%{x}: <b>%{y}</b> missed<extra></extra>",
))
fig_follow.update_layout(barmode="relative")
st.plotly_chart(
    style_chart(fig_follow, f"Checkup Attendance at Each Visit — {year_label}", height=420),
    use_container_width=True,
)

if ongoing_visits:
    insight_box(
        "&#x1F7E6; <strong>Attended</strong> — confirmed at visit &nbsp;|&nbsp; "
        "&#x1F7E8; <strong>Pending</strong> — visit still open, data being collected &nbsp;|&nbsp; "
        "&#x1F7E5; <strong>Missed</strong> — did not attend (completed visits only)",
        color=PURPLE,
    )
else:
    insight_box(
        "Attended visits were consistently strong across all timepoints. "
        "Missed visits remain a small proportion throughout.",
        color=PURPLE,
    )

# ---------------------------------------------------------------------------
# Section 4 – Missed Visit Rates (completed timepoints only)
# ---------------------------------------------------------------------------
section_header("Missed Visit Rates", color=AMBER, icon="❌")

miss_plot_df = follow_df[~follow_df["Ongoing"]].copy()
miss_plot_df["MissedPct"] = (miss_plot_df["Missed"] / n_recruited * 100).round(1)
miss_plot_df["Text"]      = miss_plot_df["MissedPct"].map(lambda v: f"{v:.1f}%")

fig_misspct = px.bar(
    miss_plot_df, x="Visit", y="MissedPct", text="Text",
    color_discrete_sequence=[CHART_RED], labels={"MissedPct": "Missed (%)"},
)
fig_misspct.update_traces(textposition="outside", marker_line_width=0)
fig_misspct.update_layout(showlegend=False)
chart_note = " (Completed Timepoints)" if ongoing_visits else ""
st.plotly_chart(
    style_chart(fig_misspct, f"Share of Missed Visits{chart_note} — {year_label}", height=350),
    use_container_width=True,
)

if ongoing_visits:
    excl = ", ".join(sorted(ongoing_visits, key=lambda v: visit_order.index(v)))
    insight_box(
        f"Only completed visits are shown. <strong>{excl}</strong> are excluded — "
        f"data collection is still ongoing and pending attendances are not counted as missed.",
        color=AMBER,
    )
else:
    insight_box("All follow-up visits through Month 6 are now complete.", color=AMBER)

# ---------------------------------------------------------------------------
# Section 5 – Combined Trend
# ---------------------------------------------------------------------------
section_header("Attendance & Missed Visit Trends", color=BLUE, icon="📊")

trend_df = (follow_df[~follow_df["Ongoing"]].copy() if ongoing_visits else follow_df.copy())
trend_df["MissedPct"] = (trend_df["Missed"] / n_recruited * 100).round(1)

fig_col_line = go.Figure()
fig_col_line.add_trace(go.Bar(
    x=trend_df["Visit"], y=trend_df["Completed"], name="Completed",
    text=trend_df["Completed"], textposition="outside",
    marker_color=CHART_BLUE, marker_line_width=0,
))
fig_col_line.add_trace(go.Bar(
    x=trend_df["Visit"], y=trend_df["Missed"], name="Missed",
    text=trend_df["Missed"], textposition="outside",
    marker_color=CHART_RED, marker_line_width=0,
))
fig_col_line.add_trace(go.Scatter(
    x=trend_df["Visit"], y=trend_df["MissedPct"], name="Missed %",
    mode="lines+markers+text",
    text=[f"{v:.1f}%" for v in trend_df["MissedPct"]],
    textposition="top center", yaxis="y2",
    line=dict(color=CHART_ORANGE, width=2.5, dash="dot"),
    marker=dict(size=7),
))
fig_col_line.update_layout(
    barmode="group",
    yaxis=dict(title="Participants"),
    yaxis2=dict(title="Missed (%)", overlaying="y", side="right", showgrid=False),
)
trend_note = " (completed timepoints only)" if ongoing_visits else ""
st.plotly_chart(
    style_chart(fig_col_line, f"Completed vs Missed{trend_note} — {year_label}", height=450),
    use_container_width=True,
)
if ongoing_visits:
    insight_box(
        "Trend lines reflect only completed visits. "
        "Ongoing timepoints will be added here once data collection closes.",
        color=BLUE,
    )

# ---------------------------------------------------------------------------
# Section 6 – Participant Flow & Retention
# ---------------------------------------------------------------------------
section_header("Participant Flow & Retention", color=BLUE, icon="📈")

progress_df = follow_df.copy()
progress_df["RetentionPct"] = (progress_df["Completed"] / n_recruited * 100).round(1)

col_left, col_right = st.columns(2)

with col_left:
    bar_colors = [CHART_AMBER if row["Ongoing"] else CHART_BLUE for _, row in progress_df.iterrows()]
    fig_flow = go.Figure(go.Bar(
        x=progress_df["Visit"], y=progress_df["Completed"],
        text=progress_df["Completed"], textposition="outside",
        marker_color=bar_colors, marker_line_width=0,
        hovertemplate="%{x}: <b>%{y}</b> attended<extra></extra>",
        showlegend=False,
    ))
    if ongoing_visits:
        fig_flow.add_trace(go.Bar(x=[None], y=[None], name="Attended", marker_color=CHART_BLUE))
        fig_flow.add_trace(go.Bar(x=[None], y=[None], name="Ongoing (partial)", marker_color=CHART_AMBER))
        fig_flow.update_layout(barmode="group")
    st.plotly_chart(style_chart(fig_flow, "Participant Flow Across Visits", height=400), use_container_width=True)

with col_right:
    complete_prog = progress_df[~progress_df["Ongoing"]]
    ongoing_prog  = progress_df[progress_df["Ongoing"]]

    fig_retention = go.Figure()
    fig_retention.add_trace(go.Scatter(
        x=complete_prog["Visit"], y=complete_prog["RetentionPct"],
        mode="lines+markers+text", name="Retention (complete)",
        line=dict(color=CHART_BLUE, width=3),
        fill="tozeroy", fillcolor="rgba(46,110,219,0.10)",
        marker=dict(size=8, color=CHART_BLUE),
        text=[f"{v:.0f}%" for v in complete_prog["RetentionPct"]],
        textposition="top center",
        hovertemplate="%{x}: <b>%{y:.1f}%</b> retained<extra></extra>",
    ))
    if not ongoing_prog.empty:
        fig_retention.add_trace(go.Scatter(
            x=ongoing_prog["Visit"], y=ongoing_prog["RetentionPct"],
            mode="markers+text", name="Partial (ongoing)",
            marker=dict(size=10, color=CHART_AMBER, symbol="diamond"),
            text=[f"{v:.0f}%*" for v in ongoing_prog["RetentionPct"]],
            textposition="top center",
            hovertemplate="%{x}: <b>%{y:.1f}%</b> so far (ongoing)<extra></extra>",
        ))
    st.plotly_chart(style_chart(fig_retention, "Retention Rate Across Visits", height=400), use_container_width=True)

if ongoing_visits:
    insight_box(
        "Diamond markers (&#x1F536;) indicate visits still in progress — "
        "retention figures will rise as more families attend. "
        "Solid line shows confirmed retention for completed timepoints.",
        color=BLUE,
    )
else:
    insight_box(
        "Recruitment is complete. Retention remains strong through all timepoints, "
        "with follow-up visits fully concluded.",
        color=BLUE,
    )

# ---------------------------------------------------------------------------
# Section 7 – Key Takeaways
# ---------------------------------------------------------------------------
section_header("Key Takeaways", color=GREEN, icon="📝")

# Build list items as a Python list, then join — avoids raw HTML leaking into st.markdown
li_items = [
    f'Showing data for <strong>{year_label}</strong>.',
    f'A total of <strong>{n_recruited}</strong> participants were recruited.',
    f'<strong>{retention}</strong> participants remain active — a retention rate of <strong>{retention_pct:.1f}%</strong>.',
    f'<strong>{withdrawals_count}</strong> participant(s) withdrew from the study.',
    'Families showed strong commitment to scheduled follow-ups throughout all timepoints.',
]

if ongoing_visits:
    ongoing_str = ", ".join(sorted(ongoing_visits, key=lambda v: visit_order.index(v)))
    li_items.append(
        f'Follow-up visits for <strong>{ongoing_str}</strong> are <strong>still ongoing</strong> '
        f'(Intervention arm — {selected_year}). Data collection is in progress; '
        f'these are shown as Pending, not Missed.'
    )
else:
    li_items.append('All follow-up visits through Month 6 are now complete.')
    if missed_visit_count > 0:
        li_items.append(
            f'The highest number of missed visits occurred at '
            f'<strong>{missed_visit_label}</strong> ({missed_visit_count} missed).'
        )

# Arm context note
if is_2025:
    li_items.append(
        'This cohort represents the <strong>Control arm</strong> (2025) — standard care protocol.'
    )
elif is_2026:
    li_items.append(
        'This cohort represents the <strong>Intervention arm</strong> (2026) — enhanced follow-up protocol.'
    )

list_html = "".join(f"<li>{item}</li>" for item in li_items)
st.markdown(
    f'<div style="background:#fff;border-radius:12px;padding:20px 24px;border:1px solid #e4eaf5;'
    f'box-shadow:0 2px 8px rgba(30,50,100,0.07);line-height:1.9;font-size:0.9rem;color:#334;">'
    f'<ul style="margin:0;padding-left:18px;">{list_html}</ul></div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Section 8 – Withdrawal Reasons
# ---------------------------------------------------------------------------
if withdraw_explanations:
    section_header("Reasons for Withdrawal", color=RED, icon="📌")
    wr_html = "".join(f"<li>{s}</li>" for s in withdraw_explanations)
    st.markdown(
        f'<div style="background:#fff;border-radius:12px;padding:20px 24px;border:1px solid #e4eaf5;'
        f'box-shadow:0 2px 8px rgba(30,50,100,0.07);line-height:1.9;font-size:0.9rem;color:#334;">'
        f'<ul style="margin:0;padding-left:18px;">{wr_html}</ul></div>',
        unsafe_allow_html=True,
    )

# ── Footer ──
st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)
st.markdown(
    f'<div style="text-align:center;color:{GREY};font-size:0.75rem;'
    f'border-top:1px solid #e4eaf5;padding-top:16px;">'
    f'Participant Tracking Dashboard &nbsp;&#183;&nbsp; {year_label}</div>',
    unsafe_allow_html=True,
)
