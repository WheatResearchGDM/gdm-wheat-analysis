"""Small, testable summaries for charts; never refit or change the active datacut."""
import unicodedata

import numpy as np
import pandas as pd
from scipy.stats import linregress

from analysis import GENOTYPE, TRIAL, data_fingerprint, environmental_data
from trial_units import identifier


def genotype_count(data):
    """Count genotype identities by GID, falling back to the displayed name."""
    if "gid" in data:
        gids = data["gid"].map(identifier).dropna()
        if not gids.empty:
            return int(gids.nunique())
    if GENOTYPE in data:
        names = data[GENOTYPE].map(identifier).dropna()
        return int(names.nunique())
    return 0


def head_to_head_wins(values, genotype_a, genotype_b):
    """One vote per paired trial; numerical ties are not assigned to either entry."""
    pairs = values.pivot(index=TRIAL, columns=GENOTYPE, values="genotype_yield")
    pairs = pairs.reindex(columns=[genotype_a, genotype_b]).replace([np.inf, -np.inf], np.nan).dropna()
    delta = pairs[genotype_a] - pairs[genotype_b]
    ties = np.isclose(delta, 0, rtol=0, atol=1e-8)
    counts = [int(((delta > 0) & ~ties).sum()), int(((delta < 0) & ~ties).sum()), int(ties.sum())]
    return pd.DataFrame({"Resultado": [genotype_a, genotype_b, "Empate"], "Ensaios": counts,
                         "Percentual": np.array(counts) / len(pairs) * 100 if len(pairs) else [0., 0., 0.]})


def material_category(value):
    if pd.isna(value):
        return "Não informada"
    normalized = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().strip().upper()
    if normalized in {"CHECK", "CHECKS", "TESTEMUNHA", "TESTEMUNHAS"}:
        return "Check"
    if normalized in {"COMERCIAL", "COMERCIAIS", "COMMERCIAL", "COMMERCIALS"}:
        return "Comercial"
    if normalized in {"EXPERIMENTAL", "EXPERIMENTAIS", "EXPERIMENTALS"}:
        return "Experimental"
    return str(value).strip()


def cycle_data(data, materials, fitted=None):
    """Join heading days by GID, one point per genotype. Return excluded count.

    Raw yield gives equal weight to observed trials. Estimated yield uses the
    fitted marginal genotype means (not just the random BLUP deviation).
    Ambiguous name/GID links are omitted rather than assigning arbitrary metadata.
    Inputs use the app's normalized GIDs.
    """
    if not {"gid", "days_to_spike"}.issubset(materials.columns) or "gid" not in data:
        raise ValueError("A aba auxiliar precisa conter gid e days_to_spike (dias ao espigamento).")
    if fitted is not None:
        if fitted["signature"] != data_fingerprint(data) or fitted["response"] != "yield":
            raise ValueError("Calcule BLUE ou BLUP para yield com o datacut atual.")
        values = fitted["genotypes"][[GENOTYPE, "Estimativa", "n", "Ensaios"]].copy()
    else:
        cells = environmental_data(data)
        values = cells.groupby(GENOTYPE, as_index=False).agg(
            Estimativa=("yield", "mean"), Ensaios=(TRIAL, "nunique"))
        valid = data.copy()
        valid["yield"] = pd.to_numeric(valid["yield"], errors="coerce")
        valid = valid.replace([np.inf, -np.inf], np.nan).dropna(subset=[GENOTYPE, TRIAL, "yield"])
        values = values.merge(valid.groupby(GENOTYPE).size().rename("n"), on=GENOTYPE, validate="one_to_one")
    links = data[[GENOTYPE, "gid"]].drop_duplicates()
    links = links.loc[~links[GENOTYPE].duplicated(keep=False)].dropna()
    metadata = materials.copy()
    if "category" not in metadata:
        metadata["category"] = None
    metadata = metadata[["gid", "days_to_spike", "category"]].drop_duplicates()
    metadata = metadata.loc[~metadata["gid"].duplicated(keep=False)].dropna(subset=["gid"])
    joined = values.merge(links, on=GENOTYPE, how="left", validate="one_to_one").merge(
        metadata, on="gid", how="left", validate="many_to_one")
    joined["days_to_spike"] = pd.to_numeric(
        joined["days_to_spike"].astype("string").str.replace(",", ".", regex=False), errors="coerce")
    joined = joined.replace([np.inf, -np.inf], np.nan).dropna(subset=["gid", "days_to_spike", "Estimativa"])
    joined["Categoria"] = joined["category"].map(material_category)
    return joined.drop(columns="category"), len(values) - len(joined)


def reference_regression(points):
    """OLS with intercept, equal genotype weights, selected checks/commercials only."""
    reference = points.loc[points["Categoria"].isin(["Check", "Comercial"])].dropna(
        subset=["days_to_spike", "Estimativa"])
    if len(reference) < 2 or reference["days_to_spike"].nunique() < 2:
        return None
    fit = linregress(reference["days_to_spike"].astype(float), reference["Estimativa"].astype(float))
    return {"slope": fit.slope, "intercept": fit.intercept, "r2": fit.rvalue ** 2,
            "n": len(reference), "xmin": float(reference["days_to_spike"].min()),
            "xmax": float(reference["days_to_spike"].max())}


def model_equation(method, fixed, random, interaction):
    """Illustrative terms; metadata labels are rendered separately by the app."""
    terms = [r"\mu", r"G_{g(i)}" if method == "BLUE" else r"u_{g(i)}"]
    terms += [rf"F_{{{j},i}}" for j in range(1, len(fixed) + 1)]
    terms += [rf"U_{{{j},i}}" for j in range(1, len(random) + 1)]
    if interaction:
        terms.append(r"u_{g(i)\times e(i)}")
    return "y_i = " + " + ".join(terms + [r"\varepsilon_i"])
