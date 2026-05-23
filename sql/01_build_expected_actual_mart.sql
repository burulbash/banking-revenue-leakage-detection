CREATE SCHEMA IF NOT EXISTS mart;

DROP TABLE IF EXISTS mart.expected_actual_operation_level;

CREATE TABLE mart.expected_actual_operation_level AS
WITH matched_rules AS (
    SELECT
        o.operation_id,
        o.customer_id,
        o.client_segment,
        o.region,
        o.branch_id,
        o.operation_date,
        o.product_type,
        o.operation_type,
        o.channel,
        o.amount,
        o.operation_status,
        tr.tariff_rule_id,
        tr.fee_type,
        tr.rate,
        tr.fixed_fee,
        tr.min_fee,
        tr.max_fee
    FROM raw.operations o
    LEFT JOIN LATERAL (
        SELECT tr_inner.*
        FROM raw.tariff_rules tr_inner
        WHERE tr_inner.product_type = o.product_type
          AND tr_inner.operation_type = o.operation_type
          AND tr_inner.channel = o.channel
          AND tr_inner.client_segment = o.client_segment
          AND o.operation_date BETWEEN tr_inner.effective_from AND tr_inner.effective_to
        ORDER BY tr_inner.effective_from DESC, tr_inner.tariff_rule_id
        LIMIT 1
    ) tr ON TRUE
),
expected_fee_calc AS (
    SELECT
        *,
        CASE
            WHEN operation_status <> 'posted' THEN 0::numeric
            WHEN tariff_rule_id IS NULL THEN 0::numeric
            WHEN fee_type = 'fixed' THEN ROUND(fixed_fee, 2)
            WHEN fee_type = 'free' THEN 0::numeric
            WHEN fee_type = 'rate_min_max' THEN
                ROUND(
                    CASE
                        WHEN max_fee > 0 THEN LEAST(GREATEST(amount * rate + fixed_fee, min_fee), max_fee)
                        ELSE GREATEST(amount * rate + fixed_fee, min_fee)
                    END,
                    2
                )
            ELSE 0::numeric
        END AS expected_fee
    FROM matched_rules
),
joined_charges AS (
    SELECT
        e.operation_id,
        e.customer_id,
        e.client_segment,
        e.region,
        e.branch_id,
        e.operation_date,
        e.product_type,
        e.operation_type,
        e.channel,
        e.amount,
        e.operation_status,
        e.tariff_rule_id,
        e.expected_fee,
        COALESCE(ac.actual_fee, 0)::numeric AS actual_fee
    FROM expected_fee_calc e
    LEFT JOIN raw.actual_charges ac
        ON e.operation_id = ac.operation_id
),
final AS (
    SELECT
        *,
        actual_fee - expected_fee AS fee_diff,
        ABS(actual_fee - expected_fee) AS abs_fee_diff,
        GREATEST(expected_fee - actual_fee, 0) AS potential_loss,
        GREATEST(actual_fee - expected_fee, 0) AS overcharge_amount,
        CASE
            WHEN ABS(expected_fee) > 0.01 THEN (actual_fee - expected_fee) / expected_fee
            ELSE 0
        END AS relative_diff
    FROM joined_charges
)
SELECT
    operation_id,
    customer_id,
    client_segment,
    region,
    branch_id,
    operation_date,
    product_type,
    operation_type,
    channel,
    amount,
    operation_status,
    tariff_rule_id,
    expected_fee,
    actual_fee,
    fee_diff,
    abs_fee_diff,
    relative_diff,
    potential_loss,
    overcharge_amount,
    CASE
        WHEN tariff_rule_id IS NULL THEN 'missing_tariff_rule'
        WHEN operation_status <> 'posted' THEN 'excluded_non_posted'
        WHEN abs_fee_diff <= 0.01 THEN 'matched'
        WHEN potential_loss > 0.01 THEN 'undercharged_potential_loss'
        WHEN overcharge_amount > 0.01 THEN 'overcharged_customer_impact'
        ELSE 'review'
    END AS control_status,
    CASE
        WHEN tariff_rule_id IS NULL THEN 1
        WHEN abs_fee_diff > 0.01 AND operation_status = 'posted' THEN 1
        ELSE 0
    END AS is_deviation,
    CASE
        WHEN potential_loss > 0 THEN potential_loss
        ELSE overcharge_amount
    END AS priority_amount
