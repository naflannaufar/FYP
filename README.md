# BIPV Irradiance Calculator ☀️

A comprehensive web-based calculator for analyzing vertical Building Integrated Photovoltaics (BIPV) irradiance. This tool computes solar irradiance on both front and rear surfaces of vertical bifacial panels, accounting for complex geometric and atmospheric factors.

## Overview

The BIPV Irradiance Calculator is designed to model and analyze solar irradiance incident on vertical building facades equipped with photovoltaic panels. It calculates:

- **Front Irradiance (GF)**: Direct beam, diffuse sky, and ground-reflected radiation on the front-facing surface
- **Rear Irradiance (GR)**: Sky diffuse leakage, ground reflection, shaded wall bounce, and unshaded wall bounce on the rear surface
- **Bifacial Total**: Combined front and rear irradiance (GF + GR)

This is particularly useful for:
- Building energy simulation and optimization
- Bifacial solar panel performance prediction
- Urban solar potential assessment
- BIPV system design and feasibility studies

## Features

### Input Parameters
- **Date & Time Selection**: Choose any date in 2025 and local clock time
- **Solar Irradiance Data**: Input Global Horizontal Irradiance (GHI) and Diffuse Horizontal Irradiance (DHI)
- **Location Coordinates**: Latitude, standard meridian, and local longitude
- **Building Geometry**: Building height, panel placement, dimensions, and distance from wall
- **Surface Albedo**: Adjustable ground and wall reflectivity values

### Output Analysis
The calculator displays:
1. **Solar Position** – Day number, declination, equation of time, solar altitude angles
2. **Cavity View Factors** – Geometric view factors for sky, ground, shaded and unshaded wall surfaces
3. **Angles & Beam Ratio** – Angle of incidence, cosine factor, beam tilt ratio
4. **Rear Irradiance Breakdown** – Detailed component analysis of rear-facing irradiance

### Design Features
- **Modern, Responsive UI** – Built with Streamlit for intuitive interaction
- **Google Fonts Typography** – Manrope (headings/UI) and JetBrains Mono (numeric values)
- **Color-Coded Interface** – Teal/green theme (#0f766e) for consistent branding
- **Wide Layout** – Optimized for desktop viewing with multi-column data display
- **Structured Output** – 2x2 grid layout for organized results presentation

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/FYP.git
   cd FYP
   ```

2. **Create a Virtual Environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running the Application

```bash
streamlit run app.py
```

The app will open in your default web browser at `http://localhost:8501`

### Workflow

1. **Adjust Sidebar Parameters**:
   - Select a date (month and day)
   - Input local clock time (hours and minutes)
   - Enter GHI and DHI values in W/m²
   - Set location coordinates (latitude, standard/local longitude)
   - Define building geometry (heights and distances in meters)
   - Configure ground and wall albedo values (0.0 to 1.0)

2. **View Results**:
   - The main area displays the computed irradiance values in a prominent result banner
   - Four detailed tables organize solar position, geometry, and irradiance breakdown
   - All calculations update in real-time as you adjust inputs

3. **Interpret Output**:
   - **Higher GF values** indicate stronger front-surface illumination
   - **Higher GR values** indicate effective rear-surface utility (bifacial benefit)
   - **View factor tables** show the geometric contribution of each radiation source

## Project Structure

```
FYP/
├── app.py                  # Main Streamlit application
├── requirements.txt        # Python dependencies
├── README.md              # This file
└── LICENSE                # Project license
```

## Key Equations & Methodology

### Solar Position
Uses standard solar geometry formulas to compute:
- Declination angle (δ)
- Equation of time (EoT)
- Hour angle (ω)
- Zenith angle (θz)
- Solar altitude (αs)

### Irradiance Components
**Front Surface (GF):**
```
GF = (BHI × RbF) + (DHI × XF_sky) + (GHI × ρ_grd × XF_grd)
```
Where:
- BHI = Beam Horizontal Irradiance (GHI - DHI)
- RbF = Beam tilt ratio on front surface
- XF_sky, XF_grd = View factors (sky, ground)
- ρ_grd = Ground albedo

**Rear Surface (GR):**
```
GR = (DHI × XR_sky) + (GHI × ρ_grd × XR_grd) + Term_sh + Term_ush
```
Where:
- Term_sh = Shaded wall bounce contribution
- Term_ush = Unshaded wall bounce contribution

### View Factors
Computed using geometric relationships accounting for:
- Panel height and position
- Building height
- Distance from wall
- Solar altitude angle

## Technical Stack

- **Framework**: [Streamlit](https://streamlit.io/) – Python web app framework
- **Language**: Python 3.8+
- **Fonts**: [Google Fonts](https://fonts.google.com/) (Manrope, JetBrains Mono)
- **Styling**: Custom CSS with Streamlit markdown support
- **Math**: Python built-in `math` module
- **Date Handling**: Python `datetime` and `calendar` modules

## Customization

### Modifying Default Values
Edit the `st.number_input()` and `st.slider()` calls in the sidebar section:
```python
GHI = st.number_input("GHI – Global Horizontal", 0.0, 1500.0, 800.0, 10.0)
```
Change the fourth parameter (800.0) to your desired default.

### Adjusting Color Scheme
Modify the CSS color variables in the `<style>` section:
```css
color: #0f766e;  /* Change this to your theme color */
```

### Adding More Locations
Extend the sidebar inputs to include a location picker or preset locations database.

## Troubleshooting

### App Not Starting
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check Python version: `python --version` (must be 3.8+)

### Calculations Not Updating
- Reload the page (browser refresh) or restart the Streamlit app
- Check browser console for JavaScript errors (F12 → Console)

### Display Issues
- Try a different browser (Chrome, Firefox, Edge)
- Clear browser cache and cookies
- Ensure viewport width is at least 1200px for optimal layout

## Performance Notes

- All calculations are performed in real-time with negligible latency
- The app uses pure Python for computations (no external API calls)
- Suitable for single-user or small-group environments
- For production deployment, consider using Streamlit Cloud or a containerized solution

## Future Enhancements

- [ ] Time-series analysis (hourly/daily profiles)
- [ ] 3D visualization of panel geometry
- [ ] Export results to CSV/PDF
- [ ] Historical weather data integration
- [ ] Multiple panel configuration support
- [ ] Optimization algorithm for panel placement
- [ ] Multi-user collaboration features

## License

See [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

## Contact & Support

For questions, bug reports, or feature requests, please open an issue on GitHub or contact the maintainers.

## References

- Häberlin, H. (2012). *Photovoltaics System Design and Practice*
- Perez, R., et al. (1990). "An anisotropic hourly diffuse normal irradiance model for tilted surfaces"
- PVLIB Python Documentation: https://pvlib-python.readthedocs.io/
- Streamlit Documentation: https://docs.streamlit.io/

---

**Last Updated**: April 2026  
**Version**: 1.0.0  
**Status**: Active Development
