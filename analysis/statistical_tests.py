"""Inferential tests. Every function returns a plain dict with:
name, null, alternative, statistic, df, p_value, alpha, ci, decision,
interpretation, warnings, details."""
import numpy as np
from scipy import stats

ALT = {"two-sided": "two-sided", "greater": "greater", "less": "less"}


def _clean(a):
    return np.asarray([v for v in a if v is not None and not np.isnan(v)], float)


def _ci_t(est, se, df, alpha):
    t = stats.t.ppf(1 - alpha / 2, df)
    return (est - t * se, est + t * se)


def _ci_z(est, se, alpha):
    z = stats.norm.ppf(1 - alpha / 2)
    return (est - z * se, est + z * se)


def _alt_text(alt, sym, val):
    return {"two-sided": f"{sym} ≠ {val}", "greater": f"{sym} > {val}",
            "less": f"{sym} < {val}"}[alt]


def _verdict(p, alpha, subject):
    if p < alpha:
        return ("Reject H0", f"The result is statistically significant at "
                f"α = {alpha}: there is evidence that {subject}.")
    return ("Fail to reject H0", f"The result is not statistically significant at "
            f"α = {alpha}: there is not enough evidence that {subject}. "
            "This does not prove the null hypothesis true.")


def _normality_warn(x, label, warns):
    if len(x) < 3:
        return
    if len(x) < 30:
        warns.append(f"{label}: n = {len(x)} (<30). The t-test relies on "
                     "approximately normal data for small samples.")
    if 3 <= len(x) <= 5000 and np.ptp(x) > 0:
        w, pn = stats.shapiro(x)
        if pn < 0.05:
            warns.append(f"{label}: Shapiro-Wilk suggests non-normality "
                         f"(p = {pn:.3f}). Interpret with caution"
                         + ("; consider a non-parametric test." if len(x) < 30 else "."))


def _p(t, df, alt, dist="t"):
    d = stats.t(df) if dist == "t" else stats.norm
    if alt == "two-sided":
        return float(2 * d.sf(abs(t)))
    return float(d.sf(t) if alt == "greater" else d.cdf(t))


def one_sample_t(x, mu0, alpha=0.05, alt="two-sided"):
    x = _clean(x); n = len(x)
    if n < 2: raise ValueError("At least 2 scores are needed.")
    if np.std(x, ddof=1) == 0: raise ValueError("All scores are identical; the test cannot be computed.")
    m, s = x.mean(), x.std(ddof=1); se = s / np.sqrt(n); df = n - 1
    t = (m - mu0) / se; p = _p(t, df, alt)
    ci = _ci_t(m, se, df, alpha)
    dec, txt = _verdict(p, alpha, f"the mean differs from {mu0}" if alt == "two-sided"
                        else f"the mean is {alt} than {mu0}")
    w = []; _normality_warn(x, "Sample", w)
    return dict(name="One-sample t-test", null=f"μ = {mu0}",
                alternative=_alt_text(alt, "μ", mu0), statistic=t, df=df,
                p_value=p, alpha=alpha, ci=ci, ci_label=f"{(1-alpha)*100:.0f}% CI for the mean",
                decision=dec, interpretation=txt, warnings=w,
                details={"n": n, "mean": m, "sd": s, "se": se})


def independent_t(a, b, alpha=0.05, alt="two-sided", equal_var=False):
    a, b = _clean(a), _clean(b)
    if len(a) < 2 or len(b) < 2: raise ValueError("Each group needs at least 2 scores.")
    if np.std(a, ddof=1) == 0 and np.std(b, ddof=1) == 0:
        raise ValueError("Both groups have zero variance; the test cannot be computed.")
    va, vb = a.var(ddof=1), b.var(ddof=1); na, nb = len(a), len(b)
    diff = a.mean() - b.mean()
    if equal_var:
        df = na + nb - 2; sp2 = ((na-1)*va + (nb-1)*vb) / df; se = np.sqrt(sp2*(1/na+1/nb))
    else:
        se = np.sqrt(va/na + vb/nb)
        df = (va/na + vb/nb)**2 / ((va/na)**2/(na-1) + (vb/nb)**2/(nb-1))
    t = diff / se; p = _p(t, df, alt); ci = _ci_t(diff, se, df, alpha)
    dec, txt = _verdict(p, alpha, "the two group means differ" if alt == "two-sided"
                        else f"Group 1's mean is {alt} than Group 2's")
    w = []
    _normality_warn(a, "Group 1", w); _normality_warn(b, "Group 2", w)
    if len(a) > 2 and len(b) > 2:
        lp = stats.levene(a, b).pvalue
        if lp < 0.05 and equal_var:
            w.append(f"Levene's test suggests unequal variances (p = {lp:.3f}) "
                     "but pooled variance was selected. Welch's test is safer.")
    return dict(name=("Independent-samples t-test (pooled)" if equal_var
                      else "Independent-samples t-test (Welch)"),
                null="μ₁ − μ₂ = 0", alternative=_alt_text(alt, "μ₁ − μ₂", 0),
                statistic=t, df=df, p_value=p, alpha=alpha, ci=ci,
                ci_label=f"{(1-alpha)*100:.0f}% CI for the mean difference",
                decision=dec, interpretation=txt, warnings=w,
                details={"n1": na, "n2": nb, "mean1": a.mean(), "mean2": b.mean(),
                         "sd1": np.sqrt(va), "sd2": np.sqrt(vb), "difference": diff})


