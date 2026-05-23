from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


PRODUCT_OPERATION_MAP = {
    "card_payments": ["merchant_purchase", "p2p_transfer"],
    "domestic_transfers": ["internal_transfer", "external_transfer"],
    "cash_withdrawals": ["atm_cash_withdrawal"],
    "account_service": ["monthly_package_fee"],
    "merchant_acquiring": ["merchant_settlement"],
}

PRODUCT_CHANNEL_MAP = {
    "card_payments": ["pos", "mobile", "web"],
    "domestic_transfers": ["mobile", "web", "branch"],
    "cash_withdrawals": ["atm", "branch"],
    "account_service": ["mobile", "web", "branch"],
    "merchant_acquiring": ["pos", "web"],
}

CLIENT_SEGMENTS = ["mass", "affluent", "sme", "corporate"]
REGIONS = ["almaty", "astana", "shymkent", "karaganda", "aktobe", "other"]
STATUSES = ["posted", "reversed", "pending", "failed"]

SIZE_CONFIG = {
    "tiny": {"customers": 1_000, "operations": 10_000},
    "small": {"customers": 5_000, "operations": 50_000},
    "medium": {"customers": 20_000, "operations": 250_000},
}


def round_money(values) -> np.ndarray:
    return np.round(values, 2)


def make_ids(prefix: str, n: int) -> list[str]:
    return [f"{prefix}_{i:07d}" for i in range(1, n + 1)]


def generate_customers(n_customers: int, rng: np.random.Generator) -> pd.DataFrame:
    customer_ids = make_ids("CUST", n_customers)

    segment = rng.choice(
        CLIENT_SEGMENTS,
        size=n_customers,
        p=[0.55, 0.20, 0.18, 0.07],
    )

    region = rng.choice(
        REGIONS,
        size=n_customers,
        p=[0.28, 0.22, 0.12, 0.10, 0.08, 0.20],
    )

    branch_id = [f"BR_{x:03d}" for x in rng.integers(1, 61, size=n_customers)]

    signup_date = pd.to_datetime("2018-01-01") + pd.to_timedelta(
        rng.integers(0, 365 * 7, size=n_customers),
        unit="D",
    )

    risk_profile = rng.choice(
        ["low", "medium", "high"],
        size=n_customers,
        p=[0.45, 0.43, 0.12],
    )

    return pd.DataFrame(
        {
            "customer_id": customer_ids,
            "client_segment": segment,
            "region": region,
            "branch_id": branch_id,
            "signup_date": signup_date,
            "risk_profile": risk_profile,
        }
    )


def build_tariff_rules() -> pd.DataFrame:
    rows = []
    rule_id = 1

    segment_multiplier = {
        "mass": 1.00,
        "affluent": 0.75,
        "sme": 0.90,
        "corporate": 0.65,
    }

    channel_multiplier = {
        "mobile": 0.85,
        "web": 0.90,
        "branch": 1.20,
        "atm": 1.00,
        "pos": 0.80,
    }

    base_config = {
        "merchant_purchase": {"fee_type": "rate_min_max", "rate": 0.0025, "fixed_fee": 0.0, "min_fee": 0.0, "max_fee": 800.0},
        "p2p_transfer": {"fee_type": "rate_min_max", "rate": 0.0040, "fixed_fee": 0.0, "min_fee": 50.0, "max_fee": 2_000.0},
        "internal_transfer": {"fee_type": "fixed", "rate": 0.0, "fixed_fee": 0.0, "min_fee": 0.0, "max_fee": 0.0},
        "external_transfer": {"fee_type": "rate_min_max", "rate": 0.0030, "fixed_fee": 100.0, "min_fee": 150.0, "max_fee": 5_000.0},
        "atm_cash_withdrawal": {"fee_type": "rate_min_max", "rate": 0.0060, "fixed_fee": 0.0, "min_fee": 100.0, "max_fee": 3_000.0},
        "monthly_package_fee": {"fee_type": "fixed", "rate": 0.0, "fixed_fee": 1_500.0, "min_fee": 0.0, "max_fee": 0.0},
        "merchant_settlement": {"fee_type": "rate_min_max", "rate": 0.0110, "fixed_fee": 0.0, "min_fee": 300.0, "max_fee": 50_000.0},
    }

    periods = [
        ("2024-01-01", "2024-12-31", 1.00, "v2024"),
        ("2025-01-01", "2025-12-31", 1.12, "v2025"),
    ]

    for product_type, operations in PRODUCT_OPERATION_MAP.items():
        for operation_type in operations:
            for channel in PRODUCT_CHANNEL_MAP[product_type]:
                for segment in CLIENT_SEGMENTS:
                    for effective_from, effective_to, period_multiplier, version in periods:
                        config = base_config[operation_type]
                        rows.append(
                            {
                                "tariff_rule_id": f"TR_{rule_id:05d}",
                                "product_type": product_type,
                                "operation_type": operation_type,
                                "channel": channel,
                                "client_segment": segment,
                                "effective_from": effective_from,
                                "effective_to": effective_to,
                                "tariff_version": version,
                                "fee_type": config["fee_type"],
                                "rate": config["rate"] * segment_multiplier[segment] * channel_multiplier[channel] * period_multiplier,
                                "fixed_fee": config["fixed_fee"] * segment_multiplier[segment] * channel_multiplier[channel] * period_multiplier,
                                "min_fee": config["min_fee"] * segment_multiplier[segment],
                                "max_fee": config["max_fee"] * segment_multiplier[segment],
                            }
                        )
                        rule_id += 1

    rules = pd.DataFrame(rows)
    rules["effective_from"] = pd.to_datetime(rules["effective_from"])
    rules["effective_to"] = pd.to_datetime(rules["effective_to"])

    return rules


