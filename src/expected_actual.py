from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_fee(
    amount: float,
    fee_type: str,
    rate: float,
    fixed_fee: float,
    min_fee: float,
    max_fee: float,
) -> float:
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


def attach_tariff_rules(
    operations: pd.DataFrame,
    tariff_rules: pd.DataFrame,
) -> pd.DataFrame:
    ops = operations.copy()
    rules = tariff_rules.copy()

    ops["operation_date"] = pd.to_datetime(ops["operation_date"], errors="coerce")
    rules["effective_from"] = pd.to_datetime(rules["effective_from"], errors="coerce")
    rules["effective_to"] = pd.to_datetime(rules["effective_to"], errors="coerce")

    merged = ops.merge(
        rules,
        on=["product_type", "operation_type", "channel", "client_segment"],
        how="left",
        suffixes=("", "_rule"),
    )

    matched = merged[
        (merged["operation_date"] >= merged["effective_from"])
        & (merged["operation_date"] <= merged["effective_to"])
    ].copy()

    matched = matched.sort_values(
        ["operation_id", "effective_from", "tariff_rule_id"]
    ).drop_duplicates("operation_id", keep="last")

    missing_ops = ops.loc[~ops["operation_id"].isin(matched["operation_id"])].copy()

    if not missing_ops.empty:
        for col in rules.columns:
            if col not in missing_ops.columns:
                missing_ops[col] = np.nan
        matched = pd.concat([matched, missing_ops], ignore_index=True)

    return matched


def build_expected_actual_table(
    operations: pd.DataFrame,
    tariff_rules: pd.DataFrame,
    actual_charges: pd.DataFrame,
    money_tolerance: float = 0.01,
) -> pd.DataFrame:
    data = attach_tariff_rules(operations, tariff_rules)

    data["expected_fee"] = data.apply(
        lambda row: calculate_fee(
            amount=float(row["amount"]) if pd.notna(row["amount"]) else 0.0,
            fee_type=str(row["fee_type"]) if pd.notna(row["fee_type"]) else "missing",
            rate=float(row["rate"]) if pd.notna(row["rate"]) else 0.0,
            fixed_fee=float(row["fixed_fee"]) if pd.notna(row["fixed_fee"]) else 0.0,
            min_fee=float(row["min_fee"]) if pd.notna(row["min_fee"]) else 0.0,
            max_fee=float(row["max_fee"]) if pd.notna(row["max_fee"]) else 0.0,
        ),
        axis=1,
    )

    data.loc[data["operation_status"].ne("posted"), "expected_fee"] = 0.0

    charges = actual_charges.copy()

    result = data.merge(
        charges,
        on="operation_id",
        how="left",
        suffixes=("", "_actual"),
    )

    result["actual_fee"] = pd.to_numeric(result["actual_fee"], errors="coerce").fillna(0.0)
    result["fee_diff"] = result["actual_fee"] - result["expected_fee"]
    result["abs_fee_diff"] = result["fee_diff"].abs()
    result["potential_loss"] = np.maximum(result["expected_fee"] - result["actual_fee"], 0.0)
    result["overcharge_amount"] = np.maximum(result["actual_fee"] - result["expected_fee"], 0.0)

    result["relative_diff"] = np.where(
        result["expected_fee"].abs() > money_tolerance,
        result["fee_diff"] / result["expected_fee"],
        0.0,
    )

    result["control_status"] = np.select(
        [
            result["tariff_rule_id"].isna(),
            result["operation_status"].ne("posted"),
            result["abs_fee_diff"] <= money_tolerance,
            result["potential_loss"] > money_tolerance,
            result["overcharge_amount"] > money_tolerance,
        ],
        [
            "missing_tariff_rule",
            "excluded_non_posted",
            "matched",
            "undercharged_potential_loss",
            "overcharged_customer_impact",
        ],
        default="review",
    )

    result["is_deviation"] = result["control_status"].isin(
        [
            "missing_tariff_rule",
            "undercharged_potential_loss",
            "overcharged_customer_impact",
            "review",
        ]
    ).astype(int)

    result["priority_amount"] = result["potential_loss"].where(
        result["potential_loss"] > 0,
        result["overcharge_amount"],
    )

    selected_columns = [
        "operation_id",
        "customer_id",
        "client_segment",
        "region",
        "branch_id",
        "operation_date",
        "product_type",
        "operation_type",
        "channel",
        "amount",
        "operation_status",
        "tariff_rule_id",
        "expected_fee",
        "actual_fee",
        "fee_diff",
        "abs_fee_diff",
        "relative_diff",
        "potential_loss",
        "overcharge_amount",
        "control_status",
        "is_deviation",
        "priority_amount",
    ]

    return result[selected_columns].sort_values("priority_amount", ascending=False).reset_index(drop=True)


def build_deviation_summary(expected_actual: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    data = expected_actual.copy()

    summary = (
        data.groupby(group_cols, dropna=False)
        .agg(
            operations=("operation_id", "count"),
            deviations=("is_deviation", "sum"),
            total_amount=("amount", "sum"),
            total_expected_fee=("expected_fee", "sum"),
            total_actual_fee=("actual_fee", "sum"),
            total_fee_diff=("fee_diff", "sum"),
            total_potential_loss=("potential_loss", "sum"),
            total_overcharge_amount=("overcharge_amount", "sum"),
            avg_abs_fee_diff=("abs_fee_diff", "mean"),
        )
        .reset_index()
    )

    summary["deviation_rate"] = summary["deviations"] / summary["operations"]
    summary = summary.sort_values(
        ["total_potential_loss", "deviations"],
        ascending=[False, False],
    ).reset_index(drop=True)

    return summary


def build_top_cases(
    expected_actual: pd.DataFrame,
    n: int = 100,
) -> pd.DataFrame:
    data = expected_actual.copy()

    data = data[data["is_deviation"].eq(1)].copy()

    return (
        data.sort_values(["priority_amount", "abs_fee_diff"], ascending=[False, False])
        .head(n)
        .reset_index(drop=True)
    )
