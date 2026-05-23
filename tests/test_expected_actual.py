from __future__ import annotations

import pandas as pd

from src.expected_actual import (
    build_expected_actual_table,
    calculate_fee,
)


def test_calculate_fee_rate_min_max() -> None:
    fee = calculate_fee(
        amount=100_000,
        fee_type="rate_min_max",
        rate=0.01,
        fixed_fee=0,
        min_fee=100,
        max_fee=500,
    )

    assert fee == 500


def test_build_expected_actual_table_detects_undercharge() -> None:
    operations = pd.DataFrame(
        {
            "operation_id": ["OP_1"],
            "customer_id": ["CUST_1"],
            "client_segment": ["mass"],
            "region": ["almaty"],
            "branch_id": ["BR_001"],
            "operation_date": ["2025-02-01"],
            "product_type": ["domestic_transfers"],
            "operation_type": ["external_transfer"],
            "channel": ["mobile"],
            "amount": [100_000],
            "operation_status": ["posted"],
        }
    )

    tariff_rules = pd.DataFrame(
        {
            "tariff_rule_id": ["TR_1"],
            "product_type": ["domestic_transfers"],
            "operation_type": ["external_transfer"],
            "channel": ["mobile"],
            "client_segment": ["mass"],
            "effective_from": ["2025-01-01"],
            "effective_to": ["2025-12-31"],
            "tariff_version": ["v2025"],
            "fee_type": ["rate_min_max"],
            "rate": [0.01],
            "fixed_fee": [0],
            "min_fee": [100],
            "max_fee": [5_000],
        }
    )

    actual_charges = pd.DataFrame(
        {
            "operation_id": ["OP_1"],
            "actual_fee": [500],
            "actual_income": [500],
            "applied_tariff_rule_id": ["TR_1"],
            "charge_status": ["charged"],
            "calculation_version": ["engine_v2"],
        }
    )

    result = build_expected_actual_table(
        operations=operations,
        tariff_rules=tariff_rules,
        actual_charges=actual_charges,
    )

    assert result["expected_fee"].iloc[0] == 1000
    assert result["actual_fee"].iloc[0] == 500
    assert result["potential_loss"].iloc[0] == 500
    assert result["control_status"].iloc[0] == "undercharged_potential_loss"
