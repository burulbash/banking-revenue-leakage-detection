TRUNCATE TABLE
    raw.confirmed_incidents,
    raw.manual_adjustments,
    raw.actual_charges,
    raw.operations,
    raw.tariff_rules,
    raw.customers
RESTART IDENTITY;

\copy raw.customers FROM 'data/raw/tiny/customers.csv' WITH (FORMAT csv, HEADER true);
\copy raw.tariff_rules FROM 'data/raw/tiny/tariff_rules.csv' WITH (FORMAT csv, HEADER true);
\copy raw.operations FROM 'data/raw/tiny/operations.csv' WITH (FORMAT csv, HEADER true);
\copy raw.actual_charges FROM 'data/raw/tiny/actual_charges.csv' WITH (FORMAT csv, HEADER true);
\copy raw.manual_adjustments FROM 'data/raw/tiny/manual_adjustments.csv' WITH (FORMAT csv, HEADER true);
\copy raw.confirmed_incidents FROM 'data/raw/tiny/confirmed_incidents.csv' WITH (FORMAT csv, HEADER true);

ANALYZE raw.customers;
ANALYZE raw.tariff_rules;
ANALYZE raw.operations;
ANALYZE raw.actual_charges;
ANALYZE raw.manual_adjustments;
ANALYZE raw.confirmed_incidents;
