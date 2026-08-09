# terramechanics-based
# Air-cushion-assisted wheeled vehicle on deformable terrain

Reproduction code for the paper

> A. Bokhonko, R. Zinko, N. Tarasov. *Terramechanics-based evaluation of an
> air-cushion-assisted wheeled vehicle on deformable terrain: feasibility limits
> and the energy-optimal load-relief fraction.* Submitted to the Journal of
> Terramechanics.

## What this repository contains

| File | Purpose |
|---|---|
| `terramechanics_model.py` | The complete model. Reproduces every figure, table and number in the paper and the supplementary material. |
| `fig1_schematic.py` | Draws the force and flow schematic (Fig. 2 of the paper). |
| `results.json` | Machine-readable dump of all computed values. |

There are no experimental data. The study is analytical and numerical, and this
repository is the whole of it.

## Reproducing the paper

```
python3 -m pip install numpy matplotlib
python3 terramechanics_model.py
python3 fig1_schematic.py
```

Runtime is under two minutes on a laptop. Output goes to `fig/` (PDF and PNG)
and `results.json`, and the console log prints the limit-case verification, the
force-balance tables, the optima, both sensitivity studies, the speed sweep, the
contact-patch scenarios, the cross-comparisons and the Monte-Carlo intervals in
the order they appear in the paper.

## Changing the configuration

Every reported number derives from two dictionaries at the top of
`terramechanics_model.py`:

- `VEH` — vehicle, cushion and driveline parameters (Table 1 of the paper);
- `SOILS` — Bekker and shear parameters for the three terrain classes
  (Table 2 of the paper).

Edit either and re-run. Nothing else needs to be touched.

## Model structure

- `sinkage`, `compaction_resistance` — Bekker pressure–sinkage, with a switch
  between the flat-plate idealisation and the closed-form rigid-wheel relation.
- `traction` — Janosi–Hanamoto shear integrated over the contact patch.
- `cushion` — lumped peripheral-jet lift model and fan power.
- `evaluate` — assembles the force and power balance at a given load relief.
- `optimum` — constrained minimisation of total power subject to the
  traction-to-resistance and rut-depth constraints.
- `verification` — the seven analytical limit cases of Table S1.
- `crosscheck_sinkage`, `crosscheck_traction`, `robustness_wheel_model` —
  the independent comparisons of Section 6.
- `sens_soil`, `sens_system`, `speed_sweep`, `gamma_sweep`, `monte_carlo` —
  the uncertainty studies of Sections 5 and 7.

## License

Released under the MIT License. If you use this code, please cite the paper.

## Acknowledgement of tooling

GitHub Copilot was used as a coding assistant during development. All model
equations, parameter choices and numerical results were derived, checked and
verified by the authors; see the declaration in the paper.
