CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS mart;

DROP TABLE IF EXISTS raw.confirmed_incidents CASCADE;
DROP TABLE IF EXISTS raw.manual_adjustments CASCADE;
DROP TABLE IF EXISTS raw.actual_charges CASCADE;
DROP TABLE IF EXISTS raw.operations CASCADE;
DROP TABLE IF EXISTS raw.tariff_rules CASCADE;
DROP TABLE IF EXISTS raw.customers CASCADE;

CREATE TABLE raw.customers (
    customer_id TEXT PRIMARY KEY,
    client_segment TEXT NOT NULL,
    region TEXT NOT NULL,
    branch_id TEXT NOT NULL,
    signup_date DATE NOT NULL,
    risk_profile TEXT NOT NULL
);

CREATE TABLE raw.tariff_rules (
    tariff_rule_id TEXT PRIMARY KEY,
    product_type TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    channel TEXT NOT NULL,
    client_segment TEXT NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE NOT NULL,
    tariff_version TEXT NOT NULL,
    fee_type TEXT NOT NULL,
    rate NUMERIC(18, 8) NOT NULL,
    fixed_fee NUMERIC(18, 2) NOT NULL,
    min_fee NUMERIC(18, 2) NOT NULL,
    max_fee NUMERIC(18, 2) NOT NULL
);

CREATE TABLE raw.operations (
    operation_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    client_segment TEXT NOT NULL,
    region TEXT NOT NULL,
    branch_id TEXT NOT NULL,
    operation_date DATE NOT NULL,
    product_type TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    channel TEXT NOT NULL,
    amount NUMERIC(18, 2) NOT NULL,
    operation_status TEXT NOT NULL,
    expected_tariff_rule_id TEXT
);

CREATE TABLE raw.actual_charges (
    operation_id TEXT PRIMARY KEY,
    actual_fee NUMERIC(18, 2) NOT NULL,
    actual_income NUMERIC(18, 2) NOT NULL,
    applied_tariff_rule_id TEXT,
    charge_status TEXT NOT NULL,
    calculation_version TEXT NOT NULL
);

CREATE TABLE raw.manual_adjustments (
    adjustment_id TEXT PRIMARY KEY,
    operation_id TEXT NOT NULL,
    adjustment_date DATE NOT NULL,
    adjustment_amount NUMERIC(18, 2) NOT NULL,
    adjustment_reason TEXT NOT NULL,
    approved_flag INTEGER NOT NULL
);

CREATE TABLE raw.confirmed_incidents (
    case_id TEXT PRIMARY KEY,
    operation_id TEXT NOT NULL,
    review_date DATE NOT NULL,
    real_issue INTEGER NOT NULL,
    issue_type TEXT NOT NULL,
    confirmed_loss NUMERIC(18, 2) NOT NULL,
    resolution_status TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_operations_date ON raw.operations(operation_date);
CREATE INDEX IF NOT EXISTS idx_operations_product ON raw.operations(product_type, operation_type);
CREATE INDEX IF NOT EXISTS idx_operations_customer ON raw.operations(customer_id);
CREATE INDEX IF NOT EXISTS idx_tariff_rules_lookup
    ON raw.tariff_rules(product_type, operation_type, channel, client_segment, effective_from, effective_to);
CREATE INDEX IF NOT EXISTS idx_actual_charges_operation ON raw.actual_charges(operation_id);
CREATE INDEX IF NOT EXISTS idx_manual_adjustments_operation ON raw.manual_adjustments(operation_id);
CREATE INDEX IF NOT EXISTS idx_confirmed_incidents_operation ON raw.confirmed_incidents(operation_id);
