import math
import streamlit as st
from datetime import date
import calendar
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from scipy.optimize import fsolve, minimize_scalar
from scipy.integrate import solve_ivp


DEG_TO_RAD = math.pi / 180.0
RAD_TO_DEG = 180.0 / math.pi

def d2r(a):
    return a * DEG_TO_RAD

def r2d(a):
    return a * RAD_TO_DEG

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

@st.cache_data
def calculate_daily_bipv_physics(
    month_idx, sel_day, latitude, lambda_std, lambda_lcl, H_b, h, H_p, d_val, rho_grd, rho_w,
    A, T_room_C, alpha_g, tau_g, tau_rg, eps_g,
    mat_g_Cp, mat_g_rho, mat_g_delta, mat_g_lam,
    mat_eva_Cp, mat_eva_rho, mat_eva_delta, mat_eva_lam,
    mat_pv_Cp, mat_pv_rho, mat_pv_delta, mat_pv_lam,
    mat_wall_Cp, mat_wall_rho, mat_wall_delta, mat_wall_lam,
    gap_nu, gap_alpha_air, gap_k_air,
    Voc_F, Isc_F, Vmp_F, Imp_F, Pmax_F, Isc_R, Pmax_R, alpha_pct, beta_pct, phi, Ns
):
    df_irr = pd.read_csv("Taxila_Irradiance_Data.csv")
    df_day = df_irr[(df_irr['Month'] == month_idx) & (df_irr['Day'] == int(sel_day))]
    if df_day.empty:
        return [], [], [], [], [], [], [], []
    df_day = df_day.sort_values(by='Hour Taxila')

    stc = {
        'Voc_F': Voc_F, 'Isc_F': Isc_F, 'Vmp_F': Vmp_F, 'Imp_F': Imp_F, 'Pmax_F': Pmax_F,
        'Isc_R': Isc_R, 'Pmax_R': Pmax_R, 'alpha_pct': alpha_pct, 'beta_pct': beta_pct, 'phi': phi, 'Ns': Ns
    }
    mat = {
        'g':    {'Cp': mat_g_Cp,  'rho': mat_g_rho,  'delta': mat_g_delta,  'lam': mat_g_lam},
        'eva':  {'Cp': mat_eva_Cp, 'rho': mat_eva_rho, 'delta': mat_eva_delta, 'lam': mat_eva_lam},
        'pv':   {'Cp': mat_pv_Cp,  'rho': mat_pv_rho,  'delta': mat_pv_delta,  'lam': mat_pv_lam},
        'wall': {'Cp': mat_wall_Cp, 'rho': mat_wall_rho, 'delta': mat_wall_delta, 'lam': mat_wall_lam}
    }
    gap = {
        'd': d_val, 'H_p': H_p, 'nu': gap_nu, 'alpha_air': gap_alpha_air, 'k_air': gap_k_air
    }

    # Precalculate baseline STC
    q = 1.602e-19
    K = 1.381e-23
    E_g = 1.7936e-19
    T_ref = 298.15
    G_ref = 1000.0
    sigma = 5.67e-8

    alpha_abs = (stc['alpha_pct'] / 100.0) * stc['Isc_F']
    beta_abs  = (stc['beta_pct']  / 100.0) * stc['Voc_F']

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

    def run_thermal_model(G_F, G_R, P_PV, T_initial_array, T_a, u, T_room):
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

        # Radau solver handles stiff equations extremely fast
        solution = solve_ivp(bipv_derivatives, (0, 3600), T_initial_array, method='Radau')
        return solution.y[:, -1]

    sel_date_lcl = date(2025, month_idx, int(sel_day))
    hours, ghi_list, dhi_list, gf_list, gr_list, gt_list = [], [], [], [], [], []
    tpv_list, power_list = [], []

    for _, row in df_day.iterrows():
        h_taxila = row['Hour Taxila']
        g_h  = row['G(h)']
        gd_h = row['Gd(h)']
        
        # 1. Optical calculations
        _, _, _, curr_gf, curr_gr = compute_irradiance(
            sel_date_lcl, h_taxila, g_h, gd_h, latitude, lambda_std, lambda_lcl,
            H_b, h, H_p, d_val, rho_grd, rho_w)
        
        # 2. Weather conditions from CSV for this hour
        curr_T_a_C = row['T2m']
        curr_T_a = curr_T_a_C + 273.15
        curr_u = row['WS10m']
        curr_T_room = T_room_C + 273.15
        
        # 3. Coupled physical solver loop (resetting state to ambient each hour)
        T_old_array = [curr_T_a, curr_T_a, curr_T_a, curr_T_a, curr_T_a, curr_T_a]
        T_PV_old = T_old_array[2]
        
        error = 100.0
        iteration = 1
        max_iterations = 50
        
        while error > 1e-3 and iteration <= max_iterations:
            elec_out = run_electrical_model(curr_gf, curr_gr, T_PV_old)
            P_PV_calculated = elec_out['P_PV']
            try:
                T_new_array = run_thermal_model(curr_gf, curr_gr, P_PV_calculated, T_old_array, curr_T_a, curr_u, curr_T_room)
                T_PV_new = T_new_array[2]
                error = abs(T_PV_new - T_PV_old)
                T_PV_old = T_PV_new
            except Exception as ivp_ex:
                break
            iteration += 1
        
        elec_final = run_electrical_model(curr_gf, curr_gr, T_PV_old)
        
        hours.append(int(h_taxila))
        ghi_list.append(round(g_h,   2))
        dhi_list.append(round(gd_h,  2))
        gf_list.append(round(curr_gf, 2))
        gr_list.append(round(curr_gr, 2))
        gt_list.append(round(curr_gf + curr_gr, 2))
        
        # Store temperature and power outputs
        tpv_list.append(round(T_PV_old - 273.15, 2))
        power_list.append(round(elec_final['P_PV'], 2))

    return hours, ghi_list, dhi_list, gf_list, gr_list, gt_list, tpv_list, power_list

def show():
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
        # Initialize session state defaults if not present
        if "active_tab" not in st.session_state:
            st.session_state.active_tab = "Optical"

        # Version key: bump this to force-reset defaults when they change
        _DEFAULTS_VERSION = 5
        defaults = {
            # Optical
            'sel_month': 'June',
            'sel_day': 21,
            'hr': 12,
            'mn': 0,
            'GHI': 600.0,
            'DHI': 100.0,
            'latitude': 33.7,
            'lambda_std': 75.0,
            'lambda_lcl': 72.84,
            'H_b': 20.0,
            'h': 12.5,
            'H_p': 1.88,
            'd_val': 0.2,
            'rho_grd': 0.28,
            'rho_w': 0.35,
            
            # Thermal general
            'A': 2.0,
            'T_room_C': 22.0,
            'alpha_g': 0.05,
            'tau_g': 0.90,
            'tau_rg': 0.90,
            'eps_g': 0.85,
            'T_a_C': 25.0,
            'u': 2.0,
            
            # Thermal materials
            'mat_g_Cp': 800.0, 'mat_g_rho': 2500.0, 'mat_g_delta': 0.0032, 'mat_g_lam': 1.8,
            'mat_eva_Cp': 2090.0, 'mat_eva_rho': 960.0, 'mat_eva_delta': 0.0005, 'mat_eva_lam': 0.31,
            'mat_pv_Cp': 677.0, 'mat_pv_rho': 2330.0, 'mat_pv_delta': 0.0002, 'mat_pv_lam': 148.0,
            'mat_wall_Cp': 880.0, 'mat_wall_rho': 2400.0, 'mat_wall_delta': 0.2000, 'mat_wall_lam': 1.5,
            
            # Thermal gap
            'gap_nu': 1.56e-5,
            'gap_alpha_air': 2.21e-5,
            'gap_k_air': 0.0261,
            
            # Electrical STC
            'Voc_F': 44.5,
            'Isc_F': 9.96,
            'Vmp_F': 37.9,
            'Imp_F': 9.38,
            'Pmax_F': 355.0,
            'Isc_R': 8.53,
            'Pmax_R': 302.0,
            'alpha_pct': 0.048,
            'beta_pct': -0.30,
            'phi': 0.75,
            'Ns': 72
        }

        # Force-reset all defaults if version changed
        if st.session_state.get('_defaults_version') != _DEFAULTS_VERSION:
            for k, v in defaults.items():
                st.session_state[k] = v
            st.session_state['_defaults_version'] = _DEFAULTS_VERSION
        else:
            for k, v in defaults.items():
                if k not in st.session_state:
                    st.session_state[k] = v

        st.markdown('<div class="section-label">① Date</div>', unsafe_allow_html=True)
        month_names = list(calendar.month_name)[1:]
        col_m, col_d = st.columns(2)
        with col_m:
            st.selectbox("Month", month_names, key='sel_month')
        month_idx = month_names.index(st.session_state.sel_month) + 1
        max_day = calendar.monthrange(2025, month_idx)[1]
        with col_d:
            st.number_input("Day", min_value=1, max_value=max_day, value=int(st.session_state['sel_day']), key='sel_day')
        sel_date = date(2025, month_idx, int(st.session_state.sel_day))

        st.markdown('<div class="section-label">🔧 Parameter Select</div>', unsafe_allow_html=True)
        tab_opt, tab_ther, tab_elec = st.tabs(["Optical", "Thermal", "Electrical"])

        with tab_opt:
            st.markdown('<div class="section-label">① Location</div>', unsafe_allow_html=True)
            st.number_input("Latitude φ (°)", -90.0, 90.0, value=st.session_state['latitude'], key='latitude')
            st.number_input("Standard Longitude λstd (°)", -180.0, 180.0, value=st.session_state['lambda_std'], key='lambda_std')
            st.number_input("Local Longitude λlcl (°)", -180.0, 180.0, value=st.session_state['lambda_lcl'], key='lambda_lcl')
            
            st.markdown('<div class="section-label">② Building Geometry (m)</div>', unsafe_allow_html=True)
            st.number_input("Building Height Hb", 0.5, 200.0, value=st.session_state['H_b'], key='H_b')
            st.number_input("Panel Bottom Edge h", 0.0, 100.0, value=st.session_state['h'], key='h')
            st.number_input("Panel Height Hp", 0.1, 50.0, value=st.session_state['H_p'], key='H_p')
            st.number_input("Panel-to-Wall Distance d", 0.01, 20.0, value=st.session_state['d_val'], key='d_val')
            
            st.markdown('<div class="section-label">③ Albedo</div>', unsafe_allow_html=True)
            st.number_input("Ground Albedo ρ_grd", 0.0, 1.0, value=st.session_state['rho_grd'], key='rho_grd')
            st.number_input("Wall Albedo ρ_w", 0.0, 1.0, value=st.session_state['rho_w'], key='rho_w')

        with tab_ther:
            st.markdown('<div class="section-label">① Environment & Area</div>', unsafe_allow_html=True)
            st.number_input("Panel Area A (m²)", 0.1, 100.0, value=st.session_state['A'], key='A')
            st.number_input("Indoor Room Temp (°C)", -50.0, 100.0, value=st.session_state['T_room_C'], key='T_room_C')
            
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

    # ── Load & compute data ────────────────────────────────────────────────────
    # Load state variables for calculations
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

    # Reconstruct variables for cache key
    mat_g_Cp = st.session_state.mat_g_Cp
    mat_g_rho = st.session_state.mat_g_rho
    mat_g_delta = st.session_state.mat_g_delta
    mat_g_lam = st.session_state.mat_g_lam
    mat_eva_Cp = st.session_state.mat_eva_Cp
    mat_eva_rho = st.session_state.mat_eva_rho
    mat_eva_delta = st.session_state.mat_eva_delta
    mat_eva_lam = st.session_state.mat_eva_lam
    mat_pv_Cp = st.session_state.mat_pv_Cp
    mat_pv_rho = st.session_state.mat_pv_rho
    mat_pv_delta = st.session_state.mat_pv_delta
    mat_pv_lam = st.session_state.mat_pv_lam
    mat_wall_Cp = st.session_state.mat_wall_Cp
    mat_wall_rho = st.session_state.mat_wall_rho
    mat_wall_delta = st.session_state.mat_wall_delta
    mat_wall_lam = st.session_state.mat_wall_lam

    gap_nu = st.session_state.gap_nu
    gap_alpha_air = st.session_state.gap_alpha_air
    gap_k_air = st.session_state.gap_k_air

    Voc_F = st.session_state.Voc_F
    Isc_F = st.session_state.Isc_F
    Vmp_F = st.session_state.Vmp_F
    Imp_F = st.session_state.Imp_F
    Pmax_F = st.session_state.Pmax_F
    Isc_R = st.session_state.Isc_R
    Pmax_R = st.session_state.Pmax_R
    alpha_pct = st.session_state.alpha_pct
    beta_pct = st.session_state.beta_pct
    phi = st.session_state.phi
    Ns = st.session_state.Ns

    sel_day = int(st.session_state.sel_day)
    sel_date = date(2025, month_idx, sel_day)

    # Execute cached function (module-level)
    hours, ghi_list, dhi_list, gf_list, gr_list, gt_list, tpv_list, power_list = calculate_daily_bipv_physics(
        month_idx, sel_day, latitude, lambda_std, lambda_lcl, H_b, h, H_p, d_val, rho_grd, rho_w,
        A, T_room_C, alpha_g, tau_g, tau_rg, eps_g,
        mat_g_Cp, mat_g_rho, mat_g_delta, mat_g_lam,
        mat_eva_Cp, mat_eva_rho, mat_eva_delta, mat_eva_lam,
        mat_pv_Cp, mat_pv_rho, mat_pv_delta, mat_pv_lam,
        mat_wall_Cp, mat_wall_rho, mat_wall_delta, mat_wall_lam,
        gap_nu, gap_alpha_air, gap_k_air,
        Voc_F, Isc_F, Vmp_F, Imp_F, Pmax_F, Isc_R, Pmax_R, alpha_pct, beta_pct, phi, Ns
    )

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

    if len(hours) == 0:
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
        height=320,
        margin=dict(l=40, r=20, t=10, b=40),
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

    # ── Graph 2: PV Silicon Temperature ──
    st.markdown('<div class="tx-sec">Hourly PV Silicon Temperature Profile</div>', unsafe_allow_html=True)
    fig_temp = go.Figure()
    fig_temp.add_trace(go.Scatter(x=hours, y=tpv_list, mode='lines+markers', name='PV Temp (Tpv)',
                                 line=dict(color='#dc2626', width=2.5), marker=dict(size=5)))
    fig_temp.update_layout(
        height=320,
        margin=dict(l=40, r=20, t=10, b=40),
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
            title=dict(text='Temperature (°C)', font=dict(size=12, color='#374151')),
            showgrid=True, gridwidth=1, gridcolor='#e2e8f0',
            tickfont=dict(size=10, color='#6b7280'), zeroline=False)
    )
    st.plotly_chart(fig_temp, use_container_width=True)

    # ── Graph 3: Module Power Output ──
    st.markdown('<div class="tx-sec">Hourly Module Power Output Profile</div>', unsafe_allow_html=True)
    fig_power = go.Figure()
    fig_power.add_trace(go.Scatter(x=hours, y=power_list, mode='lines+markers', name='Module Power (P_PV)',
                                  line=dict(color='#16a34a', width=2.5), marker=dict(size=5)))
    fig_power.update_layout(
        height=320,
        margin=dict(l=40, r=20, t=10, b=40),
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
            title=dict(text='Power (W)', font=dict(size=12, color='#374151')),
            showgrid=True, gridwidth=1, gridcolor='#e2e8f0',
            tickfont=dict(size=10, color='#6b7280'), zeroline=False)
    )
    st.plotly_chart(fig_power, use_container_width=True)

    # ── Table below graph (full width, transposed) ────────────────────────────
    st.markdown('<div class="tx-sec">Hourly Irradiance & BIPV Data Table</div>', unsafe_allow_html=True)

    # Build hour → values mapping
    hour_data = {}
    for i, hv in enumerate(hours):
        hour_data[hv] = {
            'GHI': ghi_list[i], 'DHI': dhi_list[i],
            'GF': gf_list[i], 'GR': gr_list[i], 'GT': gt_list[i],
            'Tpv': tpv_list[i], 'Power': power_list[i]
        }

    # Transposed Table Rendering
    # Headers: Parameter | 00:00 | 01:00 | ... | 23:00
    hour_headers = "".join(f"<th>{h:02d}:00</th>" for h in range(24))
    header_html = f"<thead><tr><th>Parameter</th>{hour_headers}</tr></thead>"

    params = ['GHI', 'DHI', 'GF', 'GR', 'GT', 'Tpv', 'Power']
    param_names = {
        'GHI': 'GHI (W/m²)',
        'DHI': 'DHI (W/m²)',
        'GF': 'GF (W/m²)',
        'GR': 'GR (W/m²)',
        'GT': 'GT (W/m²)',
        'Tpv': 'PV Temp (°C)',
        'Power': 'Power (W)'
    }
    param_styles = {
        'GHI': 'color:#1e3a8a;',
        'DHI': 'color:#ea580c;font-weight:700;',
        'GF':  'color:#0f766e;font-weight:600;',
        'GR':  'color:#7c3aed;font-weight:600;',
        'GT':  'color:#545454;',
        'Tpv': 'color:#dc2626;font-weight:600;',
        'Power': 'color:#16a34a;font-weight:700;'
    }

    body_html = "<tbody>"
    for p in params:
        cells = []
        for h in range(24):
            val = hour_data.get(h, {}).get(p, 0.0)
            if p in ['Tpv', 'Power']:
                fmt_val = "0" if val == 0 else f"{val:.2f}"
            else:
                fmt_val = "0" if val == 0 else f"{val:.1f}"
            cells.append(f"<td style='{param_styles[p]}'>{fmt_val}</td>")
        body_html += f"<tr><td style='{param_styles[p]}'>{param_names[p]}</td>{''.join(cells)}</tr>"
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
