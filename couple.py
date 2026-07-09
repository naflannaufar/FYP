import math
from datetime import datetime
import numpy as np
from scipy.optimize import fsolve, minimize_scalar
from scipy.integrate import solve_ivp

# =====================================================================
# =====================================================================
# 1. THE CONTROL CENTER (ALL INPUTS)
# =====================================================================
# =====================================================================

# --- A. TIME & WEATHER INPUTS (Outer Loop Drivers) ---
date_str = "2025-12-12"         # Date
time_str = "12:00"              # Time (LCT)
GHI = 800                     # Global Horizontal Irradiance (W/m2)
DHI = 100                     # Diffuse Horizontal Irradiance (W/m2)
T_a_C = 25.0                    # Ambient Air Temp (Celsius)
u = 2.0                         # Wind speed (m/s)

# --- B. OPTICAL & INSTALLATION INPUTS ---
latitude = 33.7                # Latitude (φ, degrees)
lambda_std = 75.0              # Standard Longitude (λstd, degrees)
lambda_lcl = 72.84             # Local Longitude (λlcl, degrees)
H_b = 10.0                      # Building Height (Hb, meters)
h = 5                     # Height from ground to panel's bottom edge (h, meters)
H_p = 2.0                       # Height of the vertical panel (Hp, meters)
d = 0.2                         # Horizontal distance between panel and wall (d, meters)
rho_grd = 0.3                   # Ground Albedo (ρ_grd, 0-1)
rho_w = 0.3                     # Wall Albedo (ρ_w, 0-1)
tilt_angle = 90.0               # Fixed for vertical BIPV
panel_azimuth = 0.0             # 0 = South

# --- C. ELECTRICAL DATASHEET INPUTS (STC) ---
stc = {
    'Voc_F': 44.5,              # Open-Circuit Voltage, Front (V)
    'Isc_F': 9.96,              # Short-Circuit Current, Front (A)
    'Vmp_F': 37.9,              # Maximum Power Voltage, Front (V)
    'Imp_F': 9.38,              # Maximum Power Current, Front (A)
    'Pmax_F': 355.0,            # Maximum Power, Front (W)
    'Isc_R': 8.53,              # Short-Circuit Current, Rear (A)
    'Pmax_R': 302.0,            # Maximum Power, Rear (W)
    'alpha_pct': 0.048,         # Temp coefficient of Isc (%/C)
    'beta_pct': -0.30,          # Temp coefficient of Voc (%/C)
    'phi': 0.75,                # Bifaciality Factor (phi)
    'Ns': 72                    # Number of cells in series
}

# --- D. THERMAL & MATERIAL INPUTS ---
A = 2.0                         # Panel Area (m2)
T_room_C = 22.0                 # Indoor room temp (Celsius)
alpha_g = 0.05                  # Absorptance of glass
tau_g = 0.90                    # Transmittance of front glass
tau_rg = 0.90                   # Transmittance of rear glass
eps_g = 0.85                    # Emissivity of glass

mat = {
    'g':    {'Cp': 800,  'rho': 2500, 'delta': 0.0032, 'lam': 1.8},     # Glass
    'eva':  {'Cp': 2090, 'rho': 960,  'delta': 0.0005, 'lam': 0.31},    # EVA
    'pv':   {'Cp': 677,  'rho': 2330, 'delta': 0.0002, 'lam': 148},     # Silicon Cell
    'wall': {'Cp': 880,  'rho': 2400, 'delta': 0.2000, 'lam': 1.5}      # Concrete Wall
}

gap = {
    'd': d,                     # Linked to Optical input
    'H_p': H_p,                 # Linked to Optical input
    'nu': 1.56e-5,              # Kinematic viscosity of air (m2/s)
    'alpha_air': 2.21e-5,        # Thermal diffusivity of air (m2/s)
    'k_air': 0.0261              # Thermal conductivity of air (W/mK)
}

# --- E. FUNDAMENTAL CONSTANTS ---
q = 1.602e-19                   # Electron charge (C)
K = 1.381e-23                   # Boltzmann constant (J/K)
E_g = 1.7936e-19                # Band gap energy of Silicon (J)
T_ref = 298.15                  # STC Reference Temp (25 C in Kelvin)
G_ref = 1000.0                  # STC Reference Irradiance (W/m2)
sigma = 5.67e-8                 # Stefan-Boltzmann constant (W/m2K4)
DEG_TO_RAD = math.pi / 180.0
RAD_TO_DEG = 180.0 / math.pi

