# Data dictionary and model interpretation

## Identifiers and joins

`case` identifies one report-derived coarse specification: CDO, MANADO, KURANJI,
HUE, KADAMAIAN, HATYAI. A label is not evidence of a complete geographic model.
`variant` distinguishes the reference, labelled binary arrangement, or explicit
source-position counterfactual. `run_id` is unique within the main run table;
`scenario_id` joins `inputs/scenario_grid.csv`. Repeated scenario IDs across cases
implement the common experimental grammar; differing source counts mean that
not every random geographic field can be identical between sites.

`experiment` is reference, area sensitivity, CDO/Kadamaian rewiring, Huong
position, or Kuranji order uncertainty. The stored value is authoritative.
`role` is receiver, urban, or urban_and_receiver. `node` is the graph ID at which
a standalone diagnostic is evaluated. Urban and receiver records sharing a
route are NOT additive parts of a whole-network flood volume.

## Inputs (all uncalibrated unless explicitly provenance-tagged)

`duration`: 2, 8, 24 abstract ticks.
`shape`: block or triangle; normalized to assigned source volume.
`spread`: 0, 8, 24; source onsets sampled within the specified range.
`weights`: equal or randomized positive lognormal source weights.
`activation`: all or a selected subset of approximately 60% of the source groups.
Weights are renormalized after masking, so every event still injects 100 units.
`delay`: unit or heterogeneous logical-link delays (1–4 ticks). Control-only
connector edges have no extra logical delay. These are not measured travel times.
`memory`: 0 or 2; generic conservative link-release memory parameter.
`rep`: four fixed random-realization labels, not independent geographic sites.
`storage_tau`: 0, 2, 8 in primary Manado/Huong sweeps; hypothetical release-time
parameter for named storage functions. No real reservoir rule curve is fitted.
`area_weights`: 1 only for the separate internally consistent source-area tests
in Kuranji/Huong/Kadamaian. Area weights assume equal runoff per area; source
areas are not direct observed discharge. Incompatible published delineations are
not averaged. Exact areas and report pages are retained in the graph metadata.

The strictly paired timing module fixes amounts, active groups, pulse shapes,
route parameters and storage, then moves each original source onset to zero.
It compares these outputs with the corresponding unchanged staggered case.
Simultaneous source onset is not the same as simultaneous arrival downstream.

## Routing and independent probe outcomes

`input_volume`: 100 abstract units per source event (whole model).
`terminal_volume`: total routed amount leaving terminal sinks over the horizon.
`routing_residual`: water still within the conservative routing representation,
including unreleased/travelling remainder.
`mass_error`: absolute accounting residual (not calibrated prediction error).

Each source-tagged routed series at an observation drives its own finite buffer:

```text
available = previous_stored + arriving_amount
released = min(service_capacity, available)
spill = max(0, available - released - buffer_limit)
stored = available - released - spill
```

`capacity`: abstract service units per tick (2, 5, 10, 20 in the main probes).
`buffer`: abstract allowable stored units (0, 10, 30 in the main probes).
`spill`: accumulated excess beyond that buffer after service.
`spill_fraction`: spill / 100, including at urban nodes that receive only a
subset of whole-basin input. Use the denominator explicitly when interpreting
Huong urban versus lagoon values.
`overflow`: 1 if spill exceeds a small numerical tolerance, else 0. Its average
is a fraction of this experimental grid, NOT annual flood probability.
`final_storage`: water still held by the probe at simulation end. A closed
outlet can retain input; water is never deleted to force closure.
`peak_ratio`/`overload_ratio` where present: maximum arriving flow divided by the
assigned capacity; this is not stage or depth.
`first_*`/duration fields where present: discrete tick counts, not real hours.

## Arrival diagnostics

`synchrony` (SI) is max(sum of source-tagged arrivals) divided by the sum of the
individual source-tagged peaks at the same probe. It is an output-derived
quantity, not an independently measured predictor; do not regress it against
its own numerator and claim a new empirical causal law.
Source/path/centrality descriptors are properties of this coarse graph. Source
counts are grouped inflow components, not a census of first-order streams.
A common sink does not prove a unique flood-prone motif: many tree networks have
one sink. Drawing coordinates are schematic layout only, NOT latitude/longitude.

## Summaries and comparisons

`mean_spill_fraction`, `mean_spill`: arithmetic mean of spill / 100 over the stated
scenario cells. `overflow_share`: mean of the binary overflow indicator.
`mean_delta`: paired tested minus baseline spill fraction; multiply by 100 for
percentage points. A 0.075 difference means 7.5 percentage points, not 7.5% of
the baseline. `higher_share`, `lower_share`, `tie_share` retain reverse/zero effects.
`mean_rank`/`median_rank`: rank computed within each common parameter setting,
with ties averaged and 1 meaning least spill. `rank_of_ensemble_mean` instead
ranks the grand mean of each arrangement; it is a different statistic.

Kuranji's 105 refinements exhaust unordered rooted binary arrangements of five
labelled source groups; they comprise three unlabelled shapes. They form a
mathematical uncertainty envelope, NOT 105 observed drainage patterns or a
probabilistically justified confidence interval. Extra merger levels imply extra
logical travel steps under the stated model.

## Output validity boundaries

No elevation/slope is silently converted to a hydraulic speed; no annual rainfall
normal is used as an event hyetograph; no historical bankfull value is treated as
current local capacity. No pixels are converted into a false surveyed map.
Common-downstream effects in the outlet experiment are prescribed service
multipliers, not solved lake stages or backwater fields. Graph/site selection and
source dossiers require their own external audit before publication-level local
claims are made. No p-values or fitted geographic validation skill are supplied.
