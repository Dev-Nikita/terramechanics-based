"""Original schematic of the air-cushion-assisted wheeled vehicle (Fig. 1).
Drawn from scratch; no third-party image rights are involved."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrow, Circle, FancyBboxPatch
import os

os.makedirs("fig", exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                     "figure.dpi": 300, "savefig.bbox": "tight"})

fig, ax = plt.subplots(figsize=(6.8, 3.4))
ax.set_xlim(-0.55, 4.75); ax.set_ylim(-1.45, 2.65); ax.axis("off"); ax.set_aspect("equal")

ink, soft, mid = "#22292b", "#e9eef0", "#9aa7ab"
G0, RUT = 0.0, -0.14

# ---------------- terrain ----------------
ax.fill_between([-0.55, 4.75], -0.72, G0, color="#f0ebde", zorder=0)
ax.plot([-0.55, 4.75], [G0, G0], color=mid, lw=1.1, zorder=1)
for xc in (0.95, 2.95):
    ax.fill_between([xc - 0.26, xc + 0.26], RUT, G0, color="#dcd3bd", zorder=1)
    ax.plot([xc - 0.26, xc - 0.26, xc + 0.26, xc + 0.26],
            [G0, RUT, RUT, G0], color="#b9ae93", lw=0.9, zorder=2)
ax.annotate("", xy=(3.19, RUT), xytext=(3.19, G0),
            arrowprops=dict(arrowstyle="<->", lw=0.9, color="#7d7259"), zorder=3)
ax.text(3.30, RUT / 2 + 0.01, r"$z$", fontsize=9.5, color="#5f5742", va="center", zorder=4,
        bbox=dict(fc="white", ec="none", pad=0.6))
ax.text(2.00, -0.62, "deformable terrain", ha="center", fontsize=8, color="#7d7259")

# ---------------- hull ----------------
ax.add_patch(FancyBboxPatch((0.35, 0.70), 3.30, 1.00,
                            boxstyle="round,pad=0.02,rounding_size=0.10",
                            fc=soft, ec=ink, lw=1.6, zorder=3))
ax.add_patch(Rectangle((0.72, 0.88), 1.90, 0.62, fc="white", ec=ink,
                       lw=1.0, ls=(0, (4, 2)), zorder=4))
ax.text(1.67, 1.19, "plenum chamber", ha="center", va="center", fontsize=8.5, zorder=5)

# ---------------- lift fan ----------------
fx, fy, fr = 3.16, 1.20, 0.26
ax.add_patch(Circle((fx, fy), fr, fc="white", ec=ink, lw=1.5, zorder=5))
for dx, dy in ((fr * .85, 0), (fr * .42, fr * .74), (-fr * .42, fr * .74)):
    ax.plot([fx - dx, fx + dx], [fy - dy, fy + dy], color=ink, lw=1.1, zorder=6)
ax.annotate("", xy=(2.66, 1.20), xytext=(2.90, 1.20),
            arrowprops=dict(arrowstyle="->", lw=1.1, color="#2b6ca3"), zorder=6)

# ---------------- skirt ----------------
for xs in (0.30, 3.70):
    ax.plot([xs, xs], [0.70, 0.12], color=ink, lw=3.0, solid_capstyle="round", zorder=6)
ax.plot([0.30, 3.70], [0.12, 0.12], color=ink, lw=0.9, ls=(0, (2, 3)), zorder=4)
ax.annotate("", xy=(0.30, 0.12), xytext=(0.30, G0),
            arrowprops=dict(arrowstyle="<->", lw=0.9, color="#2b6ca3"), zorder=7)
ax.text(0.19, 0.06, r"$h_g$", fontsize=9.5, ha="right", color="#1f4f7a", zorder=7)

# ---------------- cushion pressure ----------------
for x in (0.75, 1.30, 1.85, 2.40, 2.95, 3.45):
    ax.add_patch(FancyArrow(x, 0.18, 0, 0.34, width=0.013, head_width=0.08,
                            head_length=0.10, fc="#4a7a3a", ec="#4a7a3a", zorder=5))
ax.text(2.13, 0.36, r"$\Delta p,\;F_{ac}$", ha="center", va="center", fontsize=10,
        color="#2f4f2f", zorder=8, bbox=dict(fc="white", ec="none", pad=1.5))

# ---------------- peripheral leakage ----------------
for xj, d in ((0.30, -1), (3.70, 1)):
    ax.add_patch(FancyArrow(xj + 0.02 * d, 0.06, 0.34 * d, -0.06, width=0.009,
                            head_width=0.06, head_length=0.08,
                            fc="#2b6ca3", ec="#2b6ca3", zorder=7))
ax.text(4.16, -0.02, r"leakage $Q$", fontsize=8.5, color="#1f4f7a", va="center")

# ---------------- wheels ----------------
for xc in (0.95, 2.95):
    ax.add_patch(Circle((xc, 0.30), 0.30, fc="white", ec=ink, lw=1.9, zorder=8))
    ax.add_patch(Circle((xc, 0.30), 0.10, fc=mid, ec=ink, lw=1.0, zorder=9))
    ax.add_patch(FancyArrow(xc, -0.66, 0, 0.22, width=0.013, head_width=0.08,
                            head_length=0.10, fc="#b03030", ec="#b03030", zorder=8))
    ax.text(xc, -0.92, r"$W_w$", ha="center", fontsize=9.5, color="#7a2020", zorder=9)

# ---------------- global forces ----------------
ax.add_patch(FancyArrow(2.00, 2.44, 0, -0.46, width=0.015, head_width=0.09,
                        head_length=0.11, fc=ink, ec=ink))
ax.text(2.12, 2.32, r"$G$", fontsize=10.5)
ax.add_patch(FancyArrow(0.55, 2.10, 0.55, 0, width=0.015, head_width=0.09,
                        head_length=0.11, fc="#c8811b", ec="#c8811b"))
ax.text(0.55, 2.24, r"$F_x$", fontsize=9.5, color="#8a5a12")
ax.add_patch(FancyArrow(3.55, 2.10, -0.55, 0, width=0.015, head_width=0.09,
                        head_length=0.11, fc="#b03030", ec="#b03030"))
ax.text(3.55, 2.24, r"$F_{res}$", fontsize=9.5, color="#7a2020", ha="right")

# ---------------- numbered callouts ----------------
lead = dict(arrowprops=dict(arrowstyle="-", lw=0.8, color="#5a6467"), fontsize=9.5,
            weight="bold", ha="center", va="center",
            bbox=dict(boxstyle="circle,pad=0.20", fc="white", ec=ink, lw=0.9))
ax.annotate("1", xy=(1.05, 1.70), xytext=(0.70, 2.02), **lead)
ax.annotate("2", xy=(3.16, 0.20), xytext=(3.66, -0.62), **lead)
ax.annotate("3", xy=(0.74, 0.20), xytext=(0.24, -0.62), **lead)
ax.annotate("4", xy=(3.70, 0.44), xytext=(4.22, 0.62), **lead)
ax.annotate("5", xy=(3.16, 1.46), xytext=(3.16, 1.94), **lead)

# ---------------- cushion span ----------------
ax.annotate("", xy=(0.30, -1.26), xytext=(3.70, -1.26),
            arrowprops=dict(arrowstyle="<->", lw=0.9, color="#5a6467"))
ax.text(2.00, -1.20, r"cushion planform area $A_{ac}$, skirt perimeter $L_p$",
        ha="center", va="bottom", fontsize=8.5, color="#4f585b",
        bbox=dict(fc="white", ec="none", pad=1.0))

fig.savefig("fig/fig1b_schematic.pdf"); fig.savefig("fig/fig1b_schematic.png")
print("written")
