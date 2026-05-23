from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.config import REPORTS_DIR  # noqa: E402
from src.expected_actual import (  # noqa: E402
    build_deviation_summary,
    build_expected_actual_table,
    build_top_cases,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run expected vs actual fee control engine.")

    parser.add_argument("--input-dir", default="data/raw/tiny")
    parser.add_argument("--top-n", type=int, default=100)

    return parser.parse_args()


def read_csv(input_dir: Path, filename: str) -> pd.DataFrame:
    path = input_dir / filename

    if not path.exists():
        raise FileNotFoundError(f"Required input file not found: {path}")

    return pd.read_csv(path)


def main() -> None:
    args = parse_args()

    input_dir = Path(args.input_dir)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    operations = read_csv(input_dir, "operations.csv")
    tariff_rules = read_csv(input_dir, "tariff_rules.csv")
    actual_charges = read_csv(input_dir, "actual_charges.csv")

    expected_actual = build_expected_actual_table(
        operations=operations,
        tariff_rules=tariff_rules,
        actual_charges=actual_charges,
    )

    summary_by_product = build_deviation_summary(expected_actual, ["product_type"])
    summary_by_channel = build_deviation_summary(expected_actual, ["channel"])
    summary_by_segment = build_deviation_summary(expected_actual, ["client_segment"])
    summary_by_product_channel = build_deviation_summary(expected_actual, ["product_type", "channel"])
    top_cases = build_top_cases(expected_actual, n=args.top_n)

    expected_actual_path = REPORTS_DIR / "expected_actual_operation_level.csv"
    product_path = REPORTS_DIR / "fee_deviation_by_product.csv"
    channel_path = REPORTS_DIR / "fee_deviation_by_channel.csv"
    segment_path = REPORTS_DIR / "fee_deviation_by_segment.csv"
    product_channel_path = REPORTS_DIR / "fee_deviation_by_product_channel.csv"
    top_cases_path = REPORTS_DIR / "top_potential_loss_cases.csv"

    expected_actual.to_csv(expected_actual_path, index=False)
    summary_by_product.to_csv(product_path, index=False)
    summary_by_channel.to_csv(channel_path, index=False)
    summary_by_segment.to_csv(segment_path, index=False)
    summary_by_product_channel.to_csv(product_channel_path, index=False)
    top_cases.to_csv(top_cases_path, index=False)

    print("Expected vs actual summary")
    print(summary_by_product.head(20))
    print()
    print("Top potential loss cases")
    print(top_cases.head(20))
    print()
    print("Reports saved to:")
    print(expected_actual_path)
    print(product_path)
    print(channel_path)
    print(segment_path)
    print(product_channel_path)
    print(top_cases_path)


if __name__ == "__main__":
    main()
