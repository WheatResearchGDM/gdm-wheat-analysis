"""Small, testable summaries for charts; never refit or change the active datacut."""
import unicodedata

import numpy as np
import pandas as pd
from scipy.stats import linregress

from analysis import GENOTYPE, TRIAL, data_fingerprint, environmental_data
from trial_units import identifier

REPORTING_API_VERSION = 2


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


def genotype_connectivity(data):
    """Return trial-by-trial counts of shared GIDs (diagonal = trial total)."""
    if TRIAL not in data:
        raise ValueError("A unidade de ensaio não está disponível.")
    identity = "gid" if "gid" in data and data["gid"].notna().any() else GENOTYPE
    if identity not in data:
        raise ValueError("A identidade dos genótipos não está disponível.")
    pairs = data[[TRIAL, identity]].copy()
    pairs[TRIAL] = pairs[TRIAL].map(identifier)
    pairs[identity] = pairs[identity].map(identifier)
    pairs = pairs.dropna().drop_duplicates()
    if pairs.empty:
        return pd.DataFrame(dtype=int)
    incidence = pd.crosstab(pairs[TRIAL], pairs[identity]).astype(int)
    matrix = incidence @ incidence.T
    matrix.index.name = TRIAL
    matrix.columns.name = TRIAL
    return matrix.astype(int)


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


def protein_data(data, materials, fitted=None):
    """One point per genotype: trial-weighted raw protein and raw/estimated yield."""
    required = {GENOTYPE, TRIAL, "protein", "gid"}
    if missing := required - set(data.columns):
        raise ValueError("Colunas necessárias ausentes: " + ", ".join(sorted(missing)))

    raw = data[[GENOTYPE, TRIAL, "gid", "protein", "yield"]].copy()
    raw["protein"] = pd.to_numeric(
        raw["protein"].astype("string").str.replace(",", ".", regex=False),
        errors="coerce",
    )
    raw["yield"] = pd.to_numeric(raw["yield"], errors="coerce")
    raw = raw.replace([np.inf, -np.inf], np.nan)
    protein_cells = raw.dropna(subset=[GENOTYPE, TRIAL, "protein"]).groupby(
        [GENOTYPE, TRIAL], as_index=False,
    )["protein"].mean()
    protein = protein_cells.groupby(GENOTYPE, as_index=False).agg(
        Proteína=("protein", "mean"), Ensaios_proteína=(TRIAL, "nunique"),
    )
    protein_n = raw.groupby(GENOTYPE)["protein"].count().rename("n_proteína")
    protein = protein.merge(protein_n, on=GENOTYPE, validate="one_to_one")

    if fitted is not None:
        if fitted["signature"] != data_fingerprint(data) or fitted["response"] != "yield":
            raise ValueError("Calcule BLUE ou BLUP para yield com o datacut atual.")
        productivity = fitted["genotypes"][[GENOTYPE, "Estimativa", "n", "Ensaios"]].copy()
    else:
        yield_cells = environmental_data(data)
        productivity = yield_cells.groupby(GENOTYPE, as_index=False).agg(
            Estimativa=("yield", "mean"), Ensaios=(TRIAL, "nunique"),
        )
        yield_n = raw.groupby(GENOTYPE)["yield"].count().rename("n")
        productivity = productivity.merge(yield_n, on=GENOTYPE, validate="one_to_one")

    before = len(productivity)
    links = data[[GENOTYPE, "gid"]].drop_duplicates()
    links = links.loc[~links[GENOTYPE].duplicated(keep=False)].dropna()
    metadata = materials.copy()
    if "category" not in metadata:
        metadata["category"] = None
    metadata = metadata[["gid", "category"]].drop_duplicates()
    metadata = metadata.loc[~metadata["gid"].duplicated(keep=False)].dropna(subset=["gid"])
    joined = productivity.merge(protein, on=GENOTYPE, validate="one_to_one").merge(
        links, on=GENOTYPE, how="left", validate="one_to_one",
    ).merge(metadata, on="gid", how="left", validate="many_to_one")
    joined = joined.dropna(subset=["gid", "Proteína", "Estimativa"])
    joined["Categoria"] = joined["category"].map(material_category)
    return joined.drop(columns="category"), before - len(joined)


def reference_regression(points, x="days_to_spike", y="Estimativa"):
    """OLS with intercept, equal genotype weights, selected checks/commercials only."""
    reference = points.loc[points["Categoria"].isin(["Check", "Comercial"])].dropna(
        subset=[x, y])
    if len(reference) < 2 or reference[x].nunique() < 2:
        return None
    fit = linregress(reference[x].astype(float), reference[y].astype(float))
    return {"slope": fit.slope, "intercept": fit.intercept, "r2": fit.rvalue ** 2,
            "n": len(reference), "xmin": float(reference[x].min()),
            "xmax": float(reference[x].max())}


def selection_tiers(points):
    """Classify non-reference genotypes relative to the mean of all checks."""
    checks = points.loc[points["Categoria"].eq("Check"), "Estimativa"].dropna()
    if checks.empty or not np.isfinite(checks.mean()) or np.isclose(checks.mean(), 0):
        raise ValueError("A classificação em tiers exige ao menos uma testemunha com produtividade válida.")
    result = points.copy()
    check_mean = float(checks.mean())
    result["Ganho vs. testemunhas (%)"] = (result["Estimativa"] / check_mean - 1) * 100
    reference = result["Categoria"].isin(["Check", "Comercial"])
    gain = result["Ganho vs. testemunhas (%)"]
    result["Tier"] = np.select(
        [reference, gain.gt(5), gain.gt(0)],
        ["Checks + Comerciais", "Tier > 5%", "Tier 0,1% a 5%"],
        default="Tier ≤ 0%",
    )
    return result, check_mean


def model_equation(method, fixed, random, interaction):
    """Illustrative terms; metadata labels are rendered separately by the app."""
    terms = [r"\mu", r"G_{g(i)}" if method == "BLUE" else r"u_{g(i)}"]
    terms += [rf"F_{{{j},i}}" for j in range(1, len(fixed) + 1)]
    terms += [rf"U_{{{j},i}}" for j in range(1, len(random) + 1)]
    if interaction:
        terms.append(r"u_{g(i)\times e(i)}")
    return "y_i = " + " + ".join(terms + [r"\varepsilon_i"])