def calculate_fee(amount: float, fee_type: str, rate: float, fixed_fee: float, min_fee: float, max_fee: float) -> float:
    if fee_type == "free":
        return 0.0

    if fee_type == "fixed":
        return float(round(fixed_fee, 2))

    raw_fee = amount * rate + fixed_fee

    if min_fee > 0:
        raw_fee = max(raw_fee, min_fee)

    if max_fee > 0:
        raw_fee = min(raw_fee, max_fee)

    return float(round(raw_fee, 2))


def build_rule_lookup(tariff_rules: pd.DataFrame) -> dict[tuple[str, str, str, str, str], dict[str, object]]:
    lookup = {}

    for row in tariff_rules.to_dict("records"):
        key = (
            row["product_type"],
            row["operation_type"],
            row["channel"],
            row["client_segment"],
            row["tariff_version"],
        )
        lookup[key] = row

    return lookup


def choose_product_and_operation(rng: np.random.Generator) -> tuple[str, str]:
    product_type = rng.choice(
        list(PRODUCT_OPERATION_MAP.keys()),
        p=[0.34, 0.27, 0.12, 0.12, 0.15],
    )
    operation_type = rng.choice(PRODUCT_OPERATION_MAP[product_type])
    return product_type, operation_type


def generate_operations(
    customers: pd.DataFrame,
    tariff_rules: pd.DataFrame,
    n_operations: int,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    customer_sample = customers.sample(
        n=n_operations,
        replace=True,
        random_state=int(rng.integers(0, 1_000_000)),
    ).reset_index(drop=True)

    operation_ids = make_ids("OP", n_operations)

    operation_dates = pd.to_datetime("2024-01-01") + pd.to_timedelta(
        rng.integers(0, 365 * 2, size=n_operations),
        unit="D",
    )

    product_types = []
    operation_types = []
    channels = []

    for _ in range(n_operations):
        product_type, operation_type = choose_product_and_operation(rng)
        product_types.append(product_type)
        operation_types.append(operation_type)
        channels.append(rng.choice(PRODUCT_CHANNEL_MAP[product_type]))

    amount = rng.lognormal(mean=10.4, sigma=1.15, size=n_operations)
    amount = np.clip(amount, 1_000, 50_000_000)
    amount = round_money(amount)

    status = rng.choice(STATUSES, size=n_operations, p=[0.93, 0.025, 0.03, 0.015])

    operations = pd.DataFrame(
        {
            "operation_id": operation_ids,
            "customer_id": customer_sample["customer_id"],
            "client_segment": customer_sample["client_segment"],
            "region": customer_sample["region"],
            "branch_id": customer_sample["branch_id"],
            "operation_date": operation_dates,
            "product_type": product_types,
            "operation_type": operation_types,
            "channel": channels,
            "amount": amount,
            "operation_status": status,
        }
    )

    operations["tariff_version"] = np.where(
        operations["operation_date"] < pd.to_datetime("2025-01-01"),
        "v2024",
        "v2025",
    )

    rule_lookup = build_rule_lookup(tariff_rules)

    expected_fees = []
    expected_rule_ids = []

    for row in operations.to_dict("records"):
        key = (
            row["product_type"],
            row["operation_type"],
            row["channel"],
            row["client_segment"],
            row["tariff_version"],
        )
        rule = rule_lookup[key]
        fee = calculate_fee(
            amount=float(row["amount"]),
            fee_type=str(rule["fee_type"]),
            rate=float(rule["rate"]),
            fixed_fee=float(rule["fixed_fee"]),
            min_fee=float(rule["min_fee"]),
            max_fee=float(rule["max_fee"]),
        )

        if row["operation_status"] != "posted":
            fee = 0.0

        expected_fees.append(fee)
        expected_rule_ids.append(rule["tariff_rule_id"])

    operations["expected_tariff_rule_id"] = expected_rule_ids

    issue_probability = np.full(n_operations, 0.018)

    issue_probability += np.where(operations["operation_date"] >= pd.to_datetime("2025-01-01"), 0.008, 0.0)
    issue_probability += np.where(operations["channel"].eq("branch"), 0.010, 0.0)
    issue_probability += np.where(operations["product_type"].eq("merchant_acquiring"), 0.012, 0.0)
    issue_probability += np.where(operations["client_segment"].eq("corporate"), 0.008, 0.0)

    real_issue = (rng.random(n_operations) < issue_probability) & operations["operation_status"].eq("posted").to_numpy()

    issue_types = np.full(n_operations, "none", dtype=object)
    issue_types[real_issue] = rng.choice(
        [
            "undercharged_fee",
            "outdated_tariff_after_change",
            "wrong_segment_tariff",
            "manual_fee_waiver_without_reason",
            "channel_mapping_error",
        ],
        size=int(real_issue.sum()),
        p=[0.35, 0.25, 0.15, 0.15, 0.10],
    )

    benign_exception = (
        (rng.random(n_operations) < 0.018)
        & operations["operation_status"].eq("posted").to_numpy()
        & ~real_issue
    )

    actual_fees = np.array(expected_fees, dtype=float)
    applied_rule_ids = np.array(expected_rule_ids, dtype=object)

    for idx in np.where(real_issue)[0]:
        issue_type = issue_types[idx]

        if issue_type == "undercharged_fee":
            actual_fees[idx] = actual_fees[idx] * rng.uniform(0.15, 0.70)
        elif issue_type == "outdated_tariff_after_change":
            actual_fees[idx] = actual_fees[idx] / rng.uniform(1.10, 1.25)
        elif issue_type == "wrong_segment_tariff":
            actual_fees[idx] = actual_fees[idx] * rng.uniform(0.45, 0.80)
        elif issue_type == "manual_fee_waiver_without_reason":
            actual_fees[idx] = 0.0
        elif issue_type == "channel_mapping_error":
            actual_fees[idx] = actual_fees[idx] * rng.uniform(0.50, 0.85)

    actual_fees[benign_exception] = actual_fees[benign_exception] * rng.uniform(0.0, 0.25, size=int(benign_exception.sum()))

    actual_fees = round_money(np.maximum(actual_fees, 0.0))

    actual_charges = pd.DataFrame(
        {
            "operation_id": operations["operation_id"],
            "actual_fee": actual_fees,
            "actual_income": actual_fees,
            "applied_tariff_rule_id": applied_rule_ids,
            "charge_status": np.where(operations["operation_status"].eq("posted"), "charged", "not_charged"),
            "calculation_version": np.where(operations["operation_date"] < pd.to_datetime("2025-01-01"), "engine_v1", "engine_v2"),
        }
    )

    adjustment_mask = (
        real_issue
        | benign_exception
        | ((rng.random(n_operations) < 0.01) & operations["operation_status"].eq("posted").to_numpy())
    )

    adjustment_rows = []
    for idx in np.where(adjustment_mask)[0]:
        expected_fee = expected_fees[idx]
        actual_fee = actual_fees[idx]
        adjustment_amount = round(float(actual_fee - expected_fee), 2)

        if issue_types[idx] == "manual_fee_waiver_without_reason":
            reason = "manual_waiver"
            approved = False
        elif benign_exception[idx]:
            reason = "approved_promo"
            approved = True
        else:
            reason = rng.choice(["pricing_correction", "manual_adjustment", "exception_case"])
            approved = bool(rng.random() > 0.25)

        adjustment_rows.append(
            {
                "adjustment_id": f"ADJ_{len(adjustment_rows) + 1:07d}",
                "operation_id": operations["operation_id"].iloc[idx],
                "adjustment_date": operations["operation_date"].iloc[idx] + pd.to_timedelta(int(rng.integers(0, 5)), unit="D"),
                "adjustment_amount": adjustment_amount,
                "adjustment_reason": reason,
                "approved_flag": int(approved),
            }
        )

    manual_adjustments = pd.DataFrame(adjustment_rows)

    confirmed_rows = []

    candidate_mask = real_issue | benign_exception | (rng.random(n_operations) < 0.015)

    for idx in np.where(candidate_mask)[0]:
        expected_fee = expected_fees[idx]
        actual_fee = actual_fees[idx]
        potential_loss = max(expected_fee - actual_fee, 0.0)

        confirmed_rows.append(
            {
                "case_id": f"CASE_{len(confirmed_rows) + 1:07d}",
                "operation_id": operations["operation_id"].iloc[idx],
                "review_date": operations["operation_date"].iloc[idx] + pd.to_timedelta(int(rng.integers(1, 20)), unit="D"),
                "real_issue": int(real_issue[idx]),
                "issue_type": issue_types[idx] if real_issue[idx] else ("approved_exception" if benign_exception[idx] else "no_issue"),
                "confirmed_loss": round(float(potential_loss if real_issue[idx] else 0.0), 2),
                "resolution_status": "confirmed" if real_issue[idx] else "closed_no_issue",
            }
        )

    confirmed_incidents = pd.DataFrame(confirmed_rows)

    operations = operations.drop(columns=["tariff_version"])

    return operations, actual_charges, manual_adjustments, confirmed_incidents


def save_table(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def generate_all(size: str, seed: int, output_dir: Path) -> None:
    if size not in SIZE_CONFIG:
        raise ValueError(f"Unknown size: {size}. Available: {sorted(SIZE_CONFIG)}")

    rng = np.random.default_rng(seed)

    n_customers = SIZE_CONFIG[size]["customers"]
    n_operations = SIZE_CONFIG[size]["operations"]

    print(f"Generating banking revenue leakage synthetic data: size={size}, customers={n_customers}, operations={n_operations}, seed={seed}")
    print(f"Output directory: {output_dir.resolve()}")

    output_dir.mkdir(parents=True, exist_ok=True)

    customers = generate_customers(n_customers, rng)
    tariff_rules = build_tariff_rules()
    operations, actual_charges, manual_adjustments, confirmed_incidents = generate_operations(
        customers=customers,
        tariff_rules=tariff_rules,
        n_operations=n_operations,
        rng=rng,
    )

    summary = pd.DataFrame(
        [
            {"metric": "customers", "value": len(customers)},
            {"metric": "tariff_rules", "value": len(tariff_rules)},
            {"metric": "operations", "value": len(operations)},
            {"metric": "actual_charges", "value": len(actual_charges)},
            {"metric": "manual_adjustments", "value": len(manual_adjustments)},
            {"metric": "confirmed_incidents", "value": len(confirmed_incidents)},
            {"metric": "confirmed_issue_rate", "value": confirmed_incidents["real_issue"].mean() if len(confirmed_incidents) else 0.0},
            {"metric": "confirmed_loss_total", "value": confirmed_incidents["confirmed_loss"].sum() if len(confirmed_incidents) else 0.0},
        ]
    )

    tables = {
        "customers.csv": customers,
        "tariff_rules.csv": tariff_rules,
        "operations.csv": operations,
        "actual_charges.csv": actual_charges,
        "manual_adjustments.csv": manual_adjustments,
        "confirmed_incidents.csv": confirmed_incidents,
        "generation_summary.csv": summary,
    }

    for filename, table in tables.items():
        save_table(table, output_dir / filename)
        print(f"{filename}: {len(table):,} rows")

    print()
    print(summary.to_string(index=False))
    print()
    print("Generation completed.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic banking revenue leakage dataset.")
    parser.add_argument("--size", choices=sorted(SIZE_CONFIG), default="tiny")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", default="data/raw/tiny")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate_all(
        size=args.size,
        seed=args.seed,
        output_dir=Path(args.output_dir),
    )


if __name__ == "__main__":
    main()
