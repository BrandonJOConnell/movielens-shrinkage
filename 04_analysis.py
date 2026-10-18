#%%
import duckdb
import numpy as np

con = duckdb.connect("movielens.duckdb", read_only=True)
df = con.sql("SELECT f.*, m.title FROM film_stats f JOIN movies m USING (movie_id)").df()

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

# variance of each film's average rating: sigma_j^2 / n_j
df["noise"] = df.sigma ** 2 / df.n

#%% Perform empirical Bayes: estimates prior from data

# Function to estimate mu and tau^2 (alternating until they settle)
def estimate_mu_tau2(d, tau2=0.5, n_iter=50, method='ml'):
    for _ in range(n_iter):
        prec = 1 / (tau2 + d.noise)                             # 1 / v_j : i.e. trust, the noisy films count for less
        mu = (prec * d.mean_rating).sum() / prec.sum()  
        resid = (d.mean_rating - mu) ** 2 - d.noise
        if method == "ml":
            tau2 = (prec**2 * resid).sum() / (prec**2).sum()    # ML fixed-point update
        else:     
            tau2 = resid.mean()                                 # method of moments
        tau2 = max(tau2, 1e-10)                                 # keeps tau**2 positive
    return mu, tau2

#%% 
for method in ("moments", "ml"):
    mu_all, tau2_all = estimate_mu_tau2(df, method=method)
    print(f"{method:8s} mu = {mu_all:.3f}, tau^2 = {tau2_all:.3f}")

# use defaults 
mu_all, tau2_all = estimate_mu_tau2(df)
mu_20, tau2_20 = estimate_mu_tau2(df[df.n >= 20])
print(f"all films:   mu = {mu_all:.3f}, tau^2 = {tau2_all:.3f}")
print(f"n >= 20:     mu = {mu_20:.3f}, tau^2 = {tau2_20:.3f}")

#%% shrinkage
df["w"] = tau2_all / (tau2_all + df.noise)    # tau2 / (tau2 + noise)
df["shrunk"] =  mu_all + df.w * (df.mean_rating - mu_all)

#%% Explore raw top rated films and "corrected" rated films
print(df.loc[df.n == 1, "w"].iloc[0])       # about 0.17
print(df.loc[df.n >= 1000, "w"].min())      # above 0.99

cols = ["movie_id", "title", "n", "mean_rating", "shrunk"]
print(df.nlargest(15, "mean_rating")[cols])    # raw top 15
print(df.nlargest(15, "shrunk")[cols])         # shrunk top 15

# Each film’s rank by raw average
df["raw_rank"] = df["mean_rating"].rank(ascending=False, method="min").astype(int)
df["shrunk_rank"] = df["shrunk"].rank(ascending=False, method="min").astype(int)
# NB: All films with a raw mean of 5.0 are tied for rank 1.

#%% save the headline tables for the README
from pathlib import Path
Path("results").mkdir(exist_ok=True)

# sort_values makes the tie order deterministic (nlargest breaks ties arbitrarily)
raw_top = (df.sort_values(["mean_rating", "n"], ascending=False)
             .head(15)[["title", "n", "mean_rating", "shrunk", "shrunk_rank"]])
shrunk_top = df.nlargest(15, "shrunk")[["title", "n", "mean_rating", "shrunk", "raw_rank"]]

raw_top.to_markdown("results/top15_raw.md", index=False, floatfmt=".3f", intfmt=",")
shrunk_top.to_markdown("results/top15_shrunk.md", index=False, floatfmt=".3f", intfmt=",")

#%% How many films have a perfect raw mean? 
df.sort_values(["mean_rating", "n"], ascending=False).head(15)[cols]
print((df.mean_rating == 5).sum())

#%% Plotting: 
import matplotlib.pyplot as plt

# view original raw ratings and how they compare to the mean and variance approximation
d = df.sort_values("n")
half = 1.96 * np.sqrt(tau2_all + d.noise)

fig, ax = plt.subplots(figsize=(8, 5))
ax.scatter(df.n, df.mean_rating, s=3, alpha=0.15, color="#2563eb", linewidths=0)
ax.plot(d.n, mu_all + half, color="0.4", lw=1.5)
ax.plot(d.n, mu_all - half, color="0.4", lw=1.5)
ax.axhline(mu_all, color="0.4", lw=1, ls="--")
ax.set_xscale("log")
ax.set_xlabel("Number of ratings (log scale)")
ax.set_ylabel("Mean rating")
ax.set_title("Few ratings, wild averages")
ax.grid(alpha=0.2)
for side in ("top", "right"):
    ax.spines[side].set_visible(False)
fig.savefig("figures/funnel_raw.png", dpi=300, bbox_inches="tight")

# plot side by side of the raw ratings and post-shrinkage ratings
fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)

for ax, col, title in zip(axes, ["mean_rating", "shrunk"],
                          ["Raw average", "After shrinkage"]):
    ax.scatter(df.n, df[col], s=3, alpha=0.15, color="#2563eb", linewidths=0)
    ax.axhline(mu_all, color="0.4", lw=1, ls="--")
    ax.set_xscale("log")
    ax.set_title(title)
    ax.set_xlabel("Number of ratings (log scale)")
    ax.grid(alpha=0.2)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

axes[0].set_ylabel("Rating")
plt.tight_layout()
fig.savefig("figures/funnel_raw_vs_shrunk.png", dpi=300, bbox_inches="tight")