# Conversions & Pre-calculations
alpha_abs = (stc['alpha_pct'] / 100.0) * stc['Isc_F']
beta_abs  = (stc['beta_pct']  / 100.0) * stc['Voc_F']
T_a = T_a_C + 273.15
T_room = T_room_C + 273.15
date_obj = datetime.strptime(date_str, "%Y-%m-%d")
h_time, m_time = map(int, time_str.split(':'))
LCT = h_time + m_time / 60.0


# =====================================================================
# 2. OPTICAL MODEL FUNCTION
# =====================================================================
def run_optical_model(verbose=False):
    def _deg_to_rad(angle_deg): return angle_deg * DEG_TO_RAD
    def _rad_to_deg(angle_rad): return angle_rad * RAD_TO_DEG

    n = date_obj.timetuple().tm_yday
    delta_deg = 23.45 * math.sin(_deg_to_rad(360.0 * (284 + n) / 365.0))
    B_rad = _deg_to_rad(360.0 * (n - 1) / 365.0)

    EoT = 229.2 * (0.000075 + 0.001868 * math.cos(B_rad) - 0.032077 * math.sin(B_rad)
                   - 0.014615 * math.cos(2 * B_rad) - 0.04089 * math.sin(2 * B_rad))

    LST = LCT + (4.0 * (lambda_std - lambda_lcl) + EoT) / 60.0
    omega_deg = 15.0 * (LST - 12.0)

    phi_rad, delta_rad, omega_rad = map(_deg_to_rad, [latitude, delta_deg, omega_deg])
    cos_z = max(-1.0, min(1.0, math.sin(phi_rad) * math.sin(delta_rad) + math.cos(phi_rad) * math.cos(delta_rad) * math.cos(omega_rad)))
    theta_z = _rad_to_deg(math.acos(cos_z))
    alpha_s = 90.0 - theta_z

    if cos_z <= 0: return 0.0, 0.0  # Nighttime

    # Angle of Incidence Front
    d_r, p_r, b_r, g_r, w_r = map(_deg_to_rad, [delta_deg, latitude, tilt_angle, panel_azimuth, omega_deg])
    cos_theta_F = max(-1.0, min(1.0, (math.sin(d_r)*math.sin(p_r)*math.cos(b_r)) - (math.sin(d_r)*math.cos(p_r)*math.sin(b_r)*math.cos(g_r)) + (math.cos(d_r)*math.cos(p_r)*math.cos(b_r)*math.cos(w_r)) + (math.cos(d_r)*math.sin(p_r)*math.sin(b_r)*math.cos(g_r)*math.cos(w_r)) + (math.cos(d_r)*math.sin(b_r)*math.sin(g_r)*math.sin(w_r))))

    RbF = max(0.0, cos_theta_F) / cos_z if (panel_azimuth - 90) <= omega_deg <= (panel_azimuth + 90) else 0.0

    # View Factors
    L = H_b - H_p - h
    XF_sky, XF_grd = 0.5, 0.5
    XR_sky = (H_p + math.sqrt(d**2 + L**2) - math.sqrt(d**2 + (H_p + L)**2)) / (2 * H_p)
    XR_grd = (H_p + math.sqrt(d**2 + h**2) - math.sqrt(d**2 + (H_p + h)**2)) / (2 * H_p)

    Delta = d * math.tan(_deg_to_rad(alpha_s)) if 0 < alpha_s < 90 else (1e6 if alpha_s >= 90 else 0.0)
    XR_sh_w = max(0.0, min(1.0, (math.sqrt(d**2 + (H_p - Delta)**2) + math.sqrt(d**2 + (H_p + Delta)**2) - 2 * math.sqrt(d**2 + Delta**2)) / (2 * H_p)))
    XR_ush_w = max(0.0, 1.0 - XR_sky - XR_grd - XR_sh_w)

    BHI = GHI - DHI
    GF = (BHI * RbF) + (DHI * XF_sky) + (GHI * rho_grd * XF_grd)
    GR = (DHI * XR_sky) + (GHI * rho_grd * XR_grd) + (((DHI / 2.0) + (GHI * rho_grd / 2.0)) * rho_w * XR_sh_w) + (GF * rho_w * XR_ush_w)

    if verbose:
        print(f"\n--- OPTICAL MODEL ---")
        print(f"Front Irradiance (G_F): {GF:.2f} W/m2")
        print(f"Rear Irradiance (G_R):  {GR:.2f} W/m2")

    return GF, GR


