from __future__ import annotations

import getpass
import os
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, text


def build_postgres_engine(
    db_host: str,
    db_port: str,
    db_name: str,
    db_user: str,
    db_password: str | None = None,
):
    password = db_password or os.getenv("PGPASSWORD")

    if password is None:
        password = getpass.getpass(f"Password for PostgreSQL user {db_user}: ")

    url = (
        f"postgresql+psycopg2://{db_user}:{quote_plus(password)}"
        f"@{db_host}:{db_port}/{db_name}"
    )

    return create_engine(url)


def read_postgres_table(
    table_name: str,
    db_host: str,
    db_port: str,
    db_name: str,
    db_user: str,
    db_password: str | None = None,
) -> pd.DataFrame:
    engine = build_postgres_engine(
        db_host=db_host,
        db_port=db_port,
        db_name=db_name,
        db_user=db_user,
        db_password=db_password,
    )

    print(f"Reading table from PostgreSQL: {table_name}")
    df = pd.read_sql(f"SELECT * FROM {table_name};", engine)
    print(f"Loaded shape: {df.shape}")

    return df


def read_csv_table(csv_path: str | Path) -> pd.DataFrame:
    path = Path(csv_path)

    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    df = pd.read_csv(path)
    print(f"Loaded CSV shape: {df.shape}")

    return df


def execute_sql_file(
    sql_path: str | Path,
    db_host: str,
    db_port: str,
    db_name: str,
    db_user: str,
    db_password: str | None = None,
) -> None:
    path = Path(sql_path)

    if not path.exists():
        raise FileNotFoundError(f"SQL file not found: {path}")

    engine = build_postgres_engine(
        db_host=db_host,
        db_port=db_port,
        db_name=db_name,
        db_user=db_user,
        db_password=db_password,
    )

    sql = path.read_text(encoding="utf-8")

    with engine.begin() as connection:
        connection.execute(text(sql))
