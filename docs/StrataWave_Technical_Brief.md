# StrataWave — 1D Site Response Analysis Platform

## Technical Brief & Product Overview

**Version**: 3.0 | **Date**: April 2026 | **Status**: Production-Ready

---

## 1. Executive Summary

StrataWave is a web-based **1D Site Response Analysis (SRA)** platform designed for geotechnical earthquake engineers. It performs total stress analysis (TSA) using three native solvers — Linear, Equivalent-Linear (EQL), and Nonlinear — without any external binary dependency. The platform delivers DEEPSOIL-equivalent analysis capability through a modern browser interface with a 3-tier SaaS monetization model.

**Key differentiators:**
- Zero-install, browser-based operation (no MATLAB/Fortran dependency)
- Native Python solvers (Thomson-Haskell, iterative EQL, implicit Newmark-beta)
- DEEPSOIL-compatible workflow and output formats
- 3-tier plan system (Free / Starter / Pro) with feature gating
- Real-time analysis with 10+ engineering metrics and 7+ chart types

---

## 2. Geotechnical Engineering Scope

### 2.1 Analysis Types

| Analysis | Method | Domain | Application |
|----------|--------|--------|-------------|
| **Linear** | Thomson-Haskell propagator matrix | Frequency | Small-strain elastic site response, transfer functions |
| **EQL** | Iterative strain-compatible linearization | Frequency | Standard-of-practice for moderate seismicity |
| **Nonlinear** | Implicit Newmark-beta time integration | Time | Strong ground motion, large-strain response |

### 2.2 Constitutive Models

**MKZ (Modified Kondner-Zelasko)**
- Backbone: `G/Gmax = 1 / (1 + (gamma/gamma_ref)^alpha)`
- Parameters: `Gmax`, `gamma_ref`, `curvature (alpha)`, `g_reduction_min`
- Hysteretic damping via extended Masing rules with MRDF correction
- Suitable for clays and low-plasticity silts

**GQH (Generalized Quadratic-Hyperbolic)**
- Backbone: `G/Gmax = 1 / (1 + a1*r + a2*r^m)` where `r = gamma/gamma_ref`
- Parameters: `Gmax`, `gamma_ref`, `a1`, `a2`, `m`, `g_reduction_min`
- More flexible curve fitting than MKZ for complex soil behavior
- Suitable for sands and gravels with nonlinear stiffness degradation

**Elastic**
- Constant shear modulus, no stiffness degradation
- Used for bedrock or stiff layers where nonlinearity is negligible

### 2.3 Reference Curves & Calibration

| Reference Curve | PI Dependent | Parameters | Application |
|---|---|---|---|
| **Darendeli (2001)** | Yes | PI, OCR, sigma_m', frequency, cycles | Universal; most widely used in practice |
| **Seed & Idriss (1970)** | No | Upper / Mean bounds | Sands; classic reference |
| **Vucetic-Dobry (1991)** | Yes | Plasticity Index | Clays; PI-dependent curves |

Calibration workflow:
1. Select reference curve type per layer
2. Input soil-specific parameters (PI, OCR, effective stress)
3. Backend auto-calibrates MKZ/GQH parameters via least-squares fit
4. Preview G/Gmax and Damping curves (log-x) with target vs fitted overlay
5. Single Element Test (SET) for loop inspection at target strain amplitude

### 2.4 Boundary Conditions

- **Rigid Base**: Fixed base assumption, no radiation damping. Suitable when rock/soil impedance contrast is very high.
- **Elastic Halfspace**: Energy radiation into underlying rock via impedance matching. Required for accurate response when base is not infinitely rigid.

### 2.5 Damping Formulation

- **Frequency-Independent**: Constant viscous damping ratio applied to all frequencies. Standard approach for EQL.
- **Rayleigh Damping**: Frequency-dependent damping matched at two target frequencies (mode 1 and mode 2). Used in nonlinear analysis for viscous damping matrix construction. Follows DEEPSOIL convention: `C = a0*M + a1*K` with Rayleigh coefficients computed from target modes.

### 2.6 Auto-Sublayering

Wavelength-based automatic sublayer generation per DEEPSOIL methodology:
- `target_dz = Vs / (ppw * f_max)`
- Configurable: max frequency, points per wavelength, minimum dz, max sublayers per layer
- Ensures adequate spatial resolution for wave propagation at target frequencies

---

## 3. Analysis Output Metrics

### 3.1 Time Domain Metrics

