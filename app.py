import math
import streamlit as st
from datetime import date
import calendar

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
</style>
""", unsafe_allow_html=True)


# ─── Core Math ────────────────────────────────────────────────────────────────
DEG_TO_RAD = math.pi / 180.0
RAD_TO_DEG = 180.0 / math.pi

def d2r(a): return a * DEG_TO_RAD
def r2d(a): return a * RAD_TO_DEG

def solar_position(date_obj, LCT, latitude, lambda_std, lambda_lcl):
    n = date_obj.timetuple().tm_yday
    delta_deg = 23.45 * math.sin(d2r(360.0 * (284 + n) / 365.0))
    B_rad = d2r(360.0 * (n - 1) / 365.0)
    EoT = 229.2 * (0.000075 + 0.001868 * math.cos(B_rad) - 0.032077 * math.sin(B_rad)
                   - 0.014615 * math.cos(2 * B_rad) - 0.04089 * math.sin(2 * B_rad))
    LST = LCT + (4.0 * (lambda_std - lambda_lcl) + EoT) / 60.0
    omega_deg = 15.0 * (LST - 12.0)
    phi_rad, delta_rad, omega_rad = d2r(latitude), d2r(delta_deg), d2r(omega_deg)
    cos_z = max(-1.0, min(1.0,
        math.sin(phi_rad) * math.sin(delta_rad) +
        math.cos(phi_rad) * math.cos(delta_rad) * math.cos(omega_rad)))
    theta_z = r2d(math.acos(cos_z))
    return {
        'n': n, 'delta': delta_deg, 'EoT': EoT, 'LST': LST,
        'omega': omega_deg, 'cos_z': cos_z, 'theta_z': theta_z,
        'alpha_s': 90.0 - theta_z
    }

def aoi_front(sol, latitude, tilt=90.0, panel_az=0.0):
    d, p, b, g, w = d2r(sol['delta']), d2r(latitude), d2r(tilt), d2r(panel_az), d2r(sol['omega'])
    sd, cd = math.sin(d), math.cos(d)
    sp, cp = math.sin(p), math.cos(p)
    sb, cb = math.sin(b), math.cos(b)
    sg, cg = math.sin(g), math.cos(g)
    sw, cw = math.sin(w), math.cos(w)
    cos_theta_F = (sd*sp*cb) - (sd*cp*sb*cg) + (cd*cp*cb*cw) + (cd*sp*sb*cg*cw) + (cd*sb*sg*sw)
    return max(-1.0, min(1.0, cos_theta_F))

def view_factors(H_b, h, H_p, d, alpha_s):
    L = H_b - H_p - h
    XR_sky = (H_p + math.sqrt(d**2 + L**2) - math.sqrt(d**2 + (H_p + L)**2)) / (2 * H_p)
    XR_grd = (H_p + math.sqrt(d**2 + h**2) - math.sqrt(d**2 + (H_p + h)**2)) / (2 * H_p)
    if 0 < alpha_s < 90:
        Delta = d * math.tan(d2r(alpha_s))
    elif alpha_s >= 90:
        Delta = 1e6
    else:
        Delta = 0.0
    t1 = math.sqrt(d**2 + (H_p - Delta)**2)
    t2 = math.sqrt(d**2 + (H_p + Delta)**2)
    t3 = 2 * math.sqrt(d**2 + Delta**2)
    XR_sh_w = max(0.0, min(1.0, (t1 + t2 - t3) / (2 * H_p)))
    XR_ush_w = max(0.0, 1.0 - XR_sky - XR_grd - XR_sh_w)
    return {
        'L': L, 'Delta': Delta,
        'XF_sky': 0.5, 'XF_grd': 0.5,
        'XR_sky': XR_sky, 'XR_grd': XR_grd,
        'XR_sh_w': XR_sh_w, 'XR_ush_w': XR_ush_w
    }

def compute_irradiance(date_obj, LCT, GHI, DHI, latitude, lambda_std, lambda_lcl,
                        H_b, h, H_p, d, rho_grd, rho_w):
    sol = solar_position(date_obj, LCT, latitude, lambda_std, lambda_lcl)
    if sol['cos_z'] <= 0:
        return sol, None, None, 0.0, 0.0

    cos_theta_F = aoi_front(sol, latitude)
    theta_F = r2d(math.acos(cos_theta_F))
    RbF = (max(0.0, cos_theta_F) / sol['cos_z']
           if (-90 <= sol['omega'] <= 90 and sol['cos_z'] > 0) else 0.0)
    vf = view_factors(H_b, h, H_p, d, sol['alpha_s'])

    BHI = GHI - DHI
    GF = (BHI * RbF) + (DHI * vf['XF_sky']) + (GHI * rho_grd * vf['XF_grd'])
    term_sky = DHI * vf['XR_sky']
    term_grd = GHI * rho_grd * vf['XR_grd']
    term_sh  = ((DHI / 2.0) + (GHI * rho_grd / 2.0)) * rho_w * vf['XR_sh_w']
    term_ush = GF * rho_w * vf['XR_ush_w']
    GR = term_sky + term_grd + term_sh + term_ush

    extras = {
        'BHI': BHI, 'theta_F': theta_F, 'cos_theta_F': cos_theta_F, 'RbF': RbF,
        'term_sky': term_sky, 'term_grd': term_grd, 'term_sh': term_sh, 'term_ush': term_ush
    }
    return sol, vf, extras, GF, GR


# ─── Sidebar Inputs ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="bipv-header">☀ BIPV</div>', unsafe_allow_html=True)
    st.markdown('<div class="bipv-sub">Irradiance Calculator</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-label">① Date & Time</div>', unsafe_allow_html=True)
    month_names = list(calendar.month_name)[1:]
    col_m, col_d = st.columns(2)
    with col_m:
        sel_month = st.selectbox("Month", month_names, index=11)
    month_idx = month_names.index(sel_month) + 1
    max_day = calendar.monthrange(2025, month_idx)[1]
    with col_d:
        sel_day = st.number_input("Day", min_value=1, max_value=max_day, value=min(21, max_day))
    sel_date = date(2025, month_idx, int(sel_day))

    col_h, col_min = st.columns(2)
    with col_h:
        hr = st.number_input("Hour", 0, 23, 12)
    with col_min:
        mn = st.number_input("Min", 0, 59, 0, step=15)
    LCT = hr + mn / 60.0

    st.markdown('<div class="section-label">② Irradiance (W/m²)</div>', unsafe_allow_html=True)
    GHI = st.number_input("GHI – Global Horizontal", 0.0, 1500.0, 800.0, 10.0)
    DHI = st.number_input("DHI – Diffuse Horizontal", 0.0, 800.0, 150.0, 10.0)

    st.markdown('<div class="section-label">③ Location</div>', unsafe_allow_html=True)
    latitude   = st.number_input("Latitude φ (°)", -90.0, 90.0, 33.7, 0.5)
    lambda_std = st.number_input("Standard Longitude λstd (°)", -180.0, 180.0, 75.0, 1.0)
    lambda_lcl = st.number_input("Local Longitude λlcl (°)", -180.0, 180.0, 73.1, 0.1)

    st.markdown('<div class="section-label">④ Building Geometry (m)</div>', unsafe_allow_html=True)
    H_b = st.number_input("Building Height Hb", 0.5, 200.0, 10.0, 0.5)
    h   = st.number_input("Panel Bottom Edge h", 0.0, 100.0, 1.0, 0.5)
    H_p = st.number_input("Panel Height Hp", 0.1, 50.0, 2.0, 0.1)
    d   = st.number_input("Panel-to-Wall Distance d", 0.01, 20.0, 0.3, 0.01)

    st.markdown('<div class="section-label">⑤ Albedo</div>', unsafe_allow_html=True)
    rho_grd = st.number_input("Ground Albedo ρ_grd", 0.0, 1.0, 0.2, 0.01)
    rho_w   = st.number_input("Wall Albedo ρ_w", 0.0, 1.0, 0.5, 0.01)


# ─── Compute at selected time ─────────────────────────────────────────────────
sol, vf, extras, GF, GR = compute_irradiance(
    sel_date, LCT, GHI, DHI, latitude, lambda_std, lambda_lcl,
    H_b, h, H_p, d, rho_grd, rho_w)


# ─── Main Layout ──────────────────────────────────────────────────────────────
st.markdown('<div class="bipv-header">Vertical BIPV Irradiance Analysis</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="bipv-sub">{sel_date.strftime("%B %d, %Y")}  •  '
    f'{hr:02d}:{mn:02d} LCT  •  Lat {latitude}°  |  λ_lcl {lambda_lcl}°</div>',
    unsafe_allow_html=True)

# ── Final Results Banner ──
if sol['cos_z'] <= 0:
    st.markdown(
        '<div class="night-warn">🌙 Sun is below the horizon at this time — irradiance is zero.</div>',
        unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div class="result-banner">
      <div class="res-item">
        <div class="res-label">Front Irradiance GF</div>
        <div class="res-value">{GF:.1f}<span class="res-unit"> W/m²</span></div>
      </div>
      <div class="res-item" style="border-left:1px solid rgba(255,255,255,0.25);
                                   border-right:1px solid rgba(255,255,255,0.25);
                                   padding:0 32px;">
        <div class="res-label">Rear Irradiance GR</div>
        <div class="res-value">{GR:.1f}<span class="res-unit"> W/m²</span></div>
      </div>
      <div class="res-item">
        <div class="res-label">Bifacial Total GF+GR</div>
        <div class="res-value">{GF+GR:.1f}<span class="res-unit"> W/m²</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ── Two-column layout ──
def make_table(rows):
    body = "".join(
        f"<tr><td>{n}</td><td>{v} {u}</td></tr>" for n, v, u in rows)
    return (f'<table class="inter-table">'
            f'<thead><tr><th>Parameter</th><th>Value</th></tr></thead>'
            f'<tbody>{body}</tbody></table>')


if vf and extras and sol['cos_z'] > 0:
    row1_left, row1_right = st.columns(2, gap="large")
    
    with row1_left:
        st.markdown('<div class="sec-title">Cavity View Factors</div>', unsafe_allow_html=True)
        vf_sum = vf['XR_sky'] + vf['XR_grd'] + vf['XR_sh_w'] + vf['XR_ush_w']
        st.markdown(make_table([
            ("Top Gap L",        f"{vf['L']:.3f}",       "m"),
            ("Shadow Δ",         f"{vf['Delta']:.3f}",   "m"),
            ("XF_sky (front)",   f"{vf['XF_sky']:.4f}",  ""),
            ("XF_grd (front)",   f"{vf['XF_grd']:.4f}",  ""),
            ("XR_sky (rear)",    f"{vf['XR_sky']:.4f}",  ""),
            ("XR_grd (rear)",    f"{vf['XR_grd']:.4f}",  ""),
            ("XR_sh_w (rear)",   f"{vf['XR_sh_w']:.4f}", ""),
            ("XR_ush_w (rear)",  f"{vf['XR_ush_w']:.4f}",""),
            ("∑ Rear VF",        f"{vf_sum:.4f}",         "≈1"),
        ]), unsafe_allow_html=True)

    with row1_right:
        st.markdown('<div class="sec-title">Solar Position</div>', unsafe_allow_html=True)
        st.markdown(make_table([
            ("Day Number n",        sol['n'],                   ""),
            ("Declination δ",       f"{sol['delta']:.4f}",      "°"),
            ("EoT",                 f"{sol['EoT']:.4f}",        "min"),
            ("Local Solar Time",    f"{sol['LST']:.4f}",        "h"),
            ("Hour Angle ω",        f"{sol['omega']:.4f}",      "°"),
            ("Zenith Angle θz",     f"{sol['theta_z']:.4f}",    "°"),
            ("Inclination αs",      f"{sol['alpha_s']:.4f}",    "°"),
        ]), unsafe_allow_html=True)

    row2_left, row2_right = st.columns(2, gap="large")

    with row2_left:
        st.markdown('<div class="sec-title">Angles & Beam Ratio</div>', unsafe_allow_html=True)
        st.markdown(make_table([
            ("AOI Front θF",        f"{extras['theta_F']:.4f}",      "°"),
            ("cos θF",              f"{extras['cos_theta_F']:.4f}",  ""),
            ("Beam Tilt Ratio RbF", f"{extras['RbF']:.4f}",          ""),
            ("BHI (GHI–DHI)",       f"{extras['BHI']:.2f}",          "W/m²"),
        ]), unsafe_allow_html=True)

    with row2_right:
        st.markdown('<div class="sec-title">Rear Irradiance Breakdown</div>', unsafe_allow_html=True)
        st.markdown(make_table([
            ("Sky diffuse leakage",   f"{extras['term_sky']:.2f}", "W/m²"),
            ("Ground reflection",     f"{extras['term_grd']:.2f}", "W/m²"),
            ("Shaded wall bounce",    f"{extras['term_sh']:.2f}",  "W/m²"),
            ("Unshaded wall bounce",  f"{extras['term_ush']:.2f}", "W/m²"),
        ]), unsafe_allow_html=True)