# =====================================================================
# 3. ELECTRICAL PRE-COMPUTATION (STC Baseline)
# =====================================================================
# Calculated ONCE before loops to save processing time
I_ph_ref = stc['Isc_F']
V_t_ref = (beta_abs * T_ref - stc['Voc_F']) / (stc['Ns'] * T_ref * (alpha_abs / I_ph_ref) - 3 * stc['Ns'] - (E_g * stc['Ns']) / (K * T_ref))
I_0_ref = stc['Isc_F'] * np.exp(-stc['Voc_F'] / (stc['Ns'] * V_t_ref))

def solve_Rs_ref(Rs_guess):
    num_Rp = (stc['Vmp_F'] - stc['Imp_F'] * Rs_guess) * (stc['Vmp_F'] - stc['Ns'] * V_t_ref)
    den_Rp = (stc['Vmp_F'] - stc['Imp_F'] * Rs_guess) * (stc['Isc_F'] - stc['Imp_F']) - stc['Ns'] * V_t_ref * stc['Imp_F']
    Rp_substituted = num_Rp / den_Rp
    I_calc = I_ph_ref - I_0_ref * (np.exp((stc['Vmp_F'] + stc['Imp_F'] * Rs_guess) / (stc['Ns'] * V_t_ref)) - 1) - ((stc['Vmp_F'] + stc['Imp_F'] * Rs_guess) / Rp_substituted)
    return I_calc - stc['Imp_F']

R_s_ref = fsolve(solve_Rs_ref, x0=0.1)[0]
R_p_ref = ((stc['Vmp_F'] - stc['Imp_F'] * R_s_ref) * (stc['Vmp_F'] - stc['Ns'] * V_t_ref)) / ((stc['Vmp_F'] - stc['Imp_F'] * R_s_ref) * (stc['Isc_F'] - stc['Imp_F']) - stc['Ns'] * V_t_ref * stc['Imp_F'])


# =====================================================================
# 4. ELECTRICAL MODEL FUNCTION
# =====================================================================
def run_electrical_model(G_F, G_R, T_PV_K, verbose=False):
    G_E = G_F + G_R * stc['phi']

    if G_E <= 0.01: # Nighttime Bypass
        if verbose: print("--- ELECTRICAL MODEL (NIGHT) ---\nPower = 0.0 W")
        return 0.0

    I_ph = (G_E / G_ref) * (I_ph_ref + alpha_abs * (T_PV_K - T_ref))
    I_0 = I_0_ref * ((T_PV_K / T_ref)**3) * np.exp((E_g / K ) * ((1/T_ref) - (1/T_PV_K)))
    R_p = (G_ref / G_E) * R_p_ref
    V_t = (T_PV_K / T_ref) * V_t_ref

    def current_eq_23(I, V):
        return I_ph - I_0 * (np.exp((V + I * R_s_ref) / (stc['Ns'] * V_t)) - 1) - ((V + I * R_s_ref) / R_p) - I

    def find_mpp(V):
        I_solved = fsolve(current_eq_23, x0=I_ph, args=(V,))[0]
        return -(I_solved * V)

    estimated_Voc = stc['Ns'] * V_t * np.log((I_ph / I_0) + 1)
    result = minimize_scalar(find_mpp, bounds=(0, estimated_Voc), method='bounded')
    P_PV = -result.fun

    if verbose:
        print(f"\n--- ELECTRICAL MODEL ---")
        print(f"I_ph_ref : {I_ph_ref:.4f} A")
        print(f"V_t_ref : {V_t_ref:.4f} V")
        print(f"I_0_ref : {I_0_ref:.4e} A")
        print(f"R_s_ref : {R_s_ref:.4f} Ohms")
        print(f"R_p_ref : {R_p_ref:.4f} Ohms")
        print(f"=== PHASE 2: DYNAMIC REAL-WORLD PARAMETERS ===")
        print(f"Equivalent Irradiance: {G_E:.2f} W/m2")
        print(f"I_ph : {I_ph:.4f} A")
        print(f"I_0 : {I_0:.4e} A")
        print(f"R_s : {R_s_ref:.4f} Ohms") # R_s is R_s_ref
        print(f"R_p : {R_p:.4f} Ohms")
        print(f"V_t : {V_t:.4f} V")
        print(f"=== PHASE 3: REAL-WORLD OPERATING MODULE I & V ===")
        print(f"Module Voltage (V): {result.x:.2f} V")
        print(f"Module Current (I): {-(result.fun / result.x):.2f} A")
        print(f"Final Module Power (P = I * V): {P_PV:.2f} W")

    return P_PV


