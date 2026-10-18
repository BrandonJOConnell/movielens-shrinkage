#%% Ingest Data: load raw MovieLens CSVs into DuckDB
import duckdb
from pathlib import Path

for name in ["ratings.csv", "movies.csv"]:
    path = Path("data/ml-32m") / name
    if not path.exists():
        raise SystemExit(f"{path} not found. See 'Reproduce' in the README for the download step.")

# Spin up DuckDB file on disk
con = duckdb.connect("movielens.duckdb") 

#%% Quick explore of ratings.csv
con.sql("DESCRIBE SELECT * FROM 'data/ml-32m/ratings.csv'").show()   # inferred types
con.sql("SUMMARIZE SELECT * FROM 'data/ml-32m/ratings.csv'").show()  # min, max, nulls, distinct counts

#%% Stage: Check types and rename as appropriate
con.sql("""
    CREATE OR REPLACE TABLE ratings     AS 
    SELECT userId::INTEGER              AS user_id,
           movieId::INTEGER             AS movie_id,
           rating::DECIMAL(2,1)         AS rating,
           epoch_ms("timestamp" * 1000) AS rated_at
    FROM read_csv_auto('data/ml-32m/ratings.csv', header=True)
""")
#%% Quick explore of movies.csv
con.sql("DESCRIBE SELECT * FROM 'data/ml-32m/movies.csv'").show()   # inferred types
con.sql("SUMMARIZE SELECT * FROM 'data/ml-32m/movies.csv'").show() 

#%% Stage: Check types and rename as appropriate
con.sql("""
    CREATE OR REPLACE TABLE movies AS
    SELECT movieId::INTEGER AS movie_id,
           title,
           genres
    FROM read_csv_auto('data/ml-32m/movies.csv')
""")

#%% Quick query check 
con.sql("SELECT * FROM ratings LIMIT 10").show()
con.sql("SELECT * FROM movies LIMIT 10").show()

#%% 
con.close() # ensures other scripts can connect to DuckDB 
# %%
