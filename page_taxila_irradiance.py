import math
import streamlit as st
from datetime import date
import calendar
import pandas as pd
import plotly.graph_objects as go

def show():
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
        return sol, vf, None, GF, GR

    # ── Inject page-level CSS overrides for no-scroll layout ──────────────────
    st.markdown("""
    <style>
      /* Remove Streamlit default padding so we control every pixel */
      .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0 !important;
        max-width: 100% !important;
      }

      /* ── Taxila Header ── */
      .tx-header {
        font-family: 'Manrope', sans-serif;
        font-size: 1.45rem;
        font-weight: 800;
        color: #000000;
        letter-spacing: -0.5px;
        line-height: 1.1;
      }
      .tx-meta {
        font-size: 0.78rem;
        color: #6b7280;
        font-weight: 500;
        letter-spacing: 0.3px;
        margin-top: 2px;
        margin-bottom: 6px;
      }

      /* ── Assumption badges ── */
      .badge-row {
        display: flex;
        gap: 8px;
        margin-bottom: 8px;
        flex-wrap: wrap;
      }
      .badge {
        background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%);
        color: #ffffff;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 20px;
        letter-spacing: 0.5px;
        white-space: nowrap;
      }

      /* ── Section title (compact) ── */
      .tx-sec {
        font-size: 0.7rem;
        font-weight: 800;
        color: #0f766e;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        border-left: 3px solid #0f766e;
        padding-left: 7px;
        margin: 4px 0 4px;
      }
      .tx-table-wrap {
        overflow: auto;
        max-height: 400px;
        border-radius: 10px;
        border: 1.5px solid #e0e7ff;
        margin-top: 4px;
      }
      .tx-table {
        width: max-content;
        min-width: 100%;
        border-collapse: collapse;
        font-size: 0.74rem;
        font-family: 'Manrope', sans-serif;
      }
      .tx-table thead th {
        position: sticky;
        top: 0;
        background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%);
        color: #ffffff;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 7px 12px;
        text-align: center;
        white-space: nowrap;
        z-index: 3;
        letter-spacing: 0.5px;
        border-right: 1px solid rgba(255,255,255,0.1);
      }
      .tx-table thead th:first-child {
        position: sticky;
        left: 0;
        z-index: 4;
        background: #0f766e;
        min-width: 100px;
      }
      .tx-table tbody td {
        padding: 8px 12px;
        text-align: center;
        border-bottom: 1px solid #f1f5f9;
        border-right: 1px solid #f1f5f9;
        color: #374151;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        white-space: nowrap;
      }
      .tx-table tbody td:first-child {
        position: sticky;
        left: 0;
        z-index: 2;
        font-family: 'Manrope', sans-serif;
        font-weight: 700;
        font-size: 0.78rem;
        color: #1a1a2e;
        background: #eef2ff !important;
        text-align: left;
        border-right: 2px solid #c7d2fe;
      }
      .tx-table tbody tr:hover td {
        background: #f0fdfa !important;
      }
      .tx-table tbody tr:hover td:first-child {
        background: #e0e7ff !important;
      }
    </style>
    """, unsafe_allow_html=True)

    # ── Sidebar ────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown('<div class="bipv-header">☀ BIPV</div>', unsafe_allow_html=True)
        st.markdown('<div class="bipv-sub">Taxila Irradiance Data</div>', unsafe_allow_html=True)

        if st.button("← Back to Home", key="taxila_back"):
            st.session_state.page = "home"
            st.rerun()

        st.markdown("""
        <div style="background:linear-gradient(135deg,#ecfeff,#f0fdfa);border:1.5px solid #99f6e4;
                    border-radius:8px;padding:10px 14px;margin:10px 0;">
            <div style="font-size:0.7rem;font-weight:800;color:#0f766e;text-transform:uppercase;
                        letter-spacing:1px;margin-bottom:6px;">⚙ Fixed Assumptions</div>
            <div style="font-size:0.82rem;color:#374151;line-height:1.6;">
                • Panel Azimuth γ<sub>P</sub> = <strong>0°</strong> (South)<br>
                • Tilt Angle β = <strong>90°</strong> (Vertical)
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<div class="section-label">① Date</div>', unsafe_allow_html=True)
        month_names = list(calendar.month_name)[1:]
        col_m, col_d = st.columns(2)
        with col_m:
            sel_month = st.selectbox("Month", month_names, index=11)
        month_idx = month_names.index(sel_month) + 1
        max_day = calendar.monthrange(2025, month_idx)[1]
        with col_d:
            sel_day = st.number_input("Day", min_value=1, max_value=max_day, value=min(21, max_day))
        sel_date = date(2025, month_idx, int(sel_day))

        st.markdown('<div class="section-label">② Location</div>', unsafe_allow_html=True)
        latitude   = st.number_input("Latitude φ (°)", -90.0, 90.0, 33.7, 0.5, key="t_lat")
        lambda_std = st.number_input("Standard Longitude λstd (°)", -180.0, 180.0, 75.0, 1.0, key="t_lstd")
        lambda_lcl = st.number_input("Local Longitude λlcl (°)", -180.0, 180.0, 73.1, 0.1, key="t_llcl")

        st.markdown('<div class="section-label">③ Building Geometry (m)</div>', unsafe_allow_html=True)
        H_b   = st.number_input("Building Height Hb", 0.5, 200.0, 10.0, 0.5, key="t_hb")
        h     = st.number_input("Panel Bottom Edge h", 0.0, 100.0, 1.0, 0.5, key="t_h")
        H_p   = st.number_input("Panel Height Hp", 0.1, 50.0, 2.0, 0.1, key="t_hp")
        d_val = st.number_input("Panel-to-Wall Distance d", 0.01, 20.0, 0.3, 0.01, key="t_d")

        st.markdown('<div class="section-label">④ Albedo</div>', unsafe_allow_html=True)
        rho_grd = st.number_input("Ground Albedo ρ_grd", 0.0, 1.0, 0.2, 0.01, key="t_rgrd")
        rho_w   = st.number_input("Wall Albedo ρ_w", 0.0, 1.0, 0.5, 0.01, key="t_rw")

    # ── Load & compute data ────────────────────────────────────────────────────
    @st.cache_data
    def load_irradiance_data():
        return pd.read_csv("Taxila_Irradiance_Data.csv")

    df_irr = load_irradiance_data()
    df_day = df_irr[(df_irr['Month'] == month_idx) & (df_irr['Day'] == int(sel_day))]

    hours, ghi_list, dhi_list, gf_list, gr_list, gt_list = [], [], [], [], [], []
    if not df_day.empty:
        for _, row in df_day.iterrows():
            h_taxila = row['Hour Taxila']
            g_h  = row['G(h)']
            gd_h = row['Gd(h)']
            _, _, _, curr_gf, curr_gr = compute_irradiance(
                sel_date, h_taxila, g_h, gd_h, latitude, lambda_std, lambda_lcl,
                H_b, h, H_p, d_val, rho_grd, rho_w)
            hours.append(int(h_taxila))
            ghi_list.append(round(g_h,   2))
            dhi_list.append(round(gd_h,  2))
            gf_list.append(round(curr_gf, 2))
            gr_list.append(round(curr_gr, 2))
            gt_list.append(round(curr_gf + curr_gr, 2))

    # ── Header strip ──────────────────────────────────────────────────────────
    st.markdown(
        f'<div class="tx-header">Taxila Irradiance Data Analysis</div>'
        f'<div class="tx-meta">{sel_date.strftime("%B %d, %Y")} &nbsp;•&nbsp; '
        f'Lat {latitude}° &nbsp;|&nbsp; λ_lcl {lambda_lcl}° &nbsp;•&nbsp; β = 90° &nbsp; γ_P = 0°</div>',
        unsafe_allow_html=True)

    st.markdown("""
    <div class="badge-row">
        <span class="badge">GHI — Global Horizontal Irradiance </span>
        <span class="badge">DHI — Diffused Horizontal Irradiance</span>
        <span class="badge">GF — Front side global Irradiance</span>
        <span class="badge">GR — Rear side global Irradiance</span>
        <span class="badge">GT = GF + GR</span>
    </div>
    """, unsafe_allow_html=True)

    if df_day.empty:
        st.warning("No data available for the selected date.")
        return

    # ── Graph (full width, on top) ────────────────────────────────────────────
    st.markdown('<div class="tx-sec">Hourly Irradiance Profile</div>', unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hours, y=ghi_list, mode='lines+markers', name='GHI',
                             line=dict(color='#1e3a8a', width=2), marker=dict(size=4)))
    fig.add_trace(go.Scatter(x=hours, y=dhi_list, mode='lines+markers', name='DHI',
                             line=dict(color='#ea580c', width=2), marker=dict(size=4)))
    fig.add_trace(go.Scatter(x=hours, y=gf_list, mode='lines+markers', name='GF',
                             line=dict(color='#0f766e', width=2.5), marker=dict(size=5)))
    fig.add_trace(go.Scatter(x=hours, y=gr_list, mode='lines+markers', name='GR',
                             line=dict(color='#7c3aed', width=2.5), marker=dict(size=5)))
    fig.add_trace(go.Scatter(x=hours, y=gt_list, mode='lines+markers', name='GT',
                             line=dict(color='#545454', width=2.5), marker=dict(size=5)))

    fig.update_layout(
        height=350,
        margin=dict(l=40, r=20, t=30, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.01,
                    xanchor="right", x=1, font=dict(size=11)),
        plot_bgcolor='#f8fafc', paper_bgcolor='white',
        font=dict(family='Manrope, sans-serif', size=11),
        xaxis=dict(
            title=dict(text='Hour (Taxila Time)', font=dict(size=12, color='#374151')),
            showgrid=True, gridwidth=1, gridcolor='#e2e8f0',
            linecolor='#e2e8f0', tickcolor='#e2e8f0',
            tickmode='linear', tick0=0, dtick=1,
            tickfont=dict(size=10, color='#6b7280'), zeroline=False),
        yaxis=dict(
            title=dict(text='Irradiance (W/m²)', font=dict(size=12, color='#374151')),
            showgrid=True, gridwidth=1, gridcolor='#e2e8f0',
            tickfont=dict(size=10, color='#6b7280'), zeroline=False)
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Table below graph (full width, transposed) ────────────────────────────
    st.markdown('<div class="tx-sec">Hourly Irradiance Data Table (W/m²)</div>', unsafe_allow_html=True)

    # Build hour → values mapping
    hour_data = {}
    for i, hv in enumerate(hours):
        hour_data[hv] = {
            'GHI': ghi_list[i], 'DHI': dhi_list[i],
            'GF': gf_list[i], 'GR': gr_list[i], 'GT': gt_list[i]
        }

    # Transposed Table Rendering
    # Headers: Parameter | 00:00 | 01:00 | ... | 23:00
    hour_headers = "".join(f"<th>{h:02d}:00</th>" for h in range(24))
    header_html = f"<thead><tr><th>Parameter</th>{hour_headers}</tr></thead>"

    params = ['GHI', 'DHI', 'GF', 'GR', 'GT']
    param_styles = {
        'GHI': 'color:#1e3a8a;',
        'DHI': 'color:#ea580c;font-weight:700;',
        'GF':  'color:#0f766e;font-weight:600;',
        'GR':  'color:#7c3aed;font-weight:600;',
        'GT':  'color:#545454;'
    }

    body_html = "<tbody>"
    for p in params:
        cells = []
        for h in range(24):
            val = hour_data.get(h, {}).get(p, 0.0)
            fmt_val = "0" if val == 0 else f"{val:.1f}"
            cells.append(f"<td style='{param_styles[p]}'>{fmt_val}</td>")
        body_html += f"<tr><td style='{param_styles[p]}'>{p}</td>{''.join(cells)}</tr>"
    body_html += "</tbody>"

    table_html = f"""
    <div class="tx-table-wrap">
      <table class="tx-table">
        {header_html}
        {body_html}
      </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)