| Metric | Definition | Unit |
|--------|-----------|------|
| **PGA** | Peak Ground Acceleration | m/s2, g |
| **PGV** | Peak Ground Velocity (integrated from acc) | cm/s |
| **PGD** | Peak Ground Displacement (double-integrated) | cm |
| **Arias Intensity** | Ia = pi/(2g) * integral(a^2 dt) | m/s |
| **CAV** | Cumulative Absolute Velocity = integral(\|a\| dt) | m/s |
| **D5-95** | Significant duration (5%-95% Arias intensity interval) | s |
| **Amplification Ratio** | Surface PGA / Input PGA | — |

### 3.2 Spectral Metrics (Pro)

| Metric | Definition | Unit |
|--------|-----------|------|
| **PSA** | Pseudo-Spectral Acceleration (5% damping, SDOF) | m/s2 |
| **PSV** | Pseudo-Spectral Velocity = PSA * T / (2pi) | m/s |
| **PSD** | Pseudo-Spectral Displacement = PSA * T^2 / (4pi^2) | m |
| **FAS** | Fourier Amplitude Spectrum (FFT-based) | m/s |
| **Kappa (kappa)** | High-frequency attenuation parameter from FAS slope | s |
| **T0** | Fundamental site period = 4H / Vs_avg | s |
| **Vs_avg** | Thickness-weighted harmonic average shear wave velocity | m/s |
| **\|H(f)\|** | Transfer function magnitude (surface/base) | — |
| **Spectral Amplification** | Surface PSA / Input PSA at each period | — |

### 3.3 Profile Metrics (Per Layer)

| Metric | Source | Unit |
|--------|--------|------|
| **gamma_max** | EQL: from eql_layers; NL: from hysteresis proxy | — |
| **tau_peak** | Peak shear stress (from hysteresis or Gmax*gamma approximation) | kPa |
| **damping_ratio** | Effective damping ratio | — |
| **sigma_v0** | Initial vertical effective stress at layer midpoint | kPa |
| **ru_max** | Maximum pore pressure ratio (if ESA) | — |

---

## 4. Technology Architecture

### 4.1 System Overview

```
Browser (React + htm)              FastAPI Backend (Python 3.12)
+------------------------+        +----------------------------+
| app.v2.js (shell)      |  HTTP  | app.py (33 endpoints)      |
| wizard.js (5 steps)    | <----> | linear.py (Thomson-Haskell)|
| results-viewer.js (6)  |        | nonlinear.py (Newmark-beta)|
| charts.js (SVG)        |        | calibration.py (Darendeli) |
| plans.js (tier gating) |        | export/excel.py (openpyxl) |
| profile-editor.js      |        | store/ (HDF5 + SQLite)     |
+------------------------+        +----------------------------+
```

### 4.2 Backend Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Web Framework | FastAPI (uvicorn) | REST API, async-ready |
| Numerical | NumPy, SciPy | FFT, integration, linear algebra |
| Spectra | Custom SDOF Newmark solver | Response spectrum computation |
| Storage | HDF5 (h5py) + SQLite | Time series + metadata |
| Export | openpyxl | Multi-sheet Excel workbook |
| Config | Pydantic v2 + YAML | Validated configuration models |
| Serving | StaticFiles mount | ESM module serving |

### 4.3 Frontend Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| UI Framework | React 18 (ESM) + htm | Component rendering, no build step |
| Charts | Custom SVG | Line charts, depth profiles, hover tooltips |
| State | React hooks (useState/useEffect) | Wizard, results, plan state |
| Persistence | localStorage | Wizard state, theme, plan tier |
| Styling | Pure CSS (variables) | Dark mode, responsive, design tokens |

### 4.4 Codebase Metrics

| Metric | Value |
|--------|-------|
| Python LOC | ~17,000 |
| JavaScript LOC | ~2,700 |
| CSS LOC | ~810 |
| API Endpoints | 33 |
| Test Cases | 273 |
| Git Commits | 176 |
| Example Configs | 4 |
| Total Files | 43 Python + 9 JS + CSS/HTML |

---

## 5. Solver Technical Details

### 5.1 Linear Solver — Thomson-Haskell

The linear solver implements 1D SH wave propagation using the Thomson-Haskell propagator matrix method:

1. Apply FFT to the input motion (base acceleration)
2. For each frequency component, compute the layer transfer matrix:
   - Complex shear modulus: `G* = G(1 + 2i*damping)`
   - Complex wave number: `k = omega / Vs*`
   - Layer propagator: 2x2 matrix relating displacement/stress at top and bottom
3. Chain-multiply propagator matrices through all layers
4. Apply boundary condition (rigid or elastic halfspace)
5. Compute surface motion via inverse FFT
6. Extract transfer function `|H(f)|` = |surface/base| in frequency domain

**Computational complexity**: O(N_layers * N_freq)

### 5.2 EQL Solver — Iterative Strain-Compatible

