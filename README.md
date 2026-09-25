# Six-case report-constrained hydro-topological stress experiment

**Executed computational supplement for a Lapasan-motivated thesis.**

The six cases are CDO, Tondano–Tikala/Manado, Batang Kuranji/Padang, Huong/Hue,
Kadamaian–Panataran/Kota Belud, and U-Tapao–Khlong Wat/Hat Yai.

## Start here

Open `deliverables/SEA_Topology_Executed_Methods_and_Results.pdf` (18 pages) for
methods, completed results, counterexamples, and six graph schematics. The DOCX
is editable. Open `deliverables/SEA_Topology_Simulation_Explorer.html` in a web
browser; it is self-contained and requires no Internet connection or Python.
`deliverables/SEA_Topology_Key_Results.csv` is a six-row numerical summary.

### Essential interpretation

- Networks are manually encoded **coarse models constrained by the uploaded
  reports**, NOT surveyed or complete GIS drainage networks. Unresolved source
  order/aggregation is labelled in each graph and the evidence register.
- Source amount is always 100 abstract units per event. A tick is not an hour.
  Capacity, storage, release time, source activation, and onset distributions are
  explicitly synthetic parameters, not measured local conditions.
- Routing is conservative and forward-only. There is no hydraulic water level,
  backwater propagation, local flood depth, actual rainfall calibration, or
  neighbourhood-scale flood map.
- Overflow is a **standalone finite-buffer diagnostic at an observation point**.
  The probes do not feed spill back into the upstream routing. Urban and receiver
  probes are alternative independent diagnostic placements, not two parts of one
  coupled flood simulation. NEVER add their spill volumes together.
- The CDO receiver is NOT renamed Lapasan. Proximity alone does not establish
  a flow edge or overbank pathway into Barangay Lapasan.
- The reports' underlying primary-source claims were not independently verified
  in this execution. Source files are fingerprinted in `source_manifest.json`.
  No government-restricted records were requested or silently assumed.

## Principal findings

Paired zero-onset versus staggered-onset tests raised mean receiver spill in all
six neutral-control models, but some individual comparisons reversed. For CDO,
three balanced alternatives averaged 20.49% spill versus 18.39% for the supplied
coarse sequential reference; the effect was not invariant and the reference was
not uniquely most susceptible. Uncertain confluence order, source-to-target
position, storage functions, and shared outlet restrictions alter results.

These are conditional within-model mechanisms. They are not proof of inevitable
flooding, actual cross-city flood probabilities, or geographical validation of
Lapasan. See report pages 5–11, including the counterexamples.

## Reproduce the numerical experiment

Tested interpreter: Python 3.13.5 on Linux. Exact installed scientific-package
versions are pinned in `requirements.txt`. Other operating systems/interpreters
were not tested. Python 3.13 with compatible wheels is recommended for exact
reproduction; these are tested versions, not a claim about latest releases.

On Windows in an extracted project folder:

```text
py -3.13 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python run_all.py
```

On Linux/macOS:

```text
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run_all.py
```

The commands need Internet only to install Python packages if they are not
already available. Once installed, simulation uses only the included code and
coarse specifications. Raw source PDFs are not needed to rerun these numerical
models. They ARE needed to audit whether the encoded connections are justified.
The original uploaded PDFs are not repackaged here; full filenames, hashes and
source-page references are included.

`python run_all.py --checks-only` runs the 26 numerical/property checks. The full
command regenerates existing numerical CSVs; back up changed results first. It
does not automatically rewrite the supplied report or HTML. Runtime depends on
hardware and Numba compilation. No background service or network access is used.

### Optional visual regeneration

```text
python -m pip install -r requirements_visuals.txt
python code/make_figures.py
python code/make_report.py
python code/make_viewer.py
```

The latter two scripts save the DOCX and HTML **one folder above the project
root**, as in the original execution. Rendering DOCX to PDF requires a separate
Word/PDF renderer and was visually checked during the supplied execution. The
browser test also requires Node.js, Playwright and Chromium and is not required
for the scientific simulation.

