import math
from datetime import datetime

# --- Constants ---
DEG_TO_RAD = math.pi / 180.0
RAD_TO_DEG = 180.0 / math.pi

def _deg_to_rad(angle_deg: float) -> float: return angle_deg * DEG_TO_RAD
def _rad_to_deg(angle_rad: float) -> float: return angle_rad * RAD_TO_DEG

# --- 1. Input Handling ---
def get_user_inputs() -> dict:
    """Prompts the user for all necessary inputs and returns a validated dictionary."""

    print("\n--- Input Parameters for Vertical BIPV Irradiance Calculation ---")

    # 1. Date
    while True:
        try:
            date_str = input("1. Enter Date (YYYY-MM-DD, e.g., 2025-12-12): ")
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            break
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")

    # 2. Time (LCT)
    while True:
        try:
            time_str = input("2. Enter Time (HH:MM in 24-hour format, e.g., 14:30): ")
            h_time, m_time = map(int, time_str.split(':'))
            if not (0 <= h_time <= 23 and 0 <= m_time <= 59):
                 raise ValueError("Hour must be 0-23, Minute 0-59.")
            LCT = h_time + m_time / 60.0
            break
        except Exception:
            print("Invalid time format or value. Please use HH:MM.")

    # 3-13. Numeric Inputs
    GHI = float(input("3. Enter Global Horizontal Irradiance (GHI, W/m²): "))
    DHI = float(input("4. Enter Diffuse Horizontal Irradiance (DHI, W/m²): "))
    latitude = float(input("5. Enter Latitude (φ, degrees, -90 to +90): "))
    lambda_std = float(input("6. Enter Standard Longitude (λstd, degrees): "))
    lambda_lcl = float(input("7. Enter Local Longitude (λlcl, degrees): "))
    H_b = float(input("8. Enter Building Height (Hb, meters): "))
    h_gap = float(input("9. Enter Height from ground to panel's bottom edge (h, meters): "))
    H_p = float(input("10. Enter Height of the panel (Hp, meters): "))
    d = float(input("11. Enter Horizontal distance between panel and wall (d, meters): "))
    rho_grd = float(input("12. Enter Ground Albedo (ρ_grd, dimensionless 0-1): "))
    rho_w = float(input("13. Enter Wall Albedo (ρ_w, dimensionless 0-1): "))

    # Fixed Variables per instruction
    tilt_angle = 90.0
    panel_azimuth = 0.0

    return {
        'date': date_obj, 'LCT': LCT, 'GHI': GHI, 'DHI': DHI,
        'latitude': latitude, 'lambda_std': lambda_std, 'lambda_lcl': lambda_lcl,
        'H_b': H_b, 'h': h_gap, 'H_p': H_p, 'd': d,
        'rho_grd': rho_grd, 'rho_w': rho_w,
        'tilt_angle': tilt_angle, 'panel_azimuth': panel_azimuth
    }

# --- 2. Solar Position Equations ---
def calculate_solar_position(inputs: dict) -> dict:
    n = inputs['date'].timetuple().tm_yday

    delta_deg = 23.45 * math.sin(_deg_to_rad(360.0 * (284 + n) / 365.0))
    B_deg = 360.0 * (n - 1) / 365.0
    B_rad = _deg_to_rad(B_deg)

    EoT = 229.2 * (0.000075 + 0.001868 * math.cos(B_rad) - 0.032077 * math.sin(B_rad)
                   - 0.014615 * math.cos(2 * B_rad) - 0.04089 * math.sin(2 * B_rad))

    LST = inputs['LCT'] + (4.0 * (inputs['lambda_std'] - inputs['lambda_lcl']) + EoT) / 60.0
    omega_deg = 15.0 * (LST - 12.0)

    phi_rad = _deg_to_rad(inputs['latitude'])
    delta_rad = _deg_to_rad(delta_deg)
    omega_rad = _deg_to_rad(omega_deg)

    cos_z = math.sin(phi_rad) * math.sin(delta_rad) + math.cos(phi_rad) * math.cos(delta_rad) * math.cos(omega_rad)
    cos_z = max(-1.0, min(1.0, cos_z))
    theta_z = _rad_to_deg(math.acos(cos_z))
    alpha_s = 90.0 - theta_z

    return {
        'n': n, 'delta': delta_deg, 'B': B_deg, 'EoT': EoT,
        'LST': LST, 'omega': omega_deg, 'cos_z': cos_z,
        'theta_z': theta_z, 'alpha_s': alpha_s
    }