The EQL solver extends the linear solver with iterative property updates:

1. **Initialize**: Set G/Gmax = 1.0 and damping = damping_min for all layers
2. **Iterate** (max 15 iterations):
   a. Run linear analysis with current properties
   b. Compute effective strain per layer: `gamma_eff = strain_ratio * gamma_max` (default ratio = 0.65, per Idriss & Sun 1992)
   c. Update G/Gmax and damping from material curves at gamma_eff
   d. Check convergence: `max(|delta_Vs|) < tolerance` (default 3%)
3. **Output**: Converged properties, iteration history, per-layer Vs/damping/strain

**Convergence tracking**: Max Vs change per iteration stored in HDF5 for diagnostic plotting.

### 5.3 Nonlinear Solver — Implicit Newmark-Beta

The nonlinear solver implements time-domain integration of the equation of motion:

```
[M]{a} + [C]{v} + {F_int(u)} = {F_ext(t)}
```

**Integration scheme**: Average acceleration method (beta=0.25, gamma=0.5)

1. **Initialization**: Compute mass matrix M, initial stiffness K0, Rayleigh damping C = a0*M + a1*K0
2. **For each time step dt**:
   a. Predict displacement increment: `du_predict = dt*v + 0.5*dt^2*a`
   b. Compute internal force from backbone curve: `F_int = tau(gamma)` using MKZ or GQH
   c. Form effective stiffness: `K_eff = K_t + a0*M + a1*C` (tangent stiffness linearization)
   d. Solve: `K_eff * du_correction = R` (residual force)
   e. Update: `u, v, a` with Newmark update equations
3. **Hysteresis**: Masing rules for unload/reload paths with MRDF damping correction

**Key advantages over explicit schemes**:
- Unconditionally stable (no CFL condition on dt)
- No strain overshoot at loading reversal
- No positive-feedback softening loops
- Supports larger time steps for computational efficiency

---

## 6. SaaS Plan Structure

### 6.1 3-Tier Feature Map

| Feature | Free | Starter | Pro |
|---------|------|---------|-----|
| **Solvers** | Linear, EQL, Nonlinear | All | All |
| **Time Histories** (acc, vel, disp) | Yes | Yes | Yes |
| **PGA, PGV, PGD, Arias, CAV, D5-95** | Yes | Yes | Yes |
| **Response Spectra (PSA)** | Yes | Yes | Yes |
| **Transfer Function (raw)** | Yes | Yes | Yes |
| **Fourier Amplitude Spectrum** | Yes | Yes | Yes |
| **Stress-Strain Loops** | Yes | Yes | Yes |
| **Depth Profile Charts** | Yes | Yes | Yes |
| **CSV Export** | Yes | Yes | Yes |
| **Daily Run Limit** | **3** | **10** | **Unlimited** |
| **Excel Export** | — | Basic | Full (PSV/PSD) |
| **Run Comparison** | — | Yes | Yes |
| **Batch Analysis** | — | Yes | Yes |
| **Dark Mode** | — | Yes | Yes |
| **SVG Chart Export** | — | Yes | Yes |
| **PSV / PSD Charts** | — | — | Yes |
| **Kappa (kappa) Estimator** | — | — | Yes |
| **Site Period (T0)** | — | — | Yes |
| **Smoothed Transfer Function** | — | — | Yes |

### 6.2 Feature Gating Implementation

- Frontend: `ProGuard` component wraps Pro features with blur overlay + lock icon
- `TierBadge` component shows required plan tier (STARTER / PRO)
- `canUseFeature(plan, feature)` checks plan order against feature minimum tier
- Backend: `/api/plan` returns daily run count and limit enforcement
- Excel export: `tier` parameter controls sheet content (Starter: no PSV/PSD columns)

---

## 7. User Workflow

### 7.1 Five-Step Wizard

```
1. Analysis Type    → Solver selection, boundary condition, example loader
2. Soil Profile     → Layer table (CRUD, copy, reorder), reference curve selector,
                      calibration preview (G/Gmax + Damping), auto-sublayering,
                      CSV import/export, Single Element Test
3. Input Motion     → CSV/AT2 upload, motion library browser, PGA preview,
                      scaling (factor / target PGA), batch mode (multi-motion)
4. Damping          → Frequency-independent or Rayleigh (2-mode), viscous update
5. Analysis Control → dt, f_max, EQL iterations/tolerance/strain ratio,
                      NL substeps, validation warnings, Run button
```

### 7.2 Results Dashboard (6 Tabs)

