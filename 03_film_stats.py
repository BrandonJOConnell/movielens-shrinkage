#%% 
import duckdb
con = duckdb.connect("movielens.duckdb") 

#%% Mart: film_stats (one row per film, aggregated from ratings)
con.sql("""
    CREATE OR REPLACE TABLE film_stats AS 
    SELECT  movie_id,
            COUNT(*)            AS n,
            AVG(rating)         AS mean_rating,
            VAR_SAMP(rating)    AS var_rating
    FROM ratings
    GROUP BY movie_id
""")

#%% Compute within-film pooled std deviation
con.sql("""
    SELECT SQRT(SUM((n-1) * var_rating) / SUM(n - 1)) AS std_pooled
    FROM film_stats
    WHERE n > 1
""").show()
# %%
con.close()