# --- 3. Angle of Incidence & Beam Tilt Ratio ---
def calculate_aoi_front(sol: dict, inputs: dict) -> float:
    d, p, b, g, w = map(_deg_to_rad, [sol['delta'], inputs['latitude'], inputs['tilt_angle'], inputs['panel_azimuth'], sol['omega']])
    s_d, c_d, s_p, c_p, s_b, c_b, s_g, c_g, s_w, c_w = math.sin(d), math.cos(d), math.sin(p), math.cos(p), math.sin(b), math.cos(b), math.sin(g), math.cos(g), math.sin(w), math.cos(w)

    cos_theta_F = (s_d*s_p*c_b) - (s_d*c_p*s_b*c_g) + (c_d*c_p*c_b*c_w) + (c_d*s_p*s_b*c_g*c_w) + (c_d*s_b*s_g*s_w)
    return max(-1.0, min(1.0, cos_theta_F))

def calculate_RbF(cos_theta_F: float, cos_z: float, omega_deg: float, gamma_p: float) -> float:
    if cos_z <= 0: return 0.0
    # Condition: w is between gamma_p - 90 and gamma_p + 90
    if (gamma_p - 90) <= omega_deg <= (gamma_p + 90):
        return max(0.0, cos_theta_F) / cos_z
    return 0.0

# --- 4. Cavity View Factors ---
def calculate_cavity_view_factors(inputs: dict, alpha_s: float) -> dict:
    H_b = inputs['H_b']
    h = inputs['h']
    H_p = inputs['H_p']
    d = inputs['d']

    # Eq 17: Distance from top of panel to top of building
    L = H_b - H_p - h

    # Front Side
    XF_sky = 0.5  # For beta = 90
    XF_grd = 0.5  # For beta = 90

    # Rear Side: Sky and Ground (Eq 12 & 13)
    XR_sky = (H_p + math.sqrt(d**2 + L**2) - math.sqrt(d**2 + (H_p + L)**2)) / (2 * H_p)
    XR_grd = (H_p + math.sqrt(d**2 + h**2) - math.sqrt(d**2 + (H_p + h)**2)) / (2 * H_p)

    # Shaded Wall View Factor (Eq 14 & 16)
    if alpha_s > 0 and alpha_s < 90:
        Delta = d * math.tan(_deg_to_rad(alpha_s))
    elif alpha_s >= 90:
        Delta = 1e6 # Near infinity if sun is exactly overhead
    else:
        Delta = 0.0 # Sun below horizon

    term1 = math.sqrt(d**2 + (H_p - Delta)**2)
    term2 = math.sqrt(d**2 + (H_p + Delta)**2)
    term3 = 2 * math.sqrt(d**2 + Delta**2)

    XR_sh_w = (term1 + term2 - term3) / (2 * H_p)

    # Safety clamp for mathematical anomalies with extreme shadows
    XR_sh_w = max(0.0, min(1.0, XR_sh_w))

    # Unshaded Wall View Factor (Eq 15)
    XR_ush_w = 1.0 - XR_sky - XR_grd - XR_sh_w
    XR_ush_w = max(0.0, XR_ush_w) # Prevent floating point negative precision

    return {
        'L': L, 'Delta': Delta,
        'XF_sky': XF_sky, 'XF_grd': XF_grd,
        'XR_sky': XR_sky, 'XR_grd': XR_grd,
        'XR_sh_w': XR_sh_w, 'XR_ush_w': XR_ush_w
    }