## Module counts (do not treat as independent observations)

- Six reference models, including the two named-storage sweeps: 11,520 routes.
- Three known area-partition sensitivity sets: 1,728 routes.
- CDO: 15 labelled binary arrangements, 17,280 routes; only two unlabelled shapes.
- Kadamaian: three labelled pairings, 3,456 routes.
- Huong: two source-position variants, 2,304 routes.
- Kuranji: 105 labelled binary refinements × 72 fixed scenarios = 7,560 routes;
  only three unlabelled shapes, not 105 observed watersheds.
- Main total: 43,848 routes and 616,032 capacity/buffer evaluations.
- Additional strictly paired timing module: 6,144 routes, 36,864 paired rows,
  equivalent to 73,728 capacity/buffer evaluations.
- Equal-budget outlet module: 82,944 evaluations; it re-routes 1,152 existing
  Hat Yai reference inputs for implementation convenience, not new independent
  scenarios.
- Combined main/control/paired routing evaluations: **49,992**, excluding that
  repeated outlet-input computation and numerical unit checks.
- Combined capacity/buffer evaluations: **772,704**.

Random seeds and scenario IDs are fixed; equal weighting of this chosen scenario
grid does NOT give real-world event probabilities. Four realizations in the
factorial grid are not four independent geographical samples.

## Files and audit trail

- `code/model.py`: graph definitions, source generator, conservative routing,
  queue, exhaustive labelled-tree generator, descriptors.
- `inputs/*_graph.json`: exported copies of the six exact reference specifications.
  The executable source of those specifications is `reference_specs()` in
  `code/model.py`; edit that function (not only an exported JSON) to change a
  graph and regenerate the study.
- `inputs/alternative_graphs.json`: all counterfactual/refinement specifications.
- `inputs/edge_evidence_register.csv`: source pages and uncertainty status for
  every coarse edge.
- `inputs/node_register.csv`: source labels, roles and control nodes.
- `inputs/source_manifest.json`: uploaded filenames, pages, SHA-256 fingerprints.
- `inputs/scenario_grid.csv`: 1,152 source/routing factor settings.
- `results/routing_audit.csv.gz`: weights, starts, active masks, whole-routing
  mass balance for every main run.
- `results/probe_results.csv.gz`: complete main probe outcomes, not just averages.
- `results/paired_timing_results.csv.gz`: strictly paired onset interventions.
- `results/node_metrics.csv.gz`: source-tagged arrival diagnostics.
- `results/outlet_counterfactuals.csv.gz`: equal-budget/common-boundary tests.
- `results/*summary*.csv`, `*paired.csv`, `computed_findings.json`: aggregates.
- `results/counterexamples_*.csv`: reverse-sign examples retained deliberately.
- `results/validation.json`, `viewer_validation.json`: executed numerical checks.
- `results/viewer_series.json`: selected equal-input/unit-delay demonstration
  series, not the full factor grid. Browser capacity/buffer calculations are live.
- `figures/`: six result figures and six coarse, non-geographic graph drawings.

See `DATA_DICTIONARY.md` for field definitions. A `FILE_MANIFEST_SHA256.csv`
allows content-integrity checking. Gzip archive bytes and timing logs can differ
between reruns even when the numerical CSV values are reproduced.

## Validation achieved and absent

All 26 core checks passed. Main routing/probe absolute water-accounting errors
were below 1e-12 abstract units. Selected 512/1024-tick horizon checks agree;
positive-capacity main probe buffers finish empty. The exact CDO alternative
clone matches the reference, and equal-budget one/two-route unrestricted results
match. The HTML queue matched Python for 1,440 cases with zero numeric difference.
All six HTML selections were checked in Chromium; desktop/mobile layouts had no
page errors or mobile horizontal overflow in that test.


