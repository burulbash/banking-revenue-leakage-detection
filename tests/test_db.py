from __future__ import annotations

import pandas as pd

from src.db import read_csv_table


def test_read_csv_table(tmp_path) -> None:
    path = tmp_path / "sample.csv"
    pd.DataFrame({"a": [1, 2], "b": ["x", "y"]}).to_csv(path, index=False)

    df = read_csv_table(path)

    assert df.shape == (2, 2)
    assert list(df.columns) == ["a", "b"]
