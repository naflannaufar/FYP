import math
import streamlit as st
from datetime import date
import calendar
import numpy as np
from scipy.optimize import fsolve, minimize_scalar
from scipy.integrate import solve_ivp

def show():
    # ─── Page-level CSS Overrides ──────────────────────────────────────────────
    st.markdown("""
    <style>
      .block-container {
        padding-top: 0rem !important;
        padding-bottom: 2rem !important;
      }
      /* Sidebar active/inactive button overrides */
      section[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"] {
        background: #eef2ff !important;
        color: #0f766e !important;
        border: 1px solid #c7d2fe !important;
        box-shadow: none !important;
        font-weight: 500 !important;
      }
      section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%) !important;
        color: #ffffff !important;
        border: none !important;
        box-shadow: 0 4px 10px rgba(15,118,110,0.2) !important;
        font-weight: 700 !important;
      }
    </style>
    """, unsafe_allow_html=True)

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

    # ─── Sidebar Inputs ────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown('<div class="bipv-header">☀ BIPV</div>', unsafe_allow_html=True)
        st.markdown('<div class="bipv-sub">Manual Irradiance Tester</div>', unsafe_allow_html=True)

        if st.button("← Back to Home", key="manual_back"):
            st.session_state.page = "home"
            st.rerun()

        # Initialize session state defaults if not present
        if "active_tab" not in st.session_state:
            st.session_state.active_tab = "Optical"

        # Version key: bump this to force-reset defaults when they change
        _DEFAULTS_VERSION = 3
        defaults = {
            # Optical (matching couple.py exactly)
            'sel_month': 'December',
            'sel_day': 12,
            'hr': 12,
            'mn': 0,
            'GHI': 800.0,                 # couple.py: GHI = 800
            'DHI': 100.0,                 # couple.py: DHI = 100
            'latitude': 33.7,             # couple.py: latitude = 33.7
            'lambda_std': 75.0,           # couple.py: lambda_std = 75.0
            'lambda_lcl': 72.84,          # couple.py: lambda_lcl = 72.84
            'H_b': 10.0,                  # couple.py: H_b = 10.0
            'h': 5.0,                     # couple.py: h = 5
            'H_p': 2.0,                   # couple.py: H_p = 2.0
            'd_val': 0.2,                 # couple.py: d = 0.2
            'rho_grd': 0.3,              # couple.py: rho_grd = 0.3
            'rho_w': 0.3,                # couple.py: rho_w = 0.3
            
            # Thermal general (matching couple.py exactly)
            'A': 2.0,                     # couple.py: A = 2.0
            'T_room_C': 22.0,            # couple.py: T_room_C = 22.0
            'alpha_g': 0.05,             # couple.py: alpha_g = 0.05
            'tau_g': 0.90,               # couple.py: tau_g = 0.90
            'tau_rg': 0.90,              # couple.py: tau_rg = 0.90
            'eps_g': 0.85,               # couple.py: eps_g = 0.85
            'T_a_C': 25.0,              # couple.py: T_a_C = 25.0
            'u': 2.0,                    # couple.py: u = 2.0
            
            # Thermal materials (matching couple.py mat dict exactly)
            'mat_g_Cp': 800.0, 'mat_g_rho': 2500.0, 'mat_g_delta': 0.0032, 'mat_g_lam': 1.8,
            'mat_eva_Cp': 2090.0, 'mat_eva_rho': 960.0, 'mat_eva_delta': 0.0005, 'mat_eva_lam': 0.31,
            'mat_pv_Cp': 677.0, 'mat_pv_rho': 2330.0, 'mat_pv_delta': 0.0002, 'mat_pv_lam': 148.0,
            'mat_wall_Cp': 880.0, 'mat_wall_rho': 2400.0, 'mat_wall_delta': 0.2000, 'mat_wall_lam': 1.5,
            
            # Thermal gap (matching couple.py gap dict exactly)
            'gap_nu': 1.56e-5,           # couple.py: nu = 1.56e-5
            'gap_alpha_air': 2.21e-5,     # couple.py: alpha_air = 2.21e-5
            'gap_k_air': 0.0261,          # couple.py: k_air = 0.0261
            
            # Electrical STC (matching couple.py stc dict exactly)
            'Voc_F': 44.5,              # couple.py: Voc_F = 44.5
            'Isc_F': 9.96,              # couple.py: Isc_F = 9.96
            'Vmp_F': 37.9,              # couple.py: Vmp_F = 37.9
            'Imp_F': 9.38,              # couple.py: Imp_F = 9.38
            'Pmax_F': 355.0,            # couple.py: Pmax_F = 355.0
            'Isc_R': 8.53,              # couple.py: Isc_R = 8.53
            'Pmax_R': 302.0,            # couple.py: Pmax_R = 302.0
            'alpha_pct': 0.048,          # couple.py: alpha_pct = 0.048
            'beta_pct': -0.30,           # couple.py: beta_pct = -0.30
            'phi': 0.75,                 # couple.py: phi = 0.75
            'Ns': 72                     # couple.py: Ns = 72
        }

        # Force-reset all defaults if version changed (clears stale session state)
        if st.session_state.get('_defaults_version') != _DEFAULTS_VERSION:
            for k, v in defaults.items():
                st.session_state[k] = v
            st.session_state['_defaults_version'] = _DEFAULTS_VERSION
        else:
            for k, v in defaults.items():
                if k not in st.session_state:
                    st.session_state[k] = v

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

        st.markdown('<div class="section-label">🔧 Parameter Select</div>', unsafe_allow_html=True)
        tab_opt, tab_ther, tab_elec = st.tabs(["Optical", "Thermal", "Electrical"])
        month_names = list(calendar.month_name)[1:]

        with tab_opt:
            st.markdown('<div class="section-label">① Date & Time</div>', unsafe_allow_html=True)
            col_m, col_d = st.columns(2)
            with col_m:
                st.selectbox("Month", month_names, key='sel_month')
            month_idx = month_names.index(st.session_state.sel_month) + 1
            max_day = calendar.monthrange(2025, month_idx)[1]
            if st.session_state.sel_day > max_day:
                st.session_state.sel_day = max_day
            with col_d:
                st.number_input("Day", min_value=1, max_value=max_day, value=int(st.session_state['sel_day']), key='sel_day')
            
            col_h, col_min = st.columns(2)
            with col_h:
                st.number_input("Hour", 0, 23, value=int(st.session_state['hr']), key='hr')
            with col_min:
                st.number_input("Min", 0, 59, value=int(st.session_state['mn']), key='mn', step=15)
            
            st.markdown('<div class="section-label">② Irradiance (W/m²)</div>', unsafe_allow_html=True)
            st.number_input("GHI – Global Horizontal", 0.0, 1500.0, value=st.session_state['GHI'], key='GHI')
            st.number_input("DHI – Diffuse Horizontal", 0.0, 800.0, value=st.session_state['DHI'], key='DHI')
            
            st.markdown('<div class="section-label">③ Location</div>', unsafe_allow_html=True)
            st.number_input("Latitude φ (°)", -90.0, 90.0, value=st.session_state['latitude'], key='latitude')
            st.number_input("Standard Longitude λstd (°)", -180.0, 180.0, value=st.session_state['lambda_std'], key='lambda_std')
            st.number_input("Local Longitude λlcl (°)", -180.0, 180.0, value=st.session_state['lambda_lcl'], key='lambda_lcl')
            
            st.markdown('<div class="section-label">④ Building Geometry (m)</div>', unsafe_allow_html=True)
            st.number_input("Building Height Hb", 0.5, 200.0, value=st.session_state['H_b'], key='H_b')
            st.number_input("Panel Bottom Edge h", 0.0, 100.0, value=st.session_state['h'], key='h')
            st.number_input("Panel Height Hp", 0.1, 50.0, value=st.session_state['H_p'], key='H_p')
            st.number_input("Panel-to-Wall Distance d", 0.01, 20.0, value=st.session_state['d_val'], key='d_val')
            
            st.markdown('<div class="section-label">⑤ Albedo</div>', unsafe_allow_html=True)
            st.number_input("Ground Albedo ρ_grd", 0.0, 1.0, value=st.session_state['rho_grd'], key='rho_grd')
            st.number_input("Wall Albedo ρ_w", 0.0, 1.0, value=st.session_state['rho_w'], key='rho_w')

        with tab_ther:
            st.markdown('<div class="section-label">① Environment & Area</div>', unsafe_allow_html=True)
            st.number_input("Panel Area A (m²)", 0.1, 100.0, value=st.session_state['A'], key='A')
            st.number_input("Indoor Room Temp (°C)", -50.0, 100.0, value=st.session_state['T_room_C'], key='T_room_C')
            st.number_input("Ambient Air Temp (°C)", -50.0, 100.0, value=st.session_state['T_a_C'], key='T_a_C')
            st.number_input("Wind Speed u (m/s)", 0.0, 100.0, value=st.session_state['u'], key='u')
            
            st.markdown('<div class="section-label">② Glass Properties</div>', unsafe_allow_html=True)
            st.number_input("Absorptance of glass α_g", 0.0, 1.0, value=st.session_state['alpha_g'], key='alpha_g')
            st.number_input("Transmittance of front glass τ_g", 0.0, 1.0, value=st.session_state['tau_g'], key='tau_g')
            st.number_input("Transmittance of rear glass τ_rg", 0.0, 1.0, value=st.session_state['tau_rg'], key='tau_rg')
            st.number_input("Emissivity of glass ε_g", 0.0, 1.0, value=st.session_state['eps_g'], key='eps_g')
            
            st.markdown('<div class="section-label">③ Material Layers</div>', unsafe_allow_html=True)
            with st.expander("Glass layer properties"):
                st.number_input("Cp (J/kg·K)", value=st.session_state['mat_g_Cp'], key='mat_g_Cp')
                st.number_input("rho (kg/m³)", value=st.session_state['mat_g_rho'], key='mat_g_rho')
                st.number_input("delta (m)", value=st.session_state['mat_g_delta'], key='mat_g_delta', format="%.4f")
                st.number_input("lambda (W/m·K)", value=st.session_state['mat_g_lam'], key='mat_g_lam')
                
            with st.expander("EVA layer properties"):
                st.number_input("Cp (J/kg·K)", value=st.session_state['mat_eva_Cp'], key='mat_eva_Cp')
                st.number_input("rho (kg/m³)", value=st.session_state['mat_eva_rho'], key='mat_eva_rho')
                st.number_input("delta (m)", value=st.session_state['mat_eva_delta'], key='mat_eva_delta', format="%.5f")
                st.number_input("lambda (W/m·K)", value=st.session_state['mat_eva_lam'], key='mat_eva_lam')
                
            with st.expander("PV Silicon properties"):
                st.number_input("Cp (J/kg·K)", value=st.session_state['mat_pv_Cp'], key='mat_pv_Cp')
                st.number_input("rho (kg/m³)", value=st.session_state['mat_pv_rho'], key='mat_pv_rho')
                st.number_input("delta (m)", value=st.session_state['mat_pv_delta'], key='mat_pv_delta', format="%.5f")
                st.number_input("lambda (W/m·K)", value=st.session_state['mat_pv_lam'], key='mat_pv_lam')
                
            with st.expander("Concrete Wall properties"):
                st.number_input("Cp (J/kg·K)", value=st.session_state['mat_wall_Cp'], key='mat_wall_Cp')
                st.number_input("rho (kg/m³)", value=st.session_state['mat_wall_rho'], key='mat_wall_rho')
                st.number_input("delta (m)", value=st.session_state['mat_wall_delta'], key='mat_wall_delta', format="%.4f")
                st.number_input("lambda (W/m·K)", value=st.session_state['mat_wall_lam'], key='mat_wall_lam')

            st.markdown('<div class="section-label">④ Air Gap Constants</div>', unsafe_allow_html=True)
            st.number_input("Kinematic viscosity nu (m²/s)", value=st.session_state['gap_nu'], format="%.2e", key='gap_nu')
            st.number_input("Thermal diffusivity alpha_air (m²/s)", value=st.session_state['gap_alpha_air'], format="%.2e", key='gap_alpha_air')
            st.number_input("Thermal conductivity k_air (W/m·K)", value=st.session_state['gap_k_air'], format="%.4f", key='gap_k_air')

        with tab_elec:
            st.markdown('<div class="section-label">① Front Panel Datasheet</div>', unsafe_allow_html=True)
            st.number_input("Voc_F: Open-Circuit Voltage (V)", 0.0, 200.0, value=st.session_state['Voc_F'], key='Voc_F')
            st.number_input("Isc_F: Short-Circuit Current (A)", 0.0, 50.0, value=st.session_state['Isc_F'], key='Isc_F')
            st.number_input("Vmp_F: Max Power Voltage (V)", 0.0, 200.0, value=st.session_state['Vmp_F'], key='Vmp_F')
            st.number_input("Imp_F: Max Power Current (A)", 0.0, 50.0, value=st.session_state['Imp_F'], key='Imp_F')
            st.number_input("Pmax_F: Max Power (W)", 0.0, 1000.0, value=st.session_state['Pmax_F'], key='Pmax_F')
            
            st.markdown('<div class="section-label">② Rear Panel Datasheet</div>', unsafe_allow_html=True)
            st.number_input("Isc_R: Short-Circuit Current (A)", 0.0, 50.0, value=st.session_state['Isc_R'], key='Isc_R')
            st.number_input("Pmax_R: Max Power (W)", 0.0, 1000.0, value=st.session_state['Pmax_R'], key='Pmax_R')
            
            st.markdown('<div class="section-label">③ Coefficients & Tech</div>', unsafe_allow_html=True)
            st.number_input("alpha_pct: Temp Coeff of Isc (%/°C)", -5.0, 5.0, value=st.session_state['alpha_pct'], key='alpha_pct', format="%.3f")
            st.number_input("beta_pct: Temp Coeff of Voc (%/°C)", -5.0, 5.0, value=st.session_state['beta_pct'], key='beta_pct', format="%.2f")
            st.number_input("phi: Bifaciality Factor", 0.0, 1.5, value=st.session_state['phi'], key='phi', format="%.2f")
            st.number_input("Ns: Cells in Series", 1, 500, value=int(st.session_state['Ns']), key='Ns')

    # ─── Load state variables for calculations ───────────────────────────────
    sel_month = st.session_state.sel_month
    sel_day = st.session_state.sel_day
    hr = st.session_state.hr
    mn = st.session_state.mn
    GHI = st.session_state.GHI
    DHI = st.session_state.DHI
    latitude = st.session_state.latitude
    lambda_std = st.session_state.lambda_std
    lambda_lcl = st.session_state.lambda_lcl
    H_b = st.session_state.H_b
    h = st.session_state.h
    H_p = st.session_state.H_p
    d_val = st.session_state.d_val
    rho_grd = st.session_state.rho_grd
    rho_w = st.session_state.rho_w

    A = st.session_state.A
    T_room_C = st.session_state.T_room_C
    alpha_g = st.session_state.alpha_g
    tau_g = st.session_state.tau_g
    tau_rg = st.session_state.tau_rg
    eps_g = st.session_state.eps_g
    T_a_C = st.session_state.T_a_C
    u = st.session_state.u

    mat = {
        'g':    {'Cp': st.session_state.mat_g_Cp,  'rho': st.session_state.mat_g_rho,  'delta': st.session_state.mat_g_delta,  'lam': st.session_state.mat_g_lam},
        'eva':  {'Cp': st.session_state.mat_eva_Cp, 'rho': st.session_state.mat_eva_rho, 'delta': st.session_state.mat_eva_delta, 'lam': st.session_state.mat_eva_lam},
        'pv':   {'Cp': st.session_state.mat_pv_Cp,  'rho': st.session_state.mat_pv_rho,  'delta': st.session_state.mat_pv_delta,  'lam': st.session_state.mat_pv_lam},
        'wall': {'Cp': st.session_state.mat_wall_Cp, 'rho': st.session_state.mat_wall_rho, 'delta': st.session_state.mat_wall_delta, 'lam': st.session_state.mat_wall_lam}
    }

    gap = {
        'd': d_val,
        'H_p': H_p,
        'nu': st.session_state.gap_nu,
        'alpha_air': st.session_state.gap_alpha_air,
        'k_air': st.session_state.gap_k_air
    }

    stc = {
        'Voc_F': st.session_state.Voc_F,
        'Isc_F': st.session_state.Isc_F,
        'Vmp_F': st.session_state.Vmp_F,
        'Imp_F': st.session_state.Imp_F,
        'Pmax_F': st.session_state.Pmax_F,
        'Isc_R': st.session_state.Isc_R,
        'Pmax_R': st.session_state.Pmax_R,
        'alpha_pct': st.session_state.alpha_pct,
        'beta_pct': st.session_state.beta_pct,
        'phi': st.session_state.phi,
        'Ns': st.session_state.Ns
    }

    month_idx = month_names.index(sel_month) + 1
    sel_date = date(2025, month_idx, int(sel_day))
    LCT = hr + mn / 60.0

    # ─── Compute Optical model ──────────────────────────────────────────────────
    sol, vf, extras, GF, GR = compute_irradiance(
        sel_date, LCT, GHI, DHI, latitude, lambda_std, lambda_lcl,
        H_b, h, H_p, d_val, rho_grd, rho_w)

    # ─── Coupled Physics Solver ─────────────────────────────────────────────────
    q = 1.602e-19                   # Electron charge (C)
    K = 1.381e-23                   # Boltzmann constant (J/K)
    E_g = 1.7936e-19                # Band gap energy of Silicon (J)
    T_ref = 298.15                  # STC Reference Temp (25 C in Kelvin)
    G_ref = 1000.0                  # STC Reference Irradiance (W/m2)
    sigma = 5.67e-8                 # Stefan-Boltzmann constant (W/m2K4)

    alpha_abs = (stc['alpha_pct'] / 100.0) * stc['Isc_F']
    beta_abs  = (stc['beta_pct']  / 100.0) * stc['Voc_F']
    T_a = T_a_C + 273.15
    T_room = T_room_C + 273.15

    # Precalculate baseline STC
    try:
        I_ph_ref = stc['Isc_F']
        V_t_ref = (beta_abs * T_ref - stc['Voc_F']) / (stc['Ns'] * T_ref * (alpha_abs / I_ph_ref) - 3 * stc['Ns'] - (E_g * stc['Ns']) / (K * T_ref))
        I_0_ref = stc['Isc_F'] * np.exp(-stc['Voc_F'] / (stc['Ns'] * V_t_ref))

        def solve_Rs_ref_eq(Rs_guess):
            num_Rp = (stc['Vmp_F'] - stc['Imp_F'] * Rs_guess) * (stc['Vmp_F'] - stc['Ns'] * V_t_ref)
            den_Rp = (stc['Vmp_F'] - stc['Imp_F'] * Rs_guess) * (stc['Isc_F'] - stc['Imp_F']) - stc['Ns'] * V_t_ref * stc['Imp_F']
            Rp_substituted = num_Rp / den_Rp
            I_calc = I_ph_ref - I_0_ref * (np.exp((stc['Vmp_F'] + stc['Imp_F'] * Rs_guess) / (stc['Ns'] * V_t_ref)) - 1) - ((stc['Vmp_F'] + stc['Imp_F'] * Rs_guess) / Rp_substituted)
            return I_calc - stc['Imp_F']

        R_s_ref = fsolve(solve_Rs_ref_eq, x0=0.1)[0]
        R_p_ref = ((stc['Vmp_F'] - stc['Imp_F'] * R_s_ref) * (stc['Vmp_F'] - stc['Ns'] * V_t_ref)) / ((stc['Vmp_F'] - stc['Imp_F'] * R_s_ref) * (stc['Isc_F'] - stc['Imp_F']) - stc['Ns'] * V_t_ref * stc['Imp_F'])
    except Exception as ex:
        I_ph_ref = stc['Isc_F']
        V_t_ref = 0.025
        I_0_ref = 1e-9
        R_s_ref = 0.1
        R_p_ref = 100.0

    def run_electrical_model(G_F, G_R, T_PV_K):
        G_E = G_F + G_R * stc['phi']
        if G_E <= 0.01:
            return {
                'P_PV': 0.0, 'G_E': G_E, 'I_ph': 0.0, 'I_0': 0.0, 'R_s': R_s_ref, 'R_p': 1e6, 'V_t': 0.0,
                'V_mp': 0.0, 'I_mp': 0.0
            }

        I_ph = (G_E / G_ref) * (I_ph_ref + alpha_abs * (T_PV_K - T_ref))
        I_0 = I_0_ref * ((T_PV_K / T_ref)**3) * np.exp((E_g / K) * ((1/T_ref) - (1/T_PV_K)))
        R_p = (G_ref / G_E) * R_p_ref
        V_t = (T_PV_K / T_ref) * V_t_ref

        def current_eq_23(I, V):
            return I_ph - I_0 * (np.exp((V + I * R_s_ref) / (stc['Ns'] * V_t)) - 1) - ((V + I * R_s_ref) / R_p) - I

        def find_mpp(V):
            try:
                I_solved = fsolve(current_eq_23, x0=I_ph, args=(V,))[0]
            except:
                I_solved = 0.0
            return -(I_solved * V)

        estimated_Voc = stc['Ns'] * V_t * np.log((I_ph / I_0) + 1)
        if not np.isfinite(estimated_Voc) or estimated_Voc <= 0:
            return {
                'P_PV': 0.0, 'G_E': G_E, 'I_ph': I_ph, 'I_0': I_0, 'R_s': R_s_ref, 'R_p': R_p, 'V_t': V_t,
                'V_mp': 0.0, 'I_mp': 0.0
            }
        result = minimize_scalar(find_mpp, bounds=(0, estimated_Voc), method='bounded')
        P_PV = -result.fun
        V_mp = result.x
        try:
            I_mp = fsolve(current_eq_23, x0=I_ph, args=(V_mp,))[0]
        except:
            I_mp = 0.0

        return {
            'P_PV': P_PV, 'G_E': G_E, 'I_ph': I_ph, 'I_0': I_0, 'R_s': R_s_ref, 'R_p': R_p, 'V_t': V_t,
            'V_mp': V_mp, 'I_mp': I_mp
        }

    # Thermal masses
    M_g = mat['g']['Cp'] * mat['g']['delta'] * mat['g']['rho'] * A
    M_eva = mat['eva']['Cp'] * mat['eva']['delta'] * mat['eva']['rho'] * A
    M_pv = mat['pv']['Cp'] * mat['pv']['delta'] * mat['pv']['rho'] * A
    M_wall = mat['wall']['Cp'] * mat['wall']['delta'] * mat['wall']['rho'] * A

    def R_cond(mat1, mat2):
        return (mat[mat1]['delta'] / (2 * mat[mat1]['lam'] * A)) + (mat[mat2]['delta'] / (2 * mat[mat2]['lam'] * A))

    R_EVA1_g = R_cond('eva', 'g')
    R_PV_EVA1 = R_cond('pv', 'eva')
    R_PV_EVA2 = R_cond('pv', 'eva')
    R_EVA2_rg = R_cond('eva', 'g')
    R_cond_wall = mat['wall']['delta'] / (mat['wall']['lam'] * A)

    def calculate_h_gap(T_rg_K, T_a_K):
        delta_T = T_rg_K - T_a_K
        if delta_T <= 0.01: return gap['k_air'] / gap['d']
        Tf = T_a_K + 0.25 * delta_T
        Ra_b = ((9.81 * (1.0 / Tf) * delta_T * (gap['d'] ** 3)) / (gap['nu'] * gap['alpha_air'])) * (gap['d'] / gap['H_p'])
        Nu_b = ((144.0 / (Ra_b ** 2)) + (2.873 / (Ra_b ** 0.5))) ** (-0.5)
        return (Nu_b * gap['k_air']) / gap['d']

    def run_thermal_model(G_F, G_R, P_PV, T_initial_array):
        def bipv_derivatives(t, T_array):
            T_g, T_eva1, T_pv, T_eva2, T_rg, T_wall = T_array
            T_gap = (T_rg + T_wall) / 2.0
            T_sky = 0.0552 * (T_a ** 1.5)

            h_rad_g = eps_g * sigma * (T_sky**2 + T_g**2) * (T_sky + T_g)
            h_conv_g = 2.8 + 3.0 * u
            h_rad_rg = eps_g * sigma * (T_wall**2 + T_rg**2) * (T_wall + T_rg)
            h_gap_conv = calculate_h_gap(T_rg, T_a)

            R_rad_g, R_conv_g = 1.0 / (h_rad_g * A), 1.0 / (h_conv_g * A)
            R_rad_rg, R_conv_rg = 1.0 / (h_rad_rg * A), 1.0 / (h_gap_conv * A)

            dTg_dt = (alpha_g * G_F * A + (T_eva1 - T_g)/R_EVA1_g - (T_g - T_a)/R_conv_g - (T_g - T_sky)/R_rad_g) / M_g
            dTeva1_dt = ((T_pv - T_eva1)/R_PV_EVA1 - (T_eva1 - T_g)/R_EVA1_g) / M_eva
            dTpv_dt = (((tau_g * (G_F + G_R) * A) - P_PV) - (T_pv - T_eva1)/R_PV_EVA1 - (T_pv - T_eva2)/R_PV_EVA2 )/ M_pv
            dTeva2_dt = ((T_pv - T_eva2)/R_PV_EVA2 - (T_eva2 - T_rg)/R_EVA2_rg) / M_eva
            dTrg_dt = (alpha_g * G_R * A + (T_eva2 - T_rg)/R_EVA2_rg - (T_rg - T_gap)/R_conv_rg - (T_rg - T_wall)/R_rad_rg) / M_g
            dTwall_dt = ((T_rg - T_wall)/R_rad_rg + h_gap_conv * A * (T_gap - T_wall) - (T_wall - T_room)/R_cond_wall) / M_wall

            return [dTg_dt, dTeva1_dt, dTpv_dt, dTeva2_dt, dTrg_dt, dTwall_dt]

        solution = solve_ivp(bipv_derivatives, (0, 3600), T_initial_array, method='RK45')
        return solution.y[:, -1]

    # Coupling Iteration Loop
    T_old_array = [T_a, T_a, T_a, T_a, T_a, T_a]
    T_new_array = list(T_old_array)  # Initialize so it's always defined
    T_PV_old = T_old_array[2]
    error = 100.0
    iteration = 1
    max_iterations = 50
    converged = False

    with st.spinner("Calculating coupled system convergence..."):
        while error > 1e-5 and iteration <= max_iterations:
            elec_out = run_electrical_model(GF, GR, T_PV_old)
            P_PV_calculated = elec_out['P_PV']
            try:
                T_new_array = run_thermal_model(GF, GR, P_PV_calculated, T_old_array)
                T_PV_new = T_new_array[2]
                error = abs(T_PV_new - T_PV_old)
                T_PV_old = T_PV_new
            except Exception as ivp_ex:
                break
            iteration += 1
        if error <= 1e-5:
            converged = True

    elec_final = run_electrical_model(GF, GR, T_PV_old)
    final_temps = T_new_array

    # Final Temperatures in Celsius
    T_wall_c = final_temps[5] - 273.15
    T_gap_c = ((final_temps[4] + final_temps[5]) / 2.0) - 273.15
    T_g_c = final_temps[0] - 273.15
    T_eva1_c = final_temps[1] - 273.15
    T_pv_c = final_temps[2] - 273.15
    T_eva2_c = final_temps[3] - 273.15
    T_rg_c = final_temps[4] - 273.15

    # ─── Main Layout ──────────────────────────────────────────────────────────
    st.markdown('<div class="bipv-header" style="color: #0f766e !important;">Manual Irradiance Tester</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="bipv-sub">{sel_date.strftime("%B %d, %Y")}  •  '
        f'{hr:02d}:{mn:02d} LCT  •  Lat {latitude}°  |  λ_lcl {lambda_lcl}°</div>',
        unsafe_allow_html=True)

    if sol['cos_z'] <= 0:
        st.markdown(
            '<div class="night-warn">🌙 Sun is below the horizon at this time — solar irradiance is zero. Showing thermal model results.</div>',
            unsafe_allow_html=True)

    st.markdown(f"""
    <div class="result-banner">
      <div class="res-item">
        <div class="res-label">Front Irradiance GF</div>
        <div class="res-value">{GF:.1f}<span class="res-unit"> W/m²</span></div>
      </div>
      <div class="res-item" style="border-left:1px solid rgba(255,255,255,0.25);
                                   padding:0 20px;">
        <div class="res-label">Rear Irradiance GR</div>
        <div class="res-value">{GR:.1f}<span class="res-unit"> W/m²</span></div>
      </div>
      <div class="res-item" style="border-left:1px solid rgba(255,255,255,0.25);
                                   padding:0 20px;">
        <div class="res-label">Equivalent Irradiance</div>
        <div class="res-value">{elec_final['G_E']:.1f}<span class="res-unit"> W/m²</span></div>
      </div>
      <div class="res-item" style="border-left:1px solid rgba(255,255,255,0.25);
                                   padding:0 20px;">
        <div class="res-label">Final Module Power</div>
        <div class="res-value">{elec_final['P_PV']:.1f}<span class="res-unit"> W</span></div>
      </div>
      <div class="res-item" style="border-left:1px solid rgba(255,255,255,0.25);
                                   padding:0 20px;">
        <div class="res-label">PV Silicon Temp</div>
        <div class="res-value">{T_pv_c:.1f}<span class="res-unit"> °C</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    def make_table(rows):
        body = "".join(
            f"<tr><td>{n}</td><td>{v} {u}</td></tr>" for n, v, u in rows)
        return (f'<table class="inter-table">'
                f'<thead><tr><th>Parameter</th><th>Value</th></tr></thead>'
                f'<tbody>{body}</tbody></table>')

    if converged:
        st.info(f"✅ Coupled physics system converged in {iteration - 1} iterations.")
    else:
        st.warning(f"⚠️ Physics loop did not converge within {max_iterations} iterations. (Residual: {error:.2e} K)")

    # Two columns for Electrical and Thermal Models
    col_left, col_right = st.columns(2, gap="large")

    with col_left:
        st.markdown('<div class="sec-title">--- ELECTRICAL MODEL ---</div>', unsafe_allow_html=True)
        st.markdown(make_table([
            ("I_ph_ref :", f"{I_ph_ref:.4f}", "A"),
            ("V_t_ref :", f"{V_t_ref:.4f}", "V"),
            ("I_0_ref :", f"{I_0_ref:.4e}", "A"),
            ("R_s_ref :", f"{R_s_ref:.4f}", "Ω"),
            ("R_p_ref :", f"{R_p_ref:.4f}", "Ω")
        ]), unsafe_allow_html=True)
        
        st.markdown('<div class="sec-title">=== PHASE 2: DYNAMIC REAL-WORLD PARAMETERS ===</div>', unsafe_allow_html=True)
        st.markdown(make_table([
            ("Equivalent Irradiance GE:", f"{elec_final['G_E']:.2f}", "W/m²"),
            ("I_ph :", f"{elec_final['I_ph']:.4f}", "A"),
            ("I_0 :", f"{elec_final['I_0']:.4e}", "A"),
            ("R_s :", f"{elec_final['R_s']:.4f}", "Ω"),
            ("R_p :", f"{elec_final['R_p']:.4f}", "Ω"),
            ("V_t :", f"{elec_final['V_t']:.4f}", "V")
        ]), unsafe_allow_html=True)
        
        st.markdown('<div class="sec-title">=== PHASE 3: REAL-WORLD OPERATING MODULE I & V ===</div>', unsafe_allow_html=True)
        st.markdown(make_table([
            ("Module Voltage (V):", f"{elec_final['V_mp']:.2f}", "V"),
            ("Module Current (I):", f"{elec_final['I_mp']:.2f}", "A"),
            ("Final Module Power (P = I * V):", f"{elec_final['P_PV']:.2f}", "W")
        ]), unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="sec-title">--- THERMAL MODEL ---</div>', unsafe_allow_html=True)
        st.markdown('<div class="sec-title">=== FINAL TEMPERATURES ===</div>', unsafe_allow_html=True)
        st.markdown(make_table([
            ("Building Wall (Twall):", f"{T_wall_c:.2f}", "°C"),
            ("Air Gap (Tgap):", f"{T_gap_c:.2f}", "°C"),
            ("Front Glass (Tg):", f"{T_g_c:.2f}", "°C"),
            ("Upper EVA (Teva1):", f"{T_eva1_c:.2f}", "°C"),
            ("PV Silicon (Tpv):", f"{T_pv_c:.2f}", "°C"),
            ("Lower EVA (Teva2):", f"{T_eva2_c:.2f}", "°C"),
            ("Rear Glass (Trg):", f"{T_rg_c:.2f}", "°C")
        ]), unsafe_allow_html=True)
