#%% Quick explore
import duckdb
con = duckdb.connect("movielens.duckdb", read_only=True) # avoid edits

#%% Explore: order films by number of ratings and show titles
con.sql("""
    with per_film AS ( 
        SELECT movie_id, COUNT(*) AS n
        FROM ratings
        GROUP BY movie_id
        )
    SELECT movie_id, title, n 
    FROM per_film
    LEFT JOIN movies USING (movie_id)
    ORDER BY n ASC, movie_id
""").show()

#%% Explore: ratings per film
con.sql("""
    WITH per_film AS (
        SELECT movie_id, COUNT(*) as n
        FROM ratings
        GROUP BY movie_id
        )
    SELECT  MEDIAN(n)                       AS median_n,
            AVG(n)                          AS mean_n,
            MAX(n)                          AS max_n,
            COUNT(*) FILTER (WHERE n < 10)  AS films_under_10,
            COUNT(*)                        AS n_films 
    FROM per_film
""").show()

#%% Explore: order films by average rating, number of ratings, and title, and show std_dev
con.sql("""
    with per_film AS ( 
        SELECT movie_id, COUNT(*) AS n, AVG(rating) AS mean_rating, STDDEV_SAMP(rating) AS std_rating
        FROM ratings
        GROUP BY movie_id
        )
    SELECT movie_id, title, n, mean_rating, std_rating
    FROM per_film
    LEFT JOIN movies USING (movie_id)
    ORDER BY mean_rating DESC, n DESC, movie_id
    LIMIT 10
""").show()

#%% 
con.close() # ensures other scripts can connect to DuckDB 