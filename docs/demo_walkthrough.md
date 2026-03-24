# Demo Walkthrough

This walkthrough is designed for a hiring manager, portfolio reviewer, or warehouse stakeholder who wants to understand the platform quickly.

## 1. Business Story

The product is framed around a common warehouse control problem: inbound volume, labor availability, and dock capacity are all moving at the same time, and managers need faster answers than spreadsheets usually provide.

HVDC OpsBrain addresses that by combining four decision layers:

1. Forecast likely workload.
2. Optimize the operating plan.
3. Simulate whether that plan holds up under resource contention.
4. Convert the outputs into concrete recommendations.

## 2. What To Show In The App

Start with the Executive Overview:

- Show service level, wait time, utilization, and throughput in one screen.
- Call out the recommendation table as the business-facing output.

Move to Forecasting:

- Explain that daily volume, hourly workload, labor demand, and congestion are predicted separately.
- Point to the evaluation table and explain that the synthetic nature of the data can make baseline patterns highly learnable.

Move to Dock Optimization:

- Show that inbound trucks are assigned to recommended docks under limited capacity.
- Explain that the current optimizer is a clean MVP foundation that can accept richer constraints.

Move to Simulation / Scenario Lab:

- Increase inbound volume or reduce dock capacity.
- Show the resulting change in truck wait distribution and bottleneck frequency.

Finish with Recommendations:

- Tie the operating signal back to a business action like adding workers, pre-staging labor, or rescheduling loads.

## 3. Practical Talking Points

- The codebase is modular so each engine can be tested independently.
- The system is config-driven and reproducible with seedable synthetic data.
- The app is built to support “what-if” scenario evaluation, not just passive reporting.
- Outputs are exportable for downstream analysis or presentation.

## 4. Suggested Next Upgrades

- Add richer dock compatibility and appointment window constraints.
- Introduce probabilistic forecast intervals.
- Expand the digital twin to outbound picking and shipping.
- Add scenario comparison history and persistent saved runs.
