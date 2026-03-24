# Results Snapshot

The local demo artifacts in `outputs/reports/normal_operations/` currently show:

- Service level attainment at `100.0%`
- Average truck wait time at `15.94` minutes
- Average unload time at `86.10` minutes
- Dock utilization at `62%`
- Labor utilization at `99%`
- Throughput of `60` simulated trucks
- Lead recommendation: add `16` workers to swing shift receiving

Interpretation:

- Labor is the strongest pressure point in the current synthetic run.
- The forecasted congestion windows around `05:00` and `18:00` are good candidates for pre-staging labor.
- The operating model is close to labor saturation, which means even modest surges could translate into queue growth quickly.

This snapshot is intentionally lightweight. The detailed CSV outputs remain the source of truth for deeper analysis.
