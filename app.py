import streamlit as st

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BIPV Irradiance Calculator",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');

  html, body, [data-testid="stApp"],
  [data-testid="stAppViewContainer"],
  [data-testid="stMain"],
  .main, .block-container,
  [data-testid="stSidebar"],
  [data-testid="stSidebarContent"] {
    background-color: #ffffff !important;
    color: #1a1a2e !important;
  }

  html, body, .stApp { font-family: 'Manrope', sans-serif; }

  [data-testid="stSidebar"] {
    background-color: #f8f9ff !important;
    border-right: 2px solid #e8eaf6;
  }
  [data-testid="stSidebar"] * { font-family: 'Manrope', sans-serif !important; }

  /* Hide sidebar toggle/collapse buttons */
  [data-testid="collapsedControl"],
  [data-testid="stSidebarCollapseButton"],
  [data-testid="stSidebarHeader"] button,
  section[data-testid="stSidebar"] button[aria-label="Collapse sidebar"],
  button[kind="header"] {
    display: none !important;
  }

  .bipv-header {
    font-family: 'Manrope', sans-serif;
    font-size: 1.6rem;
    font-weight: 800;
    color: #1a1a2e;
    letter-spacing: -0.6px;
    margin-bottom: 4px;
  }
  .bipv-sub {
    font-size: 0.82rem;
    color: #6b7280;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    margin-bottom: 1.5rem;
    font-weight: 500;
  }
  .section-label {
    font-family: 'Manrope', sans-serif;
    font-size: 0.68rem;
    font-weight: 700;
    color: #0f766e;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin: 1.2rem 0 0.4rem;
    padding-bottom: 4px;
    border-bottom: 1px solid #ccfbf1;
  }
  .metric-card {
    background: #f8f9ff;
    border: 1.5px solid #e0e7ff;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
  }
  .metric-label {
    font-size: 0.72rem;
    font-weight: 600;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 3px;
  }
  .metric-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.55rem;
    font-weight: 600;
    color: #1a1a2e;
  }
  .metric-unit { font-size: 0.78rem; color: #9ca3af; margin-left: 4px; }

  .inter-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8rem;
    margin-top: 6px;
  }
  .inter-table th {
    background: #eef2ff;
    color: #4338ca;
    font-family: 'Manrope', sans-serif;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 6px 10px;
    text-align: left;
    border-bottom: 2px solid #c7d2fe;
  }
  .inter-table td {
    padding: 6px 10px;
    border-bottom: 1px solid #f1f5f9;
    color: #374151;
    vertical-align: middle;
  }
  .inter-table tr:last-child td { border-bottom: none; }
  .inter-table td:last-child {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    color: #1a1a2e;
    text-align: right;
  }
  .inter-table tr:hover td { background: #f5f3ff; }

  .result-banner {
    background: #0f766e;
    border-radius: 12px;
    padding: 18px 24px;
    display: flex;
    justify-content: space-around;
    margin-bottom: 1.5rem;
  }
  .res-item { text-align: center; }
  .res-label {
    font-size: 0.72rem;
    font-weight: 600;
    color: rgba(255,255,255,0.7);
    text-transform: uppercase;
    letter-spacing: 1px;
  }
  .res-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.9rem;
    font-weight: 700;
    color: #ffffff;
  }
  .res-unit { font-size: 0.85rem; color: rgba(255,255,255,0.6); }

  .sec-title {
    font-family: 'Manrope', sans-serif;
    font-size: 0.78rem;
    font-weight: 800;
    color: #0f766e;
    text-transform: uppercase;
    letter-spacing: 1px;
    border-left: 3px solid #0f766e;
    padding-left: 8px;
    margin: 1rem 0 0.5rem;
  }

  label { font-size: 0.82rem !important; font-weight: 500 !important; color: #374151 !important; }

  .stNumberInput input, .stTextInput input {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.88rem !important;
    border-radius: 6px !important;
  }

  /* Style number input step buttons */
  button[data-testid="stNumberInputStepUp"],
  button[data-testid="stNumberInputStepDown"] {
    color: #0f766e !important;
    background-color: #ecfeff !important;
  }
  button[data-testid="stNumberInputStepUp"]:hover,
  button[data-testid="stNumberInputStepDown"]:hover {
    background-color: #ccfbf1 !important;
    color: #115e59 !important;
    border-color: #0f766e !important;
  }

  /* Style sidebar toggle button (open/close) */
  button[data-testid="collapsedControl"],
  [data-testid="stSidebar"] button[kind="header"] {
    color: #0f766e !important;
    background-color: #ccfbf1 !important;
    border-radius: 8px !important;
    opacity: 1 !important;
    transition: all 0.2s;
  }
  button[data-testid="collapsedControl"]:hover,
  [data-testid="stSidebar"] button[kind="header"]:hover {
    background-color: #99f6e4 !important;
    color: #115e59 !important;
    transform: scale(1.05);
  }
  
  /* Ensure the open button SVG inherits the green color */
  button[data-testid="collapsedControl"] svg,
  [data-testid="stSidebar"] button[kind="header"] svg {
    fill: currentColor !important;
    stroke: currentColor !important;
  }

  .insight-wrap {
    background: radial-gradient(130% 120% at 100% 0%, #ecfeff 0%, #f8fafc 55%, #ffffff 100%);
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 16px;
    margin-bottom: 14px;
  }
  .insight-title {
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 800;
    color: #0f766e;
    margin-bottom: 10px;
  }
  .insight-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }
  .insight-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 10px 12px;
  }
  .insight-label {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.7px;
    color: #64748b;
    margin-bottom: 4px;
  }
  .insight-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1rem;
    font-weight: 700;
    color: #0f172a;
  }

  @media (max-width: 960px) {
    .result-banner {
      display: grid;
      grid-template-columns: 1fr;
      gap: 14px;
      text-align: left;
    }
    .result-banner .res-item {
      border-left: none !important;
      border-right: none !important;
      padding: 0 !important;
    }
    .insight-grid {
      grid-template-columns: 1fr;
    }
  }

  .night-warn {
    background: #fff7ed;
    border: 1.5px solid #fed7aa;
    border-radius: 8px;
    padding: 12px 16px;
    color: #9a3412;
    font-size: 0.85rem;
    font-weight: 500;
  }

  #MainMenu, footer, header { visibility: hidden; }

  /* Sidebar Back Button styling */
  section[data-testid="stSidebar"] .stButton > button {
    background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Manrope', sans-serif !important;
    font-weight: 700 !important;
    padding: 10px 16px !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 10px rgba(15,118,110,0.2) !important;
    margin-bottom: 1rem !important;
  }
  section[data-testid="stSidebar"] .stButton > button:hover {
    background: linear-gradient(135deg, #115e59 0%, #0f766e 100%) !important;
    box-shadow: 0 6px 15px rgba(15,118,110,0.3) !important;
    transform: translateY(-1px) !important;
  }
</style>
""", unsafe_allow_html=True)


# ─── Session State for Navigation ──────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "home"


# ─── Page Router ───────────────────────────────────────────────────────────────
if st.session_state.page == "home":
    # Hide sidebar + disable scroll on home
    st.markdown("""
    <style>
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="stSidebarCollapsedControl"] { display: none !important; }

        /* Lock viewport – no scroll */
        html, body, [data-testid="stApp"],
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {
            overflow: hidden !important;
            height: 100vh !important;
        }
        .block-container {
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            max-width: 900px !important;
            margin: 0 auto !important;
            display: flex;
            flex-direction: column;
            justify-content: center;
            height: 100vh;
        }

        /* ── Home title ── */
        .home-title {
            font-family: 'Manrope', sans-serif;
            font-size: 2.4rem;
            font-weight: 900;
            color: #1a1a2e;
            text-align: center;
            letter-spacing: -0.8px;
            margin-bottom: 2rem;
        }

        /* ── Teal buttons – target ALL buttons on home page ── */
        .stButton > button {
            width: 100% !important;
            background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%) !important;
            color: #ffffff !important;
            font-family: 'Manrope', sans-serif !important;
            font-size: 1.15rem !important;
            font-weight: 700 !important;
            border: none !important;
            border-radius: 14px !important;
            padding: 22px 20px !important;
            min-height: 70px !important;
            cursor: pointer !important;
            transition: all 0.25s ease !important;
            box-shadow: 0 4px 14px rgba(15,118,110,0.25) !important;
            letter-spacing: 0.2px !important;
        }
        .stButton > button:hover {
            background: linear-gradient(135deg, #115e59 0%, #0f766e 100%) !important;
            box-shadow: 0 6px 20px rgba(15,118,110,0.35) !important;
            transform: translateY(-2px) !important;
        }
        .stButton > button:active {
            transform: translateY(0) !important;
        }

        /* ── Description card ── */
        .home-desc {
            background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%);
            border-radius: 16px;
            padding: 32px 40px;
            margin-top: 2rem;
            text-align: center;
            box-shadow: 0 4px 20px rgba(15,118,110,0.2);
        }
        .home-desc p {
            font-family: 'Manrope', sans-serif;
            font-size: 1.05rem;
            font-weight: 500;
            color: #ffffff;
            line-height: 1.8;
            margin: 0;
            letter-spacing: 0.2px;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="home-title">Vertical BIPV Irradiance Analysis</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2, gap="medium")
    with col1:
        if st.button("Manual Irradiance Tester", key="btn_manual", use_container_width=True):
            st.session_state.page = "manual"
            st.rerun()
    with col2:
        if st.button("Taxila Irradiance Data", key="btn_taxila", use_container_width=True):
            st.session_state.page = "taxila"
            st.rerun()

    st.markdown("""
    <div class="home-desc">
        <p>
            Analyze front and rear irradiance on vertically integrated bifacial 
            photovoltaic panels mounted on building façades. This tool uses cavity 
            view-factor models to compute GF (front), GR (rear) and GT (total) 
            irradiance based on solar geometry, building dimensions, and surface 
            albedo — enabling accurate energy-yield estimation for wall-mounted 
            BIPV systems.
        </p>
    </div>
    """, unsafe_allow_html=True)

elif st.session_state.page == "manual":
    import page_manual_irradiance
    page_manual_irradiance.show()

elif st.session_state.page == "taxila":
    import page_taxila_irradiance
    page_taxila_irradiance.show()