# =====================================================================
# 5. THERMAL MODEL FUNCTION
# =====================================================================
# Pre-calculate Thermal Masses and Internal Resistances
M_g = mat['g']['Cp'] * mat['g']['delta'] * mat['g']['rho'] * A
M_eva = mat['eva']['Cp'] * mat['eva']['delta'] * mat['eva']['rho'] * A
M_pv = mat['pv']['Cp'] * mat['pv']['delta'] * mat['pv']['rho'] * A
M_wall = mat['wall']['Cp'] * mat['wall']['delta'] * mat['wall']['rho'] * A

def R_cond(mat1, mat2): return (mat[mat1]['delta'] / (2 * mat[mat1]['lam'] * A)) + (mat[mat2]['delta'] / (2 * mat[mat2]['lam'] * A))
R_EVA1_g, R_PV_EVA1, R_PV_EVA2, R_EVA2_rg = R_cond('eva', 'g'), R_cond('pv', 'eva'), R_cond('pv', 'eva'), R_cond('eva', 'g')
R_cond_wall = mat['wall']['delta'] / (mat['wall']['lam'] * A)

def calculate_h_gap(T_rg_K, T_a_K):
    delta_T = T_rg_K - T_a_K
    if delta_T <= 0.01: return gap['k_air'] / gap['d']
    Tf = T_a_K + 0.25 * delta_T
    Ra_b = ((9.81 * (1.0 / Tf) * delta_T * (gap['d'] ** 3)) / (gap['nu'] * gap['alpha_air'])) * (gap['d'] / gap['H_p'])
    Nu_b = ((144.0 / (Ra_b ** 2)) + (2.873 / (Ra_b ** 0.5))) ** (-0.5)
    return (Nu_b * gap['k_air']) / gap['d']

def run_thermal_model(G_F, G_R, P_PV, T_initial_array, verbose=False):

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
    final_temps = solution.y[:, -1]

    if verbose:
        # Calculate T_gap explicitly for verbose output
        T_gap_c = (final_temps[4] + final_temps[5]) / 2.0

        print(f"\n--- THERMAL MODEL ---")
        print(f"=== FINAL TEMPERATURES ===")
        print(f"Building Wall (Twall): {final_temps[5] - 273.15:.2f} °C")
        print(f"Air Gap (Tgap): {T_gap_c - 273.15:.2f} °C")
        print(f"Front Glass (Tg): {final_temps[0] - 273.15:.2f} °C")
        print(f"Upper EVA (Teva1): {final_temps[1] - 273.15:.2f} °C")
        print(f"PV Silicon (Tpv): {final_temps[2] - 273.15:.2f} °C")
        print(f"Lower EVA (Teva2): {final_temps[3] - 273.15:.2f} °C")
        print(f"Rear Glass (Trg): {final_temps[4] - 273.15:.2f} °C")

    return final_temps


# =====================================================================
# 6. THE MASTER COUPLING LOOP (Figure 7 Implementation)
# =====================================================================
if __name__ == '__main__':
    print("="*50)
    print("STARTING O-E-T COUPLED SIMULATION")
    print("="*50)

    # Step 1: Run Optical Model (Independent Driver)
    G_F, G_R = run_optical_model(verbose=True)

    # Step 2: The Initial Guess
    # Assume the entire panel is sitting at ambient temperature
    T_old_array = [T_a, T_a, T_a, T_a, T_a, T_a]
    T_PV_old = T_old_array[2]

    error = 100.0
    iteration = 1

    print("\n[STARTING ITERATION LOOP]")

    # Step 3: The Physics Standoff (The "Converge?" Diamond)
    while error > 1e-5:
        print(f" Iteration {iteration} | Testing Cell Temp: {T_PV_old - 273.15:.4f} °C...")

        # A. Electrical model calculates Power using the guessed Temp
        P_PV_calculated = run_electrical_model(G_F, G_R, T_PV_old, verbose=False)

        # B. Thermal model calculates New Temp using the calculated Power
        T_new_array = run_thermal_model(G_F, G_R, P_PV_calculated, T_old_array, verbose=False)
        T_PV_new = T_new_array[2]

        # C. Calculate Error
        error = abs(T_PV_new - T_PV_old)

        # D. Update the guess for the next loop
        T_PV_old = T_PV_new
        iteration += 1

        # Failsafe
        if iteration > 50:
            print("WARNING: Failed to converge after 50 iterations.")
            break

    # Step 4: Convergence Achieved! Run once more with 'verbose=True' to print final stats
    print("\n" + "="*50)
    print(" ✅ CONVERGED! PHYSICS ARE BALANCED.")
    print("="*50)
    final_power = run_electrical_model(G_F, G_R, T_PV_new, verbose=True)
    final_temps = run_thermal_model(G_F, G_R, final_power, T_old_array, verbose=True)