1. **Time Histories**: Acceleration, Velocity, Displacement charts + Husid plot + 10 metric cards
2. **Stress-Strain**: Per-layer hysteresis loops + G/Gmax, damping, energy metrics
3. **Spectral**: PSA (with compare overlay), Amp. Ratio, Transfer Function, FAS (with kappa fit), PSV, PSD, Smoothed TF, PSA Summary Table (19 standard periods)
4. **Profile**: Depth charts (Vs, max strain, peak stress, damping, sigma_v0, ru_max) + layer table
5. **Mobilized Strength**: Mobilized ratio, G/Gmax, damping depth charts + per-layer table
6. **Convergence**: EQL: iteration chart + metrics; NL: severity badge + warning/failure counts

### 7.3 Export Options

| Format | Tier | Content |
|--------|------|---------|
| **CSV** | Free | Surface acceleration time history |
| **SVG** | Starter | Individual chart download (any chart) |
| **Excel** | Starter | Summary, Time History, Spectral, Profile, EQL Convergence |
| **Excel (Pro)** | Pro | + PSV/PSD columns, T0/kappa/Vs_avg in Summary |

---

## 8. Quality Assurance

### 8.1 Test Coverage

- **273 test cases** across 34 test files
- Linear solver validation against analytical solutions
- Nonlinear Newmark-beta integration accuracy
- Material model calibration (Darendeli fit quality)
- EQL convergence behavior
- Web API endpoint testing
- HDF5/SQLite storage integrity
- Motion import/processing (PEER AT2, CSV)

### 8.2 Validation Approach

- **Input validation**: `validateWizard()` checks all parameters before run
- **Backend sanity check**: `POST /api/wizard/sanity-check` validates file paths, config compatibility, Nyquist condition
- **Run limit enforcement**: Daily count tracked per plan tier
- **Delete confirmation**: `confirm()` dialog before run deletion

### 8.3 DEEPSOIL Parity

StrataWave native solvers have been validated against DEEPSOIL for:
- 4 canonical example profiles (linear, EQL, nonlinear MKZ, nonlinear GQH)
- PGA agreement within 5% for standard benchmark motions
- Transfer function shape and peak frequency alignment
- EQL convergence behavior (iteration count, final Vs change)
- GoF metrics: Arias intensity ratio, cross-correlation lag

---

## 9. Deployment & Infrastructure

### 9.1 Current Architecture

```
Single-server deployment:
  Python 3.12 + uvicorn (ASGI)
  FastAPI serving API + static assets
  Local file system for HDF5/SQLite results
  No external database required
```

### 9.2 Requirements

- Python 3.12+
- NumPy, SciPy, h5py, pydantic, fastapi, uvicorn
- openpyxl (optional, for Excel export)
- No Fortran/C compilation required
- No MATLAB runtime required
- No external solver binary required

### 9.3 Scaling Path

| Stage | Architecture | Capacity |
|-------|-------------|----------|
| MVP (current) | Single server, file-based | ~50 concurrent users |
| Growth | Docker + PostgreSQL + S3 | ~500 concurrent users |
| Scale | Kubernetes + worker queue + Redis | ~5000+ concurrent users |

---

## 10. Competitive Positioning

| Feature | DEEPSOIL | SHAKE | Strata | **StrataWave** |
|---------|----------|-------|--------|---------------|
| Platform | Desktop (Win) | Desktop | Desktop | **Web (any browser)** |
| Install | Required | Required | Required | **Zero-install** |
| Linear | Yes | Yes | Yes | **Yes** |
| EQL | Yes | Yes | Yes | **Yes** |
| Nonlinear | Yes | No | No | **Yes** |
| Constitutive | MKZ, GQH, PM4 | Linear | Linear | **MKZ, GQH** |
| API Access | No | No | No | **Yes (33 endpoints)** |
| Batch Analysis | Limited | No | No | **Yes** |
| Real-time Preview | No | No | No | **Yes** |
| SaaS Model | No | No | No | **Yes (3-tier)** |
| Kappa Estimator | No | No | No | **Yes** |
| Dark Mode | No | No | No | **Yes** |
| Mobile-friendly | No | No | No | **Yes** |

---

## 11. Roadmap

### Planned Features
- Native Effective Stress Analysis (ESA) solver
- PM4Sand / PM4Silt constitutive models
- User authentication & workspace management
- Docker containerized deployment
- Multi-language UI (EN/TR/JP)
- API documentation (OpenAPI/Swagger auto-generated)
- Cloud storage for results (S3/GCS)
- Tripartite spectral chart (4-way log paper)

### Research Directions
- Machine learning site classification from Vs profile
- Automated design spectrum matching
- Probabilistic site response analysis
- 2D/3D extension feasibility study

---

*StrataWave is built with Python, React, and engineering rigor. Every solver implements peer-reviewed methods. Every metric follows established seismological conventions.*
