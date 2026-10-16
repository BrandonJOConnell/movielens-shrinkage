#%% Checks
import duckdb
con = duckdb.connect("movielens.duckdb", read_only=True) # avoid edits

#%% Check: volumes 
con.sql("""
    SELECT COUNT(*)                 AS n_ratings,
           COUNT(DISTINCT user_id)  AS n_users,
           COUNT(DISTINCT movie_id) AS n_movies
    FROM ratings
""").show()

#%% Check: missing values
con.sql("""
    SELECT COUNT(*) FILTER (WHERE user_id  IS NULL) AS null_user,
           COUNT(*) FILTER (WHERE movie_id IS NULL) AS null_movie,
           COUNT(*) FILTER (WHERE rating   IS NULL) AS null_rating,
           COUNT(*) FILTER (WHERE rated_at IS NULL) AS null_rated_at
    FROM ratings
""").show()

#%% Check: rating values
con.sql("SELECT rating, COUNT(*) AS n FROM ratings GROUP BY rating ORDER BY rating").show()

con.sql("""
    SELECT COUNT(*) AS invalid_ratings
    FROM ratings
    WHERE rating < 0.5 OR rating > 5 OR (rating * 2) <> FLOOR(rating * 2)
""").show()

#%% Check: duplicate ratings
con.sql("""
    SELECT user_id, movie_id, COUNT(*) AS n
    FROM ratings
    GROUP BY user_id, movie_id
    HAVING COUNT(*) > 1
""").show()

#%% Check: duplicate films
con.sql("""
    SELECT movie_id, COUNT(*) as n
    FROM movies
    GROUP BY movie_id
    HAVING COUNT(*) > 1
""").show()

#%% Referential integrity: ratings for movies missing from movies table
con.sql("""
    SELECT COUNT(*) AS orphan_ratings
    FROM ratings r
    LEFT JOIN movies m USING (movie_id)
    WHERE m.movie_id IS NULL;
""").show()

#%% Timestamp sanity: check converted timestamps 
con.sql("""
    SELECT MIN(rated_at) AS first_rating,
        MAX(rated_at) AS last_rating
    FROM ratings
""").show()
