#%%
import duckdb
import numpy as np

con = duckdb.connect("movielens.duckdb", read_only=True)
df = con.sql("SELECT * FROM film_stats").df()

#%% Compute pooled std_dev in buckets (more representative)  
bucket_sigma = con.sql("""
    SELECT CASE WHEN n < 10      THEN '2-9'
                WHEN n < 100    THEN '10-99'
                WHEN n < 1000   THEN '100-999'
                ELSE '1000+' END AS bucket,
           COUNT(*) AS n_films,
           SQRT(SUM((n - 1) * var_rating) / SUM(n - 1)) AS sigma_pooled
    FROM film_stats
    WHERE n > 1
    GROUP BY bucket
    ORDER BY MIN(n)
""").df() 
con.close()

print(bucket_sigma)

#%% give every film a sigma and a noise level (n = 1 films get the 2-9 sigma: an assumption)
s = bucket_sigma["sigma_pooled"].to_numpy()
df["sigma"] = np.select([df.n < 10, df.n < 100, df.n < 1000], [s[0], s[1], s[2]], default=s[3])

# computes std dev for the films, weighted by their number of ratings
df["noise"] = df.sigma ** 2 / df.n

#%% Perform empirical Bayes: estimates prior from data
# estimate mu and tau^2 together (alternating until they settle)
def estimate_mu_tau2(d, tau2=0.5, n_iter=10):
    for _ in range(n_iter):
        prec = 1 / (tau2 + d.noise)                       # trust: noisy films count for less
        mu = (prec * d.mean_rating).sum() / prec.sum()
        tau2 = ((d.mean_rating - mu) ** 2 - d.noise).mean()
    return mu, tau2

#%% 
mu_all, tau2_all = estimate_mu_tau2(df)
mu_20, tau2_20 = estimate_mu_tau2(df[df.n >= 20])
print(f"all films:   mu = {mu_all:.3f}, tau^2 = {tau2_all:.3f}")
print(f"n >= 20:     mu = {mu_20:.3f}, tau^2 = {tau2_20:.3f}")