# --- 5. Main Execution & Output ---
def run_bipv_irradiance():
    inp = get_user_inputs()
    sol = calculate_solar_position(inp)

    print("\n" + "="*50)
    print(" BIPV SOLAR CALCULATION RESULTS (STEP-BY-STEP)")
    print("="*50)

    print("\n[A] Solar Position")
    print(f" Day Number (n): {sol['n']}")
    print(f" Solar Declination (δ): {sol['delta']:.6f}°")
    print(f" Equation of Time (EoT): {sol['EoT']:.6f} mins")
    print(f" Local Solar Time (LST): {sol['LST']:.6f} hrs")
    print(f" Hour Angle (ω): {sol['omega']:.6f}°")
    print(f" Zenith Angle (θz): {sol['theta_z']:.6f}°")
    print(f" Cosine of θz: {math.cos(sol['theta_z'])}")
    print(f" Inclination Angle (αs): {sol['alpha_s']:.6f}°")

    # --- Nighttime Guardrail ---
    if sol['cos_z'] <= 0:
        print("\n--- SUN BELOW HORIZON (IRRADIANCE IS ZERO) ---")
        return

    # Calculate AOI & View Factors
    cos_theta_F = calculate_aoi_front(sol, inp)
    theta_F = _rad_to_deg(math.acos(cos_theta_F))
    RbF = calculate_RbF(cos_theta_F, sol['cos_z'], sol['omega'], inp['panel_azimuth'])

    vf = calculate_cavity_view_factors(inp, sol['alpha_s'])

    print("\n[B] Incident Angles & Optical Ratios")
    print(f" Angle of Incidence Front (θF): {theta_F:.6f}°")
    print(f" Cosine of Incidence (cos θF): {cos_theta_F:.6f}")
    print(f" Beam Tilt Ratio Front (RbF): {RbF:.6f}")

    print("\n[C] Cavity Geometry & View Factors")
    print(f" Top Gap Length (L): {vf['L']:.2f} m")
    print(f" Bottom Gap Length (h): {inp['h']:.2f} m")
    print(f" Shadow Displacement (Δ): {vf['Delta']:.6f} m")
    print(f" Front Sky VF (XF.sky): {vf['XF_sky']:.6f}")
    print(f" Front Ground VF (XF.grd): {vf['XF_grd']:.6f}")
    print(f" Rear Sky VF (XR.sky): {vf['XR_sky']:.6f}")
    print(f" Rear Ground VF (XR.grd): {vf['XR_grd']:.6f}")
    print(f" Rear Shaded Wall VF (XR.sh.w): {vf['XR_sh_w']:.6f}")
    print(f" Rear Unshaded Wall VF (XR.ush.w): {vf['XR_ush_w']:.6f}")

    # View Factor Check
    sum_vf = vf['XR_sky'] + vf['XR_grd'] + vf['XR_sh_w'] + vf['XR_ush_w']
    print(f" (Rear VF Summation Check: {sum_vf:.6f} -> should be ~1.0)")

    # Calculate Final Irradiance
    BHI = inp['GHI'] - inp['DHI']

    # Eq 18
    GF = (BHI * RbF) + (inp['DHI'] * vf['XF_sky']) + (inp['GHI'] * inp['rho_grd'] * vf['XF_grd'])

    # Eq 19
    term_sky = inp['DHI'] * vf['XR_sky']
    term_grd = inp['GHI'] * inp['rho_grd'] * vf['XR_grd']
    term_sh_w = ((inp['DHI'] / 2.0) + (inp['GHI'] * inp['rho_grd'] / 2.0)) * inp['rho_w'] * vf['XR_sh_w']
    term_ush_w = GF * inp['rho_w'] * vf['XR_ush_w']

    GR = term_sky + term_grd + term_sh_w + term_ush_w

    print("\n[D] Rear Irradiance Breakdown (W/m²)")
    print(f" Sky Diffuse Leakage: {term_sky:.2f}")
    print(f" Ground Reflection Leakage: {term_grd:.2f}")
    print(f" Shaded Wall Bounce: {term_sh_w:.2f}")
    print(f" Unshaded Wall Bounce: {term_ush_w:.2f}")

    print("\n" + "="*50)
    print(f" FINAL FRONT-SIDE IRRADIANCE (GF): {GF:.2f} W/m²")
    print(f" FINAL REAR-SIDE IRRADIANCE (GR):  {GR:.2f} W/m²")
    print("="*50 + "\n")

if __name__ == '__main__':
    run_bipv_irradiance()