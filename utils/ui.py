"""Shared styling: white background, navy sidebar, light-blue accents, rounded cards."""
import streamlit as st

NAVY, LIGHT_BLUE = "#0B1F3A", "#E8F1FB"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
.stApp {{ background: #F3F7FC; color: {NAVY}; }}
.stApp p, .stApp label, .stApp span, .stApp li, .stApp div[data-testid="stMarkdownContainer"] {{ color: {NAVY}; }}
.stApp input, .stApp textarea {{ color: {NAVY} !important; background: #FFFFFF !important; }}
section[data-testid="stSidebar"] {{ background: {NAVY}; }}
section[data-testid="stSidebar"] * {{ color: #F3F7FC !important; }}
section[data-testid="stSidebar"] .stRadio label {{ padding: 6px 10px; border-radius: 10px; }}
section[data-testid="stSidebar"] .stRadio label:hover {{ background: rgba(255,255,255,.08); }}
.kpi-card {{ background: {LIGHT_BLUE}; border-radius: 16px; padding: 18px 20px;
    border: 1px solid #D3E3F6; }}
.kpi-label {{ color: #4A6584; font-size: 13px; font-weight: 500; }}
.kpi-value {{ color: {NAVY}; font-size: 30px; font-weight: 700; line-height: 1.2; }}
h1, h2, h3 {{ color: {NAVY}; }}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def kpi_card(label: str, value, col):
    col.markdown(
        f'<div class="kpi-card"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div></div>', unsafe_allow_html=True)


def show_chart(fig):
    """Plotly chart full-width (works across Streamlit versions)."""
    fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="rgba(0,0,0,0)",
                      font=dict(color=NAVY))
    try:
        st.plotly_chart(fig, width="stretch")
    except Exception:
        st.plotly_chart(fig, use_container_width=True)


def show_df(df):
    try:
        st.dataframe(df, width="stretch", hide_index=True)
    except Exception:
        st.dataframe(df, use_container_width=True, hide_index=True)


def flash(message: str, icon: str = "✅"):
    """Remember a message to show after the next rerun (st.rerun clears normal messages)."""
    st.session_state["_flash"] = (message, icon)


def show_flash():
    if "_flash" in st.session_state:
        msg, icon = st.session_state.pop("_flash")
        st.toast(msg, icon=icon)


def fmt_dt(value, with_time=True):
    if not value:
        return ""
    return f"{value:%d %b %Y %H:%M}" if with_time else f"{value:%d %b %Y}"