def paired_t(before, after, alpha=0.05, alt="two-sided"):
    b, a = np.asarray(before, float), np.asarray(after, float)
    if len(a) != len(b): raise ValueError("Paired samples must have the same length.")
    ok = ~(np.isnan(a) | np.isnan(b)); a, b = a[ok], b[ok]
    d = a - b; n = len(d)
    if n < 2: raise ValueError("At least 2 complete pairs are needed.")
    if np.std(d, ddof=1) == 0: raise ValueError("All differences are identical; the test cannot be computed.")
    md, sd = d.mean(), d.std(ddof=1); se = sd/np.sqrt(n); df = n-1
    t = md/se; p = _p(t, df, alt); ci = _ci_t(md, se, df, alpha)
    dec, txt = _verdict(p, alpha, "the mean change (second − first) differs from zero"
                        if alt == "two-sided" else f"the mean change is {alt} than zero")
    w = []; _normality_warn(d, "Differences", w)
    return dict(name="Paired-samples t-test", null="μ_d = 0",
                alternative=_alt_text(alt, "μ_d", 0), statistic=t, df=df,
                p_value=p, alpha=alpha, ci=ci,
                ci_label=f"{(1-alpha)*100:.0f}% CI for the mean difference",
                decision=dec, interpretation=txt, warnings=w,
                details={"pairs": n, "mean_difference": md, "sd_difference": sd})


Z_NOTE = ("A z-test is appropriate only when the population standard deviation "
          "is KNOWN (e.g. from a standardised test), or the samples are very "
          "large and σ is well estimated. If σ is estimated from a small class, "
          "use a t-test instead.")


def one_sample_z(x, mu0, sigma, alpha=0.05, alt="two-sided"):
    x = _clean(x); n = len(x)
    if n < 1: raise ValueError("At least 1 score is needed.")
    if sigma is None or sigma <= 0: raise ValueError("Population σ must be a positive number.")
    se = sigma/np.sqrt(n); z = (x.mean()-mu0)/se; p = _p(z, None, alt, "z")
    ci = _ci_z(x.mean(), se, alpha)
    dec, txt = _verdict(p, alpha, f"the mean differs from {mu0}" if alt == "two-sided"
                        else f"the mean is {alt} than {mu0}")
    w = [Z_NOTE]
    if n < 30: w.append(f"n = {n} (<30): normality of the population is required for a valid z-test.")
    return dict(name="One-sample z-test", null=f"μ = {mu0}",
                alternative=_alt_text(alt, "μ", mu0), statistic=z, df=None,
                p_value=p, alpha=alpha, ci=ci, ci_label=f"{(1-alpha)*100:.0f}% CI for the mean",
                decision=dec, interpretation=txt, warnings=w,
                details={"n": n, "mean": x.mean(), "sigma": sigma, "se": se})


def two_sample_z(a, b, sigma1, sigma2, alpha=0.05, alt="two-sided"):
    a, b = _clean(a), _clean(b)
    if len(a) < 1 or len(b) < 1: raise ValueError("Each group needs at least 1 score.")
    if not sigma1 or not sigma2 or sigma1 <= 0 or sigma2 <= 0:
        raise ValueError("Both population σ values must be positive numbers.")
    se = np.sqrt(sigma1**2/len(a) + sigma2**2/len(b)); diff = a.mean()-b.mean()
    z = diff/se; p = _p(z, None, alt, "z"); ci = _ci_z(diff, se, alpha)
    dec, txt = _verdict(p, alpha, "the two group means differ" if alt == "two-sided"
                        else f"Group 1's mean is {alt} than Group 2's")
    w = [Z_NOTE]
    if min(len(a), len(b)) < 30: w.append("A group has fewer than 30 scores: normality of the populations is required.")
    return dict(name="Two-sample z-test", null="μ₁ − μ₂ = 0",
                alternative=_alt_text(alt, "μ₁ − μ₂", 0), statistic=z, df=None,
                p_value=p, alpha=alpha, ci=ci,
                ci_label=f"{(1-alpha)*100:.0f}% CI for the mean difference",
                decision=dec, interpretation=txt, warnings=w,
                details={"n1": len(a), "n2": len(b), "mean1": a.mean(),
                         "mean2": b.mean(), "difference": diff, "se": se})


def descriptive(x):
    x = _clean(x)
    if len(x) == 0: raise ValueError("No numeric scores found.")
    vals, counts = np.unique(x, return_counts=True)
    modes = vals[counts == counts.max()]
    mode_txt = ", ".join(f"{m:g}" for m in modes[:5]) + (" …" if len(modes) > 5 else "")
    if counts.max() == 1: mode_txt = "No repeated value"
    return {"N": len(x), "Mean": float(x.mean()), "Median": float(np.median(x)),
            "Mode": mode_txt, "Minimum": float(x.min()), "Maximum": float(x.max()),
            "Range": float(np.ptp(x)),
            "Variance (sample)": float(x.var(ddof=1)) if len(x) > 1 else float("nan"),
            "Std. deviation (sample)": float(x.std(ddof=1)) if len(x) > 1 else float("nan")}
