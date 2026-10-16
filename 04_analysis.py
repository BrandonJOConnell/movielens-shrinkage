#%%
import duckdb
import numpy as np

con = duckdb.connect("movielens.duckdb", read_only=True)
df = con.sql("SELECT * FROM film_stats").df()

# %% extract global stats 
overall_mean_rating = (df.n * df.mean_rating).sum() / df.n.sum() 
overall_std_rating = np.sqrt((df.n * df.var_rating).sum() / df.n.sum())
print(f"Overall Mean Rating: {overall_mean_rating}")
print(f"Overall Std Rating: {overall_std_rating}")

# %%
df["sq_dev"] = (df.mean_rating - overall_mean_rating) ** 2
df["noise"] = overall_std_rating ** 2 / df.n # uses global std deviation weighting
tau2 = (df.sq_dev - df.noise).mean()
tau2 = (df[df.n >= 20].sq_dev - df[df.n >= 20].noise).mean()

print(f"Tau^2 using all ratings of all movies: {tau2}")
print(f"Tau^2 using all movies with n ratings >= 20: {tau2}")

# ^ above shows that using global std-dev is perhaps not ideal

#%% Compute pooled std_dev in buckets (more representative)  
con.sql("""
    SELECT CASE WHEN n < 5      THEN '2-4'
                WHEN n < 10     THEN '5-9'
                WHEN n < 100    THEN '10-99'
                WHEN n < 1000   THEN '100-999'
                ELSE '1000+' END AS bucket,
           COUNT(*) AS n_films,
           SQRT(SUM((n - 1) * var_rating) / SUM(n - 1)) AS sigma_pooled
    FROM film_stats
    WHERE n > 1
    GROUP BY bucket
    ORDER BY MIN(n)
""").show()

#%% Use bucketed pooled std_dev values and view new tau2
df["sigma"] = np.select(
    [df.n < 10, df.n < 100, df.n < 1000],      # conditions, checked in order
    [1.08,      1.046,      0.984],            # value for each condition
    default=0.953,                             # everything else (n >= 1000)
)
df["noise"] = df.sigma ** 2 / df.n
tau2_all = (df.sq_dev - df.noise).mean()
tau2_20  = (df.sq_dev[df.n >= 20] - df.noise[df.n >= 20]).mean()

# %%
