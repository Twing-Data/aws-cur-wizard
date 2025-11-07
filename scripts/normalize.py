#!/usr/bin/env python
import os
import pathlib
import sys

import duckdb
from dotenv import load_dotenv

load_dotenv()

NORMALIZED_DATA_DIR = pathlib.Path(os.getenv("NORMALIZED_DATA_DIR") or "").resolve()
if not NORMALIZED_DATA_DIR.exists() or not NORMALIZED_DATA_DIR.is_dir():
    sys.exit(f"NORMALIZED_DATA_DIR ({NORMALIZED_DATA_DIR}) does not exist or is not a directory")
output_path = NORMALIZED_DATA_DIR / "normalized.parquet"

def get_env_var_or_exit(env_var_name):
    env_var = os.getenv(env_var_name)
    if not env_var:
        sys.exit(f"${env_var_name} variable not set!")
    else:
        return env_var

AWS_REGION = get_env_var_or_exit("AWS_REGION")
AWS_ACCESS_KEY_ID = get_env_var_or_exit("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = get_env_var_or_exit("AWS_SECRET_ACCESS_KEY")
BUCKET_NAME = get_env_var_or_exit("BUCKET_NAME")
S3_INPUT_DATA_PATH = get_env_var_or_exit("S3_INPUT_DATA_PATH")

con = duckdb.connect(database=":memory:")

# Configure DuckDB to access S3
con.execute(f"""
    INSTALL httpfs;
    LOAD httpfs;

    SET s3_region='{AWS_REGION}';
    SET s3_access_key_id='{AWS_ACCESS_KEY_ID}';
    SET s3_secret_access_key='{AWS_SECRET_ACCESS_KEY}';
""")

# Read Parquet file directly from S3 into a DuckDB relation
con.execute(
    f"""
    CREATE VIEW raw AS
      SELECT *
      FROM read_parquet('s3://{BUCKET_NAME}/{S3_INPUT_DATA_PATH}', UNION_BY_NAME => TRUE)
    """
)

schema_rows = con.execute("DESCRIBE SELECT * FROM raw").fetchall()
all_columns = {row[0] for row in schema_rows}
map_cols = [row[0] for row in schema_rows if row[1].startswith("MAP")]
print("MAP columns found:", map_cols)


select_clauses = ["*"]

for col in map_cols:
    keys = [
        k[0]
        for k in con.execute(
            f"""
            SELECT DISTINCT
              key.unnest AS key_str
            FROM (
              SELECT map_keys({col}) AS k
              FROM raw
              WHERE {col} IS NOT NULL
            ) t
            CROSS JOIN UNNEST(k) AS key
            """
        ).fetchall()
    ]

    for key_str in keys:
        exploded = f"{col} ->> '{key_str}'"
        flat = f"{col}_{key_str}"
        if flat in all_columns:
            clause = f"COALESCE({flat}, {exploded}) AS {flat}"
        else:
            clause = f"{exploded} AS {flat}"
        select_clauses.append(clause)

if len(select_clauses) > 1:
    print("Generated SELECT clauses:\n", "\n".join(select_clauses))
else:
    print("No MAP columns found. No normalization needed.")

select_sql = "SELECT " + ",\n       ".join(select_clauses) + "\n  FROM raw"

copy_sql = "COPY (\n" + select_sql + f"\n) TO '{output_path}' (FORMAT PARQUET);"
con.execute(copy_sql)
print(f"✅ Normalized parquet written to {output_path}")
