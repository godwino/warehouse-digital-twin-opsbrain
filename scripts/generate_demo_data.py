from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.config.settings import ScenarioConfig
from src.data.pipeline import build_synthetic_dataset


def main() -> None:
    scenario = ScenarioConfig(name="normal_operations", horizon_days=120, random_seed=42)
    bundle = build_synthetic_dataset(scenario)
    print("Generated tables:")
    for name, frame in bundle.to_dict().items():
        print(f" - {name}: {len(frame):,} rows")


if __name__ == "__main__":
    main()
