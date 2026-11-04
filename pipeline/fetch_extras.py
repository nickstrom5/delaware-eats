"""Overture address points for Delaware -> data/de/addresses_de.parquet

Places official records that have no usable coordinates (Revenue's licenses carry zip-code centroids; 520 DPH rows have no point) and
researched addresses the map listings lack. Adapted from oh-eats/pipeline/fetch_extras.py.
"""
import os, time
import duckdb

RELEASE = "2026-10-21.0"
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "de")
t = time.time()
con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial; SET s3_region='us-west-2';")
addr = f"s3://overturemaps-us-west-2/release/{RELEASE}/theme=addresses/type=address/*.parquet"
con.execute(f"""COPY (SELECT number, street, unit, postcode, postal_city, address_levels[1].value AS state, address_levels[-1].value AS muni,
  ST_Y(geometry) lat, ST_X(geometry) lon FROM read_parquet('{addr}', hive_partitioning=1)
  WHERE country = 'US' AND bbox.xmin BETWEEN -75.85 AND -74.98 AND bbox.ymin BETWEEN 38.40 AND 39.88)
  TO '{OUT}/addresses_de.parquet' (FORMAT PARQUET)""")
print(con.execute(f"select count(*), count(*) filter (where state='DE') from '{OUT}/addresses_de.parquet'").fetchall(), round(time.time() - t), "s")
