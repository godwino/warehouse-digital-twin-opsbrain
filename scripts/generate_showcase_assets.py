from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.config.settings import ScenarioConfig
from src.utils.demo import compare_named_scenarios, run_mvp_pipeline


def _write_svg(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_executive_svg(service_level: float, wait_time: float, throughput: float, top_action: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="760" viewBox="0 0 1400 760">
<rect width="1400" height="760" fill="#eef2f3"/>
<rect x="40" y="36" width="1320" height="150" rx="28" fill="#12343b"/>
<text x="88" y="102" fill="#f7f5ef" font-family="Arial, sans-serif" font-size="44" font-weight="700">HVDC OpsBrain</text>
<text x="88" y="146" fill="#dbe7ea" font-family="Arial, sans-serif" font-size="22">Warehouse digital twin and decision intelligence platform</text>
<rect x="60" y="220" width="290" height="180" rx="22" fill="#ffffff"/>
<rect x="375" y="220" width="290" height="180" rx="22" fill="#ffffff"/>
<rect x="690" y="220" width="290" height="180" rx="22" fill="#ffffff"/>
<rect x="1005" y="220" width="290" height="180" rx="22" fill="#ffffff"/>
<text x="90" y="270" fill="#5a6a70" font-family="Arial, sans-serif" font-size="18">SERVICE LEVEL</text>
<text x="90" y="335" fill="#12343b" font-family="Arial, sans-serif" font-size="46" font-weight="700">{service_level:.1%}</text>
<text x="405" y="270" fill="#5a6a70" font-family="Arial, sans-serif" font-size="18">AVG TRUCK WAIT</text>
<text x="405" y="335" fill="#12343b" font-family="Arial, sans-serif" font-size="46" font-weight="700">{wait_time:.1f} min</text>
<text x="720" y="270" fill="#5a6a70" font-family="Arial, sans-serif" font-size="18">THROUGHPUT</text>
<text x="720" y="335" fill="#12343b" font-family="Arial, sans-serif" font-size="46" font-weight="700">{int(throughput)} trucks</text>
<text x="1035" y="270" fill="#5a6a70" font-family="Arial, sans-serif" font-size="18">LEAD ACTION</text>
<text x="1035" y="325" fill="#12343b" font-family="Arial, sans-serif" font-size="24" font-weight="700">Top recommendation</text>
<foreignObject x="1035" y="338" width="230" height="72">
  <div xmlns="http://www.w3.org/1999/xhtml" style="font-family:Arial,sans-serif;font-size:16px;color:#355159;line-height:1.25;">{top_action}</div>
</foreignObject>
<rect x="60" y="440" width="1240" height="260" rx="24" fill="#ffffff"/>
<text x="90" y="495" fill="#12343b" font-family="Arial, sans-serif" font-size="30" font-weight="700">Decision Cockpit Snapshot</text>
<text x="90" y="535" fill="#355159" font-family="Arial, sans-serif" font-size="20">Use the Streamlit dashboard to explore scenario impacts, bottlenecks, recommendations, and recent run history.</text>
<rect x="90" y="570" width="360" height="18" rx="9" fill="#d8e4e8"/>
<rect x="90" y="570" width="284" height="18" rx="9" fill="#0b5c7a"/>
<text x="90" y="620" fill="#5a6a70" font-family="Arial, sans-serif" font-size="18">Service level signal</text>
<rect x="520" y="570" width="360" height="18" rx="9" fill="#fbe1cc"/>
<rect x="520" y="570" width="164" height="18" rx="9" fill="#f28f3b"/>
<text x="520" y="620" fill="#5a6a70" font-family="Arial, sans-serif" font-size="18">Wait-time pressure</text>
<rect x="950" y="570" width="300" height="18" rx="9" fill="#dae4cf"/>
<rect x="950" y="570" width="205" height="18" rx="9" fill="#7a8b5a"/>
<text x="950" y="620" fill="#5a6a70" font-family="Arial, sans-serif" font-size="18">Throughput posture</text>
</svg>"""


def _build_comparison_svg(wait_delta: float, cycle_delta: float, service_delta: float, scenario_name: str) -> str:
    bars = [
        ("Wait Time", wait_delta, "#f28f3b"),
        ("Cycle Time", cycle_delta, "#0b5c7a"),
        ("Service Level", service_delta * 100, "#7a8b5a"),
    ]
    base_x = 180
    bar_y = [230, 340, 450]
    scale = 18
    pieces = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="760" viewBox="0 0 1400 760">',
        '<rect width="1400" height="760" fill="#f7f5ef"/>',
        '<rect x="40" y="36" width="1320" height="130" rx="28" fill="#0b5c7a"/>',
        '<text x="88" y="98" fill="#f7f5ef" font-family="Arial, sans-serif" font-size="42" font-weight="700">Scenario Comparison</text>',
        f'<text x="88" y="138" fill="#d7eaef" font-family="Arial, sans-serif" font-size="22">Normal operations vs {scenario_name.replace("_", " ")}</text>',
        '<text x="90" y="210" fill="#12343b" font-family="Arial, sans-serif" font-size="28" font-weight="700">KPI delta snapshot</text>',
    ]
    for (label, value, color), y in zip(bars, bar_y):
        width = max(12, int(abs(value) * scale))
        pieces.append(f'<text x="90" y="{y+8}" fill="#355159" font-family="Arial, sans-serif" font-size="22">{label}</text>')
        pieces.append(f'<rect x="{base_x}" y="{y-18}" width="520" height="36" rx="18" fill="#dde7ea"/>')
        pieces.append(f'<rect x="{base_x}" y="{y-18}" width="{width}" height="36" rx="18" fill="{color}"/>')
        pieces.append(f'<text x="730" y="{y+8}" fill="#12343b" font-family="Arial, sans-serif" font-size="24" font-weight="700">{value:.2f}</text>')
    pieces.extend(
        [
            '<rect x="820" y="220" width="470" height="340" rx="24" fill="#ffffff"/>',
            '<text x="860" y="280" fill="#12343b" font-family="Arial, sans-serif" font-size="30" font-weight="700">What changed</text>',
            '<text x="860" y="330" fill="#355159" font-family="Arial, sans-serif" font-size="20">Compare baseline against stressed scenarios with KPI deltas, stage bottleneck shifts, and recommendation changes.</text>',
            '<text x="860" y="420" fill="#5a6a70" font-family="Arial, sans-serif" font-size="18">Use the Streamlit comparison page for the full side-by-side analysis.</text>',
            '</svg>',
        ]
    )
    return "".join(pieces)


def main() -> None:
    assets_dir = ROOT / "docs" / "assets"
    baseline = run_mvp_pipeline(ScenarioConfig())
    comparison = compare_named_scenarios("normal_operations", "labor_shortage")

    kpi_map = {row["kpi"]: row["value"] for _, row in baseline.simulation.kpis.iterrows()}
    executive_svg = _build_executive_svg(
        service_level=kpi_map["service_level_attainment"],
        wait_time=kpi_map["average_truck_wait_time"],
        throughput=kpi_map["throughput"],
        top_action=baseline.recommendations.iloc[0]["recommendation"],
    )
    comparison_map = comparison.kpi_delta.set_index("kpi")
    comparison_svg = _build_comparison_svg(
        wait_delta=float(comparison_map.loc["average_truck_wait_time", "delta"]),
        cycle_delta=float(comparison_map.loc["average_total_cycle_time", "delta"]),
        service_delta=float(comparison_map.loc["service_level_attainment", "delta"]),
        scenario_name=comparison.comparison_name,
    )

    _write_svg(assets_dir / "executive_snapshot.svg", executive_svg)
    _write_svg(assets_dir / "scenario_comparison_snapshot.svg", comparison_svg)
    print(f"Showcase assets saved to: {assets_dir}")


if __name__ == "__main__":
    main()
