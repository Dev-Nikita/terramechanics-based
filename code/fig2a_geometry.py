"""Panel (a) of Fig. 2: longitudinal geometry and vertical force balance.
Original drawing; no third-party image content."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrow, Polygon
import os

os.makedirs("fig", exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                     "figure.dpi": 300, "savefig.bbox": "tight"})

ink, mid = "#22292b", "#9aa7ab"
RED, GRN, BLU, ORG = "#b03030", "#4a7a3a", "#2b6ca3", "#c8811b"

fig, ax = plt.subplots(figsize=(6.9, 3.3))
ax.set_xlim(-0.55, 6.25); ax.set_ylim(-1.45, 2.55); ax.axis("off"); ax.set_aspect("equal")

XR, XF, R = 1.30, 4.20, 0.32
XC = 0.5 * (XR + XF)
CL, CR = XR + 0.82, XF - 0.62
HG = 0.16

# ---------------- ground ----------------
ax.fill_between([-0.55, 5.95], -1.45, 0, color="#f2eee3", zorder=0)
ax.plot([-0.55, 5.95], [0, 0], color=mid, lw=1.2, zorder=1)

# ---------------- body outline ----------------
outline = [(0.52, 0.34), (0.60, 0.88), (1.60, 0.98), (2.30, 1.64), (3.55, 1.68),
           (4.30, 1.00), (5.08, 0.92), (5.14, 0.34)]
ax.add_patch(Polygon(outline, closed=False, fill=False, ec=ink, lw=1.6,
                     ls=(0, (7, 4)), zorder=3))
for x0, x1 in ((0.52, CL), (CR, 5.14)):
    ax.plot([x0, x1], [0.34, 0.34], color=ink, lw=1.6, ls=(0, (7, 4)), zorder=3)

# ---------------- cushion and skirt ----------------
ax.fill_between([CL, CR], HG, 0.34, color="#e8f0e3", zorder=2)
for x in (CL, CR):
    ax.plot([x, x], [0.34, HG], color=ink, lw=2.8, solid_capstyle="round", zorder=4)
ax.plot([CL, CR], [HG, HG], color=ink, lw=0.9, ls=(0, (2, 3)), zorder=4)

# ---------------- ruts under the wheels ----------------
RUT = -0.34
for xc in (XR, XF):
    ax.fill_between([xc - 0.30, xc + 0.30], RUT, 0, color="#dcd3bd", zorder=1)
    ax.plot([xc - 0.30, xc - 0.30, xc + 0.30, xc + 0.30], [0, RUT, RUT, 0],
            color="#b9ae93", lw=1.0, zorder=2)
XZ = XF + 0.78
ax.plot([XF + 0.30, XZ + 0.10], [RUT, RUT], color="#7d7259", lw=0.7,
        ls=(0, (2, 2)), zorder=6)
ax.plot([XF + 0.30, XZ + 0.10], [0, 0], color="#7d7259", lw=0.7,
        ls=(0, (2, 2)), zorder=6)
ax.annotate("", xy=(XZ, RUT), xytext=(XZ, 0),
            arrowprops=dict(arrowstyle="<->", lw=1.0, color="#7d7259"), zorder=9)
ax.text(XZ + 0.12, RUT / 2, r"$z$", fontsize=10.5, ha="left", va="center",
        color="#5f5742", zorder=9)

# ---------------- wheels and wheel reactions ----------------
for x in (XR, XF):
    ax.add_patch(Circle((x, R), R, fc="white", ec=ink, lw=1.8, zorder=6))
    ax.add_patch(Circle((x, R), 0.10, fc=mid, ec=ink, lw=0.9, zorder=7))
    ax.add_patch(FancyArrow(x, 0.03, 0, 0.55, width=0.014, head_width=0.085,
                            head_length=0.10, fc=RED, ec=RED, zorder=8))
    ax.text(x, 0.94, r"$W_w$", fontsize=10, color="#7a2020", ha="center", zorder=9,
            bbox=dict(fc="white", ec="none", pad=1.0))

# ---------------- weight and cushion lift ----------------
ax.plot([XC], [2.36], "o", ms=5.5, mfc="white", mec=ink, mew=1.3, zorder=9)
ax.add_patch(FancyArrow(XC, 2.32, 0, -0.44, width=0.015, head_width=0.09,
                        head_length=0.11, fc=ink, ec=ink, zorder=8))
ax.text(XC + 0.14, 2.16, r"$G$", fontsize=10.5, zorder=8)
ax.add_patch(FancyArrow(XC, 0.22, 0, 0.62, width=0.015, head_width=0.09,
                        head_length=0.11, fc=GRN, ec=GRN, zorder=8))
ax.text(XC + 0.16, 0.70, r"$F_{ac}=\Delta p\,A_{ac}$", fontsize=10.5,
        color="#2f4f2f", zorder=9, bbox=dict(fc="white", ec="none", pad=1.0))

# ---------------- longitudinal forces ----------------
ax.add_patch(FancyArrow(5.05, 2.05, 0.62, 0, width=0.015, head_width=0.09,
                        head_length=0.11, fc=ORG, ec=ORG, zorder=8))
ax.text(5.10, 2.22, r"$F_x$", fontsize=10.5, color="#8a5a12")
ax.add_patch(FancyArrow(0.62, 2.05, -0.62, 0, width=0.015, head_width=0.09,
                        head_length=0.11, fc=RED, ec=RED, zorder=8))
ax.text(0.58, 2.22, r"$F_{res}$", fontsize=10.5, color="#7a2020", ha="right")

# ---------------- direction of travel ----------------
ax.add_patch(FancyArrow(XC - 0.30, 1.42, 0.60, 0, width=0.010, head_width=0.070,
                        head_length=0.090, fc="#5a6467", ec="#5a6467", zorder=8))
ax.text(XC + 0.40, 1.42, r"$v$", fontsize=10.5, color="#3c4548", ha="left",
        va="center", zorder=8)

# ---------------- dimensions ----------------
def dim(x1, x2, y, label, dy):
    ax.annotate("", xy=(x1, y), xytext=(x2, y),
                arrowprops=dict(arrowstyle="<->", lw=0.9, color="#5a6467"))
    ax.text(0.5 * (x1 + x2), y + dy, label, ha="center", va="center",
            fontsize=9.5, color="#3c4548",
            bbox=dict(fc="#f2eee3", ec="none", pad=1.2))

for x in (XR, XF):
    ax.plot([x, x], [-0.62, 0], color=mid, lw=0.7, ls=(0, (3, 3)), zorder=1)
for x in (CL, CR):
    ax.plot([x, x], [-1.16, HG], color=mid, lw=0.7, ls=(0, (3, 3)), zorder=1)

dim(XR, XF, -0.50, r"wheelbase $L_{wb}$", -0.24)
dim(CL, CR, -1.04, r"cushion length $L_{c}$, planform area $A_{ac}$", -0.24)

# skirt clearance, shown with a leader rather than a dimension line
ax.plot([CL + 0.05, CL - 0.34], [HG / 2, 0.56], color=BLU, lw=0.8, zorder=8)
ax.plot([CL + 0.05], [HG / 2], "o", ms=2.6, color=BLU, zorder=9)
ax.text(CL - 0.38, 0.58, r"$h_g$", fontsize=10.5, ha="right", va="center",
        color="#1f4f7a", zorder=10, bbox=dict(fc="white", ec="none", pad=1.2))

fig.savefig("fig/fig2a_geometry.pdf"); fig.savefig("fig/fig2a_geometry.png")
print("written")
