"""
Coupled air-cushion / terramechanics model for a partially unloaded wheeled vehicle.

Version 2 changes (in response to review):
  * fan efficiency and driveline efficiency separated; both powers referred to
    the same energy boundary (powerplant input);
  * load-dependent contact patch A_w(alpha) = A_w0 (1-alpha)^gamma;
  * one-at-a-time sensitivity extended to cushion/system parameters;
  * forward-speed sweep;
  * broad (+-30 %) uncertainty scenario alongside the local (+-15 %) one.

All figures, tables and numbers in the manuscript are produced by this file.
Run:  python3 model.py
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import json, os

os.makedirs("fig", exist_ok=True)
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.grid": True, "grid.alpha": 0.3, "grid.linestyle": ":",
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 300, "savefig.bbox": "tight",
})

# ----------------------------------------------------------------------
# 1. Vehicle and cushion parameters (single source of truth)
# ----------------------------------------------------------------------
VEH = dict(
    m=1530.0, g=9.81, G=15000.0,
    nw=4,
    b=0.40,          # contact patch width, m
    l0=0.50,         # contact patch length at alpha = 0, m
    gamma=0.0,       # contact-patch load sensitivity exponent
    wheel="plate",  # sinkage relation: "plate" (flat plate) or "rigid" (Bekker rigid wheel)
    D=1.05,          # wheel outer diameter, m (rigid-wheel relation only)
    z_crit=0.35,     # belly clearance limit, m
    A_ac=3.00,       # cushion planform area, m^2
    L_p=7.40,        # skirt perimeter, m
    h_gap=0.010,     # skirt clearance, m
    Cd_leak=0.60,    # peripheral-jet discharge coefficient
    eta_fan=0.60,    # fan aerodynamic + fan-drive efficiency
    eta_dr=0.85,     # driveline (transmission + wheel) efficiency
    rho_air=1.20,
    Cd=0.80, S=3.0,
    mu_skirt=0.05,
    f_roll=0.05,
    v=5.0,
    s=0.25,
)

SOILS = {
    "Dry sand":     dict(n=1.10, kc=0.99e3, kphi=1528.4e3, c=1.04e3, phi=28.0, K=0.025),
    "Snow (U.S.)":  dict(n=1.60, kc=4.37e3, kphi=196.7e3,  c=1.03e3, phi=19.7, K=0.025),
    "Organic soil": dict(n=1.20, kc=2.00e3, kphi=32.0e3,   c=3.00e3, phi=12.0, K=0.015),
}
SOIL_KEYS = ["n", "kc", "kphi", "c", "phi", "K"]


# ----------------------------------------------------------------------
# 2. Model
# ----------------------------------------------------------------------
def k_eq(soil, b):
    return soil["kc"] / b + soil["kphi"]


def geometry(alpha, V):
    l = V["l0"] * (1.0 - alpha) ** V["gamma"]
    return l, V["nw"] * V["b"] * l


def sinkage(alpha, soil, V=VEH):
    """Rut depth and mean contact pressure.

    "plate": flat-plate idealisation of the contact patch (baseline).
    "rigid": Bekker closed-form rigid-wheel relation, used in Section 6 as an
             independent cross-check of the sinkage branch.
    """
    _, A_tot = geometry(alpha, V)
    p = V["G"] * (1.0 - alpha) / A_tot
    if V.get("wheel", "plate") == "rigid":
        n, W = soil["n"], V["G"] * (1.0 - alpha) / V["nw"]
        z = (3.0 * W / ((3.0 - n) * k_eq(soil, V["b"]) * V["b"]
                        * np.sqrt(V["D"]))) ** (2.0 / (2.0 * n + 1.0))
        return z, p
    return (p / k_eq(soil, V["b"])) ** (1.0 / soil["n"]), p


def compaction_resistance(alpha, soil, V=VEH):
    z, _ = sinkage(alpha, soil, V)
    n = soil["n"]
    return V["nw"] * V["b"] * k_eq(soil, V["b"]) * z ** (n + 1) / (n + 1)


def traction(alpha, soil, s=None, V=VEH):
    s = V["s"] if s is None else s
    l, A_tot = geometry(alpha, V)
    sigma = V["G"] * (1.0 - alpha) / A_tot
    tau_max = soil["c"] + sigma * np.tan(np.radians(soil["phi"]))
    K = soil["K"]
    s = np.maximum(np.asarray(s, dtype=float), 1e-12)
    fac = 1.0 - (K / (s * l)) * (1.0 - np.exp(-s * l / K))
    return V["nw"] * V["b"] * l * tau_max * fac


def cushion(alpha, V=VEH):
    F_ac = alpha * V["G"]
    dp = F_ac / V["A_ac"]
    v_jet = np.sqrt(2.0 * dp / V["rho_air"])
    Q = V["Cd_leak"] * V["L_p"] * V["h_gap"] * v_jet
    return dp, Q, dp * Q / V["eta_fan"], F_ac


def evaluate(alpha, soil, V=VEH):
    alpha = np.asarray(alpha, dtype=float)
    z, p = sinkage(alpha, soil, V)
    F_def = compaction_resistance(alpha, soil, V)
    F_roll = V["f_roll"] * V["G"] * (1.0 - alpha)
    dp, Q, P_fan, F_ac = cushion(alpha, V)
    F_skirt = V["mu_skirt"] * F_ac
    F_aero = 0.5 * V["rho_air"] * V["Cd"] * V["S"] * V["v"] ** 2 * np.ones_like(alpha)
    F_res = F_def + F_roll + F_skirt + F_aero
    F_x = traction(alpha, soil, V=V)
    P_wheel = F_res * V["v"]
    P_prop = P_wheel / V["eta_dr"]
    P_tot = P_prop + P_fan
    return dict(alpha=alpha, z=z, p=p, F_def=F_def, F_roll=F_roll, F_skirt=F_skirt,
                F_aero=F_aero, F_res=F_res, F_x=F_x, K=F_x / F_res,
                dp=dp, Q=Q, P_fan=P_fan, P_wheel=P_wheel, P_prop=P_prop,
                P_tot=P_tot, E=P_tot / (V["G"] * V["v"]))


# ----------------------------------------------------------------------
# 3. Constrained optimisation
# ----------------------------------------------------------------------
def optimum(soil, V=VEH, na=9501):
    a = np.linspace(0.0, 0.95, na)
    r = evaluate(a, soil, V)
    ok_t, ok_z = r["K"] >= 1.0, r["z"] <= V["z_crit"]
    feas = ok_t & ok_z
    a_trac = float(a[ok_t][0]) if ok_t.any() else None
    a_geom = float(a[ok_z][0]) if ok_z.any() else None
    if not feas.any():
        return dict(a_min=None, a_opt=None, a_trac=a_trac, a_geom=a_geom,
                    K_max=float(r["K"].max()), P_tot0=float(r["P_tot"][0]))
    E = np.where(feas, r["E"], np.inf)
    i = int(np.argmin(E))
    band = a[feas & (r["E"] <= 1.01 * r["E"][i])]
    return dict(a_min=float(a[feas][0]), a_trac=a_trac, a_geom=a_geom,
                K_max=float(r["K"].max()), a_opt=float(a[i]), E_opt=float(r["E"][i]), K_opt=float(r["K"][i]),
                z_opt=float(r["z"][i]), P_tot_opt=float(r["P_tot"][i]),
                P_fan_opt=float(r["P_fan"][i]), P_prop_opt=float(r["P_prop"][i]),
                band=[float(band.min()), float(band.max())],
                E0=float(r["E"][0]), K0=float(r["K"][0]), z0=float(r["z"][0]),
                P_tot0=float(r["P_tot"][0]))


# ----------------------------------------------------------------------
# 4. Verification
# ----------------------------------------------------------------------
def verification():
    out, soil, V = [], SOILS["Organic soil"], VEH
    l0 = V["l0"]
    r0 = evaluate(0.0, soil)
    p_direct = V["G"] / (V["nw"] * V["b"] * l0)
    out.append(("alpha = 0 reduces to classical case (p = G/A)", float(r0["p"]), p_direct,
                abs(r0["p"] - p_direct) < 1e-9))
    r1 = evaluate(1.0 - 1e-9, soil)
    out.append(("alpha -> 1 : z -> 0", float(r1["z"]), 0.0, r1["z"] < 1e-5))
    out.append(("alpha -> 1 : F_def -> 0", float(r1["F_def"]), 0.0, r1["F_def"] < 1e-3))
    Fx_coh = V["nw"] * V["b"] * l0 * soil["c"] * (
        1 - (soil["K"] / (V["s"] * l0)) * (1 - np.exp(-V["s"] * l0 / soil["K"])))
    out.append(("alpha -> 1 : F_x -> cohesive limit", float(r1["F_x"]), float(Fx_coh),
                abs(r1["F_x"] - Fx_coh) < 1.0))
    fx0 = float(traction(0.3, soil, s=1e-9))
    out.append(("s -> 0 : F_x -> 0", fx0, 0.0, fx0 < 1.0))
    Fx_inf = float(traction(0.3, soil, s=1e4))
    sigma = V["G"] * 0.7 / (V["nw"] * V["b"] * l0)
    Fx_cm = V["nw"] * V["b"] * l0 * (soil["c"] + sigma * np.tan(np.radians(soil["phi"])))
    out.append(("s -> inf : F_x -> Coulomb-Mohr limit", Fx_inf, float(Fx_cm),
                abs(Fx_inf - Fx_cm) / Fx_cm < 1e-3))
    r = evaluate(0.5, soil)
    lhs = float(r["P_tot"])
    rhs = float(r["F_res"]) * V["v"] / V["eta_dr"] + float(r["P_fan"])
    out.append(("energy boundary: P_tot = F_res v / eta_dr + P_fan", lhs, rhs,
                abs(lhs - rhs) < 1e-6))
    return out


# ----------------------------------------------------------------------
# 5. Sensitivity
# ----------------------------------------------------------------------
def sens_soil(soil, delta=0.15):
    base = optimum(soil)["a_opt"]
    rows = []
    for k in SOIL_KEYS:
        hi, lo = dict(soil), dict(soil)
        hi[k] = soil[k] * (1 + delta); lo[k] = soil[k] * (1 - delta)
        ah, al = optimum(hi)["a_opt"], optimum(lo)["a_opt"]
        rows.append([k, al, ah, max(abs(ah - base), abs(al - base))])
    rows.sort(key=lambda r: -r[3])
    return base, rows


def sens_system(soil):
    deltas = {"h_gap": .20, "eta_fan": .15, "eta_dr": .10, "Cd_leak": .15,
              "A_ac": .10, "mu_skirt": .20, "f_roll": .20, "L_p": .10}
    base = optimum(soil)["a_opt"]
    rows = []
    for k, d in deltas.items():
        hi, lo = dict(VEH), dict(VEH)
        hi[k] = VEH[k] * (1 + d); lo[k] = VEH[k] * (1 - d)
        ah, al = optimum(soil, hi)["a_opt"], optimum(soil, lo)["a_opt"]
        rows.append([k, d, al, ah, max(abs(ah - base), abs(al - base))])
    rows.sort(key=lambda r: -r[4])
    return base, rows


def speed_sweep(soil, speeds=(2.5, 5.0, 7.5, 10.0)):
    rows = []
    for v in speeds:
        V = dict(VEH); V["v"] = v
        o = optimum(soil, V)
        rows.append([v, o["a_min"], o["a_opt"], o["P_tot_opt"] / 1e3,
                     o["P_tot0"] / 1e3, o["band"]])
    return rows


def gamma_sweep(soil, gammas=(0.0, 0.3, 0.5, 1.0)):
    """Contact patch shrinking with load: A_w = A_w0 (1-alpha)^gamma.
    gamma = 0 : near-rigid wheel, contact geometry set by the soil (soft terrain);
    gamma = 1 : fully flexible tyre at constant inflation pressure -- ground
                pressure is then independent of alpha and the concept degenerates."""
    rows = []
    for g in gammas:
        V = dict(VEH); V["gamma"] = g
        o = optimum(soil, V)
        r0 = evaluate(0.0, soil, V)
        r9 = evaluate(0.8, soil, V)
        rows.append([g, float(r0["z"]), float(r9["z"]), float(o["K_max"]),
                     o["a_trac"], o["a_geom"], o["a_min"], o["a_opt"],
                     None if o["a_opt"] is None else o["P_tot_opt"] / 1e3])
    return rows


# ----------------------------------------------------------------------
# 6. Monte-Carlo
# ----------------------------------------------------------------------
def monte_carlo(soil, N=1500, spread=0.15, seed=7, system=False):
    rng = np.random.default_rng(seed)
    a_opt, a_min = [], []
    for _ in range(N):
        s2 = {k: v * (1 + spread * rng.uniform(-1, 1)) for k, v in soil.items()}
        V = dict(VEH)
        if system:
            for k in ["h_gap", "eta_fan", "eta_dr", "Cd_leak", "A_ac", "mu_skirt", "f_roll"]:
                V[k] = VEH[k] * (1 + spread * rng.uniform(-1, 1))
        o = optimum(s2, V, na=1901)
        if o["a_opt"] is not None:
            a_opt.append(o["a_opt"]); a_min.append(o["a_min"])
    a_opt, a_min = np.array(a_opt), np.array(a_min)
    q = lambda x, p: float(np.percentile(x, p))
    return dict(n=int(len(a_opt)), N=N, spread=spread, system=system,
                opt_med=float(np.median(a_opt)), opt_ci=[q(a_opt, 2.5), q(a_opt, 97.5)],
                min_med=float(np.median(a_min)), min_ci=[q(a_min, 2.5), q(a_min, 97.5)],
                infeasible=int(N - len(a_opt)), samples=a_opt)


# ----------------------------------------------------------------------
# 6b. Cross-comparison with independent published formulations
# ----------------------------------------------------------------------
def crosscheck_sinkage(alphas=(0.0, 0.2, 0.4, 0.6, 0.8)):
    """Flat-plate sinkage vs the Bekker closed-form rigid-wheel relation."""
    rows = []
    for name, s in SOILS.items():
        Vp = dict(VEH); Vp["wheel"] = "plate"
        Vr = dict(VEH); Vr["wheel"] = "rigid"
        for al in alphas:
            zp = float(sinkage(al, s, Vp)[0])
            zr = float(sinkage(al, s, Vr)[0])
            rows.append([name, al, zp, zr, zr / zp])
    return rows


def crosscheck_traction(alphas=(0.0, 0.2, 0.4, 0.6, 0.8)):
    """Cross-comparison with the Wismer-Luth empirical relations.

    The wheel numeric Cn is not assumed: it is back-calculated from the motion
    resistance ratio predicted by the present model,
        MR/W = 1.2/Cn + 0.04,
    and the resulting Cn is then used to predict the gross traction ratio
        GT/W = 0.75 (1 - exp(-0.3 Cn s))
    independently. The traction branch is therefore tested, not fitted.
    Wismer-Luth was calibrated on mineral agricultural soils; it is not
    applicable below Cn ~ 5 and this is flagged in the output.
    """
    rows = []
    for name, s in SOILS.items():
        for al in alphas:
            r = evaluate(al, s)
            W = VEH["G"] * (1.0 - al)
            Ww = W / VEH["nw"]
            mr = (float(r["F_def"]) + float(r["F_roll"])) / VEH["nw"] / Ww
            if mr <= 0.04:
                rows.append([name, al, mr, None, None, None, None]); continue
            Cn = 1.2 / (mr - 0.04)
            gt_wl = 0.75 * (1.0 - np.exp(-0.3 * Cn * VEH["s"]))
            gt_own = float(r["F_x"]) / W
            rows.append([name, al, mr, Cn, gt_wl, gt_own,
                         100.0 * (gt_own - gt_wl) / gt_wl])
    return rows


def robustness_wheel_model():
    """Does substituting the rigid-wheel sinkage relation move the optimum?"""
    out = []
    for name, s in SOILS.items():
        for w in ("plate", "rigid"):
            V = dict(VEH); V["wheel"] = w
            o = optimum(s, V)
            out.append([name, w, o["a_min"], o["a_opt"],
                        None if o["a_opt"] is None else o["P_tot_opt"] / 1e3])
    return out


# ----------------------------------------------------------------------
# 7. Figures
# ----------------------------------------------------------------------
COL = {"Dry sand": "#c8811b", "Snow (U.S.)": "#2b6ca3", "Organic soil": "#4a7a3a"}
a = np.linspace(0, 0.9, 400)


def save(fig, stem):
    fig.savefig(f"fig/{stem}.pdf"); fig.savefig(f"fig/{stem}.png"); plt.close(fig)


def fig_sinkage():
    fig, ax = plt.subplots(figsize=(6.0, 3.8))
    for name, s in SOILS.items():
        z, _ = sinkage(a, s)
        ax.plot(a, z, lw=2, color=COL[name], label=name)
    ax.axhline(VEH["z_crit"], color="k", ls="--", lw=1)
    ax.text(0.02, VEH["z_crit"] + .012, r"$z_{crit}=0.35$ m (belly clearance)", fontsize=8)
    ax.set_xlabel(r"load-relief fraction $\alpha$ (-)")
    ax.set_ylabel(r"rut depth $z$ (m)")
    ax.set_ylim(0, 0.62); ax.set_xlim(0, 0.9); ax.legend(frameon=False)
    save(fig, "fig2_sinkage")


def fig_forces():
    soil = SOILS["Organic soil"]; r = evaluate(a, soil); o = optimum(soil)
    fig, ax = plt.subplots(figsize=(6.0, 3.8))
    ax.stackplot(a, r["F_def"]/1e3, r["F_roll"]/1e3, r["F_skirt"]/1e3, r["F_aero"]/1e3,
                 labels=[r"$F_{def}$", r"$F_{roll}$", r"$F_{skirt}$", r"$F_{aero}$"],
                 colors=["#9dbf8e", "#c6d9bd", "#e8d6a0", "#d9b8b0"], alpha=.95)
    ax.plot(a, r["F_res"]/1e3, color="#2f4f2f", lw=2, label=r"$F_{res}$ (total)")
    ax.plot(a, r["F_x"]/1e3, color="#b03030", lw=2, label=r"$F_x$ (traction)")
    ax.axvline(o["a_trac"], color="k", ls=":", lw=1.2)
    ax.axvline(o["a_geom"], color="k", ls="-.", lw=1.2)
    ax.text(o["a_trac"]+.01, 8.6, r"$K_{TR}=1$: %.2f" % o["a_trac"], fontsize=8)
    ax.text(o["a_geom"]+.01, 7.8, r"$z=z_{crit}$: %.2f" % o["a_geom"], fontsize=8)
    ax.set_xlabel(r"load-relief fraction $\alpha$ (-)"); ax.set_ylabel("force (kN)")
    ax.set_xlim(0, .9); ax.set_ylim(0, 9.4); ax.legend(frameon=False, ncol=2, fontsize=8)
    save(fig, "fig3_forces")


def fig_ratio():
    fig, ax = plt.subplots(figsize=(6.0, 3.8))
    for name, s in SOILS.items():
        ax.plot(a, evaluate(a, s)["K"], lw=2, color=COL[name], label=name)
    ax.axhline(1.0, color="k", ls="--", lw=1.2)
    ax.text(0.30, 1.25, r"$K_{TR}=1$ : mobility threshold", fontsize=8)
    o = optimum(SOILS["Organic soil"])
    ax.axvspan(o["band"][0], o["band"][1], color="#cfe0c8", alpha=.55)
    ax.set_xlabel(r"load-relief fraction $\alpha$ (-)")
    ax.set_ylabel(r"traction-to-resistance ratio $K_{TR}$ (-)")
    ax.set_xlim(0, .9); ax.set_ylim(0, 7.2)
    ax.legend(frameon=False, loc="upper right", fontsize=8)
    save(fig, "fig4_ratio")


def fig_power():
    soil = SOILS["Organic soil"]; r = evaluate(a, soil); o = optimum(soil)
    fig, ax = plt.subplots(figsize=(6.0, 3.8))
    ax.plot(a, r["P_prop"]/1e3, lw=1.8, color="#b03030",
            label=r"$P_{prop}=F_{res}v/\eta_{dr}$")
    ax.plot(a, r["P_fan"]/1e3, lw=1.8, color="#2b6ca3", label=r"$P_{fan}$")
    ax.plot(a, r["P_tot"]/1e3, lw=2.4, color="#2f2f2f", label=r"$P_{tot}$")
    ax.axvspan(o["band"][0], o["band"][1], color="#e2e2e2", alpha=.7)
    ax.axvline(o["a_opt"], color="k", ls="--", lw=1.2)
    ax.axvline(o["a_min"], color="k", ls="-.", lw=1.2)
    ax.plot([o["a_opt"]], [o["P_tot_opt"]/1e3], "o", ms=6, color="k")
    ax.annotate(r"$\alpha^{*}$=%.2f, $P_{tot}$=%.1f kW" % (o["a_opt"], o["P_tot_opt"]/1e3),
                xy=(o["a_opt"], o["P_tot_opt"]/1e3),
                xytext=(o["a_opt"]+.13, o["P_tot_opt"]/1e3+12), fontsize=8,
                arrowprops=dict(arrowstyle="->", lw=.8))
    ax.text(o["a_min"]-.01, 55, r"$\alpha_{min}$", fontsize=8, ha="right")
    ax.set_xlabel(r"load-relief fraction $\alpha$ (-)")
    ax.set_ylabel("power at powerplant input (kW)")
    ax.set_xlim(0, .9); ax.set_ylim(0, 62); ax.legend(frameon=False)
    save(fig, "fig5_power")


def fig_surface():
    soil = SOILS["Organic soil"]
    A, S = np.meshgrid(np.linspace(0, .9, 160), np.linspace(0.005, .6, 160))
    F = traction(A, soil, s=S) / 1e3
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.4, 3.6))
    cs = ax1.contourf(A, S, F, levels=14, cmap="viridis")
    cl = ax1.contour(A, S, F, levels=7, colors="w", linewidths=.6)
    ax1.clabel(cl, inline=True, fontsize=7, fmt="%.1f")
    fig.colorbar(cs, ax=ax1, label=r"$F_x$ (kN)")
    ax1.set_xlabel(r"$\alpha$ (-)"); ax1.set_ylabel(r"slip $s$ (-)")
    ax1.set_title("(a) traction map", fontsize=9); ax1.grid(False)
    sv = np.linspace(0.005, .6, 400)
    for al, c in zip([0.0, .3, .5, .8], ["#333333", "#2b6ca3", "#4a7a3a", "#c8811b"]):
        Fs = traction(al, soil, s=sv) / 1e3
        ax2.plot(sv, Fs, lw=2, color=c, label=r"$\alpha=%.2f$" % al)
        i90 = int(np.argmax(Fs >= 0.9 * Fs[-1]))
        ax2.plot([sv[i90]], [Fs[i90]], "o", ms=4.5, color=c)
    ax2.set_xlabel(r"slip $s$ (-)"); ax2.set_ylabel(r"$F_x$ (kN)")
    ax2.set_title("(b) traction-slip slices; 90 % mobilisation marked", fontsize=9)
    ax2.legend(frameon=False, fontsize=8)
    save(fig, "fig6_surface")


def fig_mc(mc15, mc30):
    fig, ax = plt.subplots(figsize=(6.2, 3.5))
    ax.hist(mc30["samples"], bins=45, color="#d9d2b8", edgecolor="w", label=r"$\pm30\%$ (broad)")
    ax.hist(mc15["samples"], bins=45, color="#9dbf8e", edgecolor="w", label=r"$\pm15\%$ (local)")
    ax.axvline(mc15["opt_med"], color="k", lw=2)
    for x in mc15["opt_ci"]:
        ax.axvline(x, color="k", ls="--", lw=1)
    for x in mc30["opt_ci"]:
        ax.axvline(x, color="#7a6a3a", ls=":", lw=1.2)
    ax.set_xlabel(r"optimal load-relief fraction $\alpha^{*}$ (-)")
    ax.set_ylabel("frequency"); ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.text(.02, .78,
            "local: median %.2f, 95%% CI [%.2f, %.2f]\nbroad: median %.2f, 95%% CI [%.2f, %.2f]"
            % (mc15["opt_med"], *mc15["opt_ci"], mc30["opt_med"], *mc30["opt_ci"]),
            transform=ax.transAxes, fontsize=8)
    save(fig, "fig7_montecarlo")


def fig_gamma():
    soil = SOILS["Organic soil"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.4, 3.6))
    for g, c in zip([0.0, 0.3, 0.5, 1.0], ["#4a7a3a", "#2b6ca3", "#c8811b", "#8a3a3a"]):
        V = dict(VEH); V["gamma"] = g
        r = evaluate(a, soil, V); o = optimum(soil, V)
        ax1.plot(a, r["K"], lw=2, color=c, label=r"$\gamma=%.1f$" % g)
        ax2.plot(a, r["P_tot"]/1e3, lw=2, color=c, label=r"$\gamma=%.1f$" % g)
        if o["a_opt"] is not None:
            ax2.plot([o["a_opt"]], [o["P_tot_opt"]/1e3], "o", ms=5.5, color=c)
    ax1.axhline(1.0, color="k", ls="--", lw=1.2)
    ax1.text(.03, 1.08, r"$K_{TR}=1$", fontsize=8)
    ax1.set_xlabel(r"load-relief fraction $\alpha$ (-)")
    ax1.set_ylabel(r"$K_{TR}$ (-)"); ax1.set_xlim(0, .9); ax1.set_ylim(0, 3.0)
    ax1.set_title("(a) mobility feasibility", fontsize=9)
    ax1.legend(frameon=False, fontsize=8, title=r"$A_w\propto(1-\alpha)^{\gamma}$",
               title_fontsize=8)
    ax2.set_xlabel(r"load-relief fraction $\alpha$ (-)")
    ax2.set_ylabel("total power (kW)"); ax2.set_xlim(0, .9); ax2.set_ylim(0, 75)
    ax2.set_title("(b) power demand", fontsize=9)
    save(fig, "fig8_gamma")


def fig_crosscheck():
    """Fig. 10: cross-comparison with independent published formulations."""
    aa = np.linspace(0, 0.9, 200)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.4, 3.6))
    Vp = dict(VEH); Vp["wheel"] = "plate"
    Vr = dict(VEH); Vr["wheel"] = "rigid"
    for name, s_ in SOILS.items():
        ax1.plot(aa, sinkage(aa, s_, Vp)[0], lw=2, color=COL[name], label=name)
        ax1.plot(aa, sinkage(aa, s_, Vr)[0], lw=1.4, ls="--", color=COL[name])
    ax1.plot([], [], color="#555555", lw=2, label="flat plate (this work)")
    ax1.plot([], [], color="#555555", lw=1.4, ls="--", label="Bekker rigid wheel")
    ax1.set_xlabel(r"load-relief fraction $\alpha$ (-)")
    ax1.set_ylabel(r"rut depth $z$ (m)")
    ax1.set_xlim(0, .9); ax1.set_ylim(0, .65)
    ax1.set_title("(a) sinkage branch", fontsize=9)
    ax1.legend(frameon=False, fontsize=7.5)

    for name, s_ in SOILS.items():
        cn, wl, ow = [], [], []
        for al in aa:
            r = evaluate(al, s_)
            W = VEH["G"] * (1 - al)
            mr = (float(r["F_def"]) + float(r["F_roll"])) / W
            if mr <= 0.045:
                continue
            C = 1.2 / (mr - 0.04)
            cn.append(C)
            wl.append(0.75 * (1 - np.exp(-0.3 * C * VEH["s"])))
            ow.append(float(r["F_x"]) / W)
        ax2.plot(cn, ow, lw=2, color=COL[name], label=name)
        ax2.plot(cn, wl, lw=1.4, ls="--", color=COL[name])
    ax2.axvspan(0, 5, color="#e6e0d2", alpha=.7)
    ax2.text(2.5, 0.86, "outside\nWismer-Luth\nrange", ha="center", fontsize=7.5,
             color="#6b6250")
    ax2.plot([], [], color="#555555", lw=2, label="this work")
    ax2.plot([], [], color="#555555", lw=1.4, ls="--", label="Wismer-Luth")
    ax2.set_xscale("log"); ax2.set_xlim(1.5, 120); ax2.set_ylim(0, 1.0)
    ax2.set_xlabel(r"implied wheel numeric $C_n$ (-)")
    ax2.set_ylabel(r"gross traction ratio $F_x/W$ (-)")
    ax2.set_title("(b) traction branch, $s=0.25$", fontsize=9)
    ax2.legend(frameon=False, fontsize=7.5, loc="lower right")
    save(fig, "fig10_crosscheck")


def fig_speed():
    soil = SOILS["Organic soil"]
    fig, ax = plt.subplots(figsize=(6.0, 3.6))
    for v, c in zip([2.5, 5.0, 7.5, 10.0], ["#2b6ca3", "#4a7a3a", "#c8811b", "#8a3a3a"]):
        V = dict(VEH); V["v"] = v
        r = evaluate(a, soil, V); o = optimum(soil, V)
        ax.plot(a, r["P_tot"]/1e3, lw=2, color=c, label=r"$v=%.1f$ m/s" % v)
        if o["a_opt"] is not None:
            ax.plot([o["a_opt"]], [o["P_tot_opt"]/1e3], "o", ms=5.5, color=c)
    ax.set_xlabel(r"load-relief fraction $\alpha$ (-)")
    ax.set_ylabel("total power (kW)"); ax.set_xlim(0, .9); ax.set_ylim(0, 120)
    ax.legend(frameon=False, fontsize=8)
    save(fig, "fig9_speed")


# ----------------------------------------------------------------------
if __name__ == "__main__":
    print("=== VERIFICATION ===")
    for d, got, exp, ok in verification():
        print(f"  [{'OK ' if ok else 'FAIL'}] {d:48s} got={got:12.5g} exp={exp:12.5g}")

    print("\n=== RESULTS ===")
    print(f"{'a':>5} {'z,m':>7} {'Fdef':>7} {'Froll':>7} {'Fskirt':>7} {'Fres':>8} "
          f"{'Fx':>8} {'K':>6} {'Pprop':>7} {'Pfan':>7} {'Ptot':>7}")
    rows = {}
    for name, s in SOILS.items():
        rows[name] = []; print(f"-- {name}")
        for av in [0.0, .2, .4, .5, .6, .8]:
            r = evaluate(av, s)
            v_ = [av, float(r['z']), float(r['F_def']), float(r['F_roll']),
                  float(r['F_skirt']), float(r['F_res']), float(r['F_x']), float(r['K']),
                  float(r['P_prop'])/1e3, float(r['P_fan'])/1e3, float(r['P_tot'])/1e3]
            rows[name].append(v_)
            print(f"{v_[0]:5.2f} {v_[1]:7.3f} {v_[2]:7.0f} {v_[3]:7.0f} {v_[4]:7.0f} "
                  f"{v_[5]:8.0f} {v_[6]:8.0f} {v_[7]:6.2f} {v_[8]:7.2f} {v_[9]:7.2f} {v_[10]:7.2f}")

    print("\n=== OPTIMA ===")
    opts = {}
    for name, s in SOILS.items():
        o = optimum(s); opts[name] = o
        print(f"  {name:14s} a_trac={o['a_trac']} a_geom={o['a_geom']} a_min={o['a_min']} "
              f"a*={o['a_opt']:.3f} band={[round(x,3) for x in o['band']]} K*={o['K_opt']:.2f} "
              f"z*={o['z_opt']:.3f} Ptot*={o['P_tot_opt']/1e3:.1f} kW "
              f"(Pfan*={o['P_fan_opt']/1e3:.1f}; a=0: {o['P_tot0']/1e3:.1f} kW, K0={o['K0']:.2f})")

    print("\n=== SENSITIVITY: SOIL (+-15 %) ===")
    base, rs = sens_soil(SOILS["Organic soil"]); print(f"  base a* = {base:.3f}")
    for k, lo, hi, d in rs:
        print(f"  {k:8s} -: {lo:.3f}  +: {hi:.3f}  max|d|={d:.3f}")

    print("\n=== SENSITIVITY: SYSTEM ===")
    base2, rs2 = sens_system(SOILS["Organic soil"])
    for k, d, lo, hi, m in rs2:
        print(f"  {k:9s} +-{d*100:4.0f}%  -: {lo:.3f}  +: {hi:.3f}  max|d|={m:.3f}")

    print("\n=== SPEED SWEEP ===")
    sp = speed_sweep(SOILS["Organic soil"])
    for v, amin, aopt, pop, p0, band in sp:
        print(f"  v={v:5.1f}  a_min={amin:.3f} a*={aopt:.3f} "
              f"band=[{band[0]:.2f},{band[1]:.2f}] Ptot*={pop:.1f} kW (a=0: {p0:.1f} kW)")

    print("\n=== CONTACT-AREA SCENARIOS ===")
    gm = gamma_sweep(SOILS["Organic soil"])
    for g, z0, z8, kmax, atr, age, amin, aopt, pop in gm:
        fm = lambda x: "  --  " if x is None else f"{x:.3f}"
        fp = lambda x: " -- " if x is None else f"{x:.1f}"
        print(f"  gamma={g:.1f} z(0)={z0:.3f} z(0.8)={z8:.3f} maxK={kmax:.2f} "
              f"a_trac={fm(atr)} a_geom={fm(age)} a_min={fm(amin)} a*={fm(aopt)} "
              f"Ptot*={fp(pop)}")

    print("\n=== CROSS-CHECK: SINKAGE (plate vs Bekker rigid wheel) ===")
    for nm, al, zp, zr, ratio in crosscheck_sinkage():
        print(f"  {nm:13s} a={al:.1f} z_plate={zp:.3f} z_rigid={zr:.3f} ratio={ratio:.2f}")

    print("\n=== CROSS-CHECK: TRACTION (Wismer-Luth) ===")
    for row in crosscheck_traction():
        nm, al, mr, C, wl, ow, d = row
        if C is None:
            print(f"  {nm:13s} a={al:.1f} MR/W={mr:.3f} below Wismer-Luth floor")
        else:
            print(f"  {nm:13s} a={al:.1f} MR/W={mr:.3f} Cn={C:6.2f} "
                  f"WL={wl:.3f} model={ow:.3f} diff={d:+7.1f}%")

    print("\n=== ROBUSTNESS: SINKAGE RELATION ===")
    for nm, w, amin, aopt, p in robustness_wheel_model():
        f = lambda x, k=".3f": "  --  " if x is None else format(x, k)
        print(f"  {nm:13s} {w:6s} a_min={f(amin)} a*={f(aopt)} Ptot*={f(p, '.1f')}")

    print("\n=== MONTE CARLO ===")
    mc15 = monte_carlo(SOILS["Organic soil"], N=1500, spread=0.15)
    mc30 = monte_carlo(SOILS["Organic soil"], N=1500, spread=0.30, seed=11)
    mcsys = monte_carlo(SOILS["Organic soil"], N=1500, spread=0.15, seed=23, system=True)
    for tag, mc in [("soil +-15%", mc15), ("soil +-30%", mc30), ("soil+system +-15%", mcsys)]:
        print(f"  {tag:18s} N={mc['n']:4d} infeas={mc['infeasible']:3d} "
              f"a* {mc['opt_med']:.3f} CI[{mc['opt_ci'][0]:.3f},{mc['opt_ci'][1]:.3f}] "
              f"a_min {mc['min_med']:.3f} CI[{mc['min_ci'][0]:.3f},{mc['min_ci'][1]:.3f}]")

    fig_sinkage(); fig_forces(); fig_ratio(); fig_power(); fig_surface()
    fig_mc(mc15, mc30); fig_gamma(); fig_speed(); fig_crosscheck()

    json.dump({"rows": rows, "opts": opts, "sens_soil": rs, "sens_sys": rs2,
               "speed": sp, "gamma": gm,
               "mc": {t: {k: v for k, v in m.items() if k != "samples"}
                      for t, m in [("s15", mc15), ("s30", mc30), ("sys15", mcsys)]},
               "veh": VEH, "soils": SOILS}, open("results.json", "w"), indent=1)
    print("\nDone: fig/*.pdf, fig/*.png, results.json")