FROM final;

CREATE INDEX IF NOT EXISTS idx_mart_expected_actual_operation_id
    ON mart.expected_actual_operation_level(operation_id);

CREATE INDEX IF NOT EXISTS idx_mart_expected_actual_product
    ON mart.expected_actual_operation_level(product_type, channel);

CREATE INDEX IF NOT EXISTS idx_mart_expected_actual_priority
    ON mart.expected_actual_operation_level(priority_amount DESC);

DROP TABLE IF EXISTS mart.fee_deviation_by_product;
CREATE TABLE mart.fee_deviation_by_product AS
SELECT
    product_type,
    COUNT(*) AS operations,
    SUM(is_deviation) AS deviations,
    SUM(amount) AS total_amount,
    SUM(expected_fee) AS total_expected_fee,
    SUM(actual_fee) AS total_actual_fee,
    SUM(fee_diff) AS total_fee_diff,
    SUM(potential_loss) AS total_potential_loss,
    SUM(overcharge_amount) AS total_overcharge_amount,
    AVG(abs_fee_diff) AS avg_abs_fee_diff,
    SUM(is_deviation)::numeric / COUNT(*) AS deviation_rate
FROM mart.expected_actual_operation_level
GROUP BY product_type
ORDER BY total_potential_loss DESC, deviations DESC;

DROP TABLE IF EXISTS mart.fee_deviation_by_channel;
CREATE TABLE mart.fee_deviation_by_channel AS
SELECT
    channel,
    COUNT(*) AS operations,
    SUM(is_deviation) AS deviations,
    SUM(amount) AS total_amount,
    SUM(expected_fee) AS total_expected_fee,
    SUM(actual_fee) AS total_actual_fee,
    SUM(fee_diff) AS total_fee_diff,
    SUM(potential_loss) AS total_potential_loss,
    SUM(overcharge_amount) AS total_overcharge_amount,
    AVG(abs_fee_diff) AS avg_abs_fee_diff,
    SUM(is_deviation)::numeric / COUNT(*) AS deviation_rate
FROM mart.expected_actual_operation_level
GROUP BY channel
ORDER BY total_potential_loss DESC, deviations DESC;

DROP TABLE IF EXISTS mart.fee_deviation_by_segment;
CREATE TABLE mart.fee_deviation_by_segment AS
SELECT
    client_segment,
    COUNT(*) AS operations,
    SUM(is_deviation) AS deviations,
    SUM(amount) AS total_amount,
    SUM(expected_fee) AS total_expected_fee,
    SUM(actual_fee) AS total_actual_fee,
    SUM(fee_diff) AS total_fee_diff,
    SUM(potential_loss) AS total_potential_loss,
    SUM(overcharge_amount) AS total_overcharge_amount,
    AVG(abs_fee_diff) AS avg_abs_fee_diff,
    SUM(is_deviation)::numeric / COUNT(*) AS deviation_rate
FROM mart.expected_actual_operation_level
GROUP BY client_segment
ORDER BY total_potential_loss DESC, deviations DESC;

DROP TABLE IF EXISTS mart.fee_deviation_by_product_channel;
CREATE TABLE mart.fee_deviation_by_product_channel AS
SELECT
    product_type,
    channel,
    COUNT(*) AS operations,
    SUM(is_deviation) AS deviations,
    SUM(amount) AS total_amount,
    SUM(expected_fee) AS total_expected_fee,
    SUM(actual_fee) AS total_actual_fee,
    SUM(fee_diff) AS total_fee_diff,
    SUM(potential_loss) AS total_potential_loss,
    SUM(overcharge_amount) AS total_overcharge_amount,
    AVG(abs_fee_diff) AS avg_abs_fee_diff,
    SUM(is_deviation)::numeric / COUNT(*) AS deviation_rate
FROM mart.expected_actual_operation_level
GROUP BY product_type, channel
ORDER BY total_potential_loss DESC, deviations DESC;

DROP TABLE IF EXISTS mart.top_potential_loss_cases;
CREATE TABLE mart.top_potential_loss_cases AS
SELECT *
FROM mart.expected_actual_operation_level
WHERE is_deviation = 1
ORDER BY priority_amount DESC, abs_fee_diff DESC
LIMIT 100;
