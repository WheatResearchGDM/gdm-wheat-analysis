"""Trial-level BLUE/BLUP estimation and environmental-index inputs.

Random intercepts are crossed variance components (one global MixedLM group).
Adjusted means standardize other fixed effects to the same trial-specific design
averages for every genotype. Overall means give each trial equal weight.
"""

import hashlib
import warnings

import numpy as np
import pandas as pd
from patsy import dmatrix
from scipy import sparse
import statsmodels.api as sm
from statsmodels.regression.mixed_linear_model import VCSpec

GENOTYPE = "germplasm_name"
TRIAL = "trial_unit_label"
GXE = "Genótipo × ensaio"


def data_fingerprint(data):
    digest = hashlib.sha256()
    digest.update(repr(list(zip(data.columns, data.dtypes.astype(str)))).encode())
    digest.update(pd.util.hash_pandas_object(data, index=True).values.tobytes())
    return digest.hexdigest()


def fit_trial_model(data, response="yield", method="BLUP", fixed=None,
                    random=None, interaction=True):
    """Fit additive fixed effects plus crossed categorical random intercepts.

Returns per-genotype adjusted means, observed genotype/trial predictions and
diagnostic arrays. Does not present predictions for unobserved genotype/trial pairs.
"""
    if method not in {"BLUE", "BLUP"}:
        raise ValueError("Escolha BLUE ou BLUP.")
    fixed = list(dict.fromkeys([TRIAL] if fixed is None else fixed))
    random = list(dict.fromkeys(random or []))
    fixed = [c for c in fixed if c != GENOTYPE]
    random = [c for c in random if c != GENOTYPE]
    (fixed if method == "BLUE" else random).append(GENOTYPE)
    if set(fixed) & set(random):
        raise ValueError("Um efeito não pode ser fixo e aleatório simultaneamente.")
    if TRIAL not in fixed + random:
        raise ValueError("Inclua Ensaio | Local entre os efeitos fixos ou aleatórios.")
    required = list(dict.fromkeys([response, GENOTYPE, TRIAL] + fixed + random))
    missing = set(required) - set(data.columns)
    if missing:
        raise ValueError("Colunas ausentes: " + ", ".join(sorted(missing)))
    dm = data[required].copy()
    dm[response] = pd.to_numeric(dm[response], errors="coerce")
    dm = dm.replace([np.inf, -np.inf], np.nan).dropna().reset_index(drop=True)
    if len(dm) < 20 or dm[GENOTYPE].nunique() < 2 or dm[TRIAL].nunique() < 2:
        raise ValueError("O ajuste exige ao menos 20 parcelas, 2 genótipos e 2 ensaios válidos.")
    categorical = {c for c in fixed + random if (
        c in [GENOTYPE, TRIAL] or not pd.api.types.is_numeric_dtype(dm[c])
        or pd.api.types.is_bool_dtype(dm[c]))}
    categorical.update(random)
    for c in categorical:
        dm[c] = dm[c].astype(str)
    q = lambda c: f"Q({c!r})"
    term = lambda c: f"C({q(c)})" if c in categorical else q(c)
    formula = "1 + " + " + ".join(term(c) for c in fixed) if fixed else "1"
    X = dmatrix(formula, dm, return_type="dataframe")
    if np.linalg.matrix_rank(X.to_numpy()) < X.shape[1]:
        raise ValueError(
            "Os efeitos fixos estão confundidos ou o datacut não conecta os genótipos. "
            "Remova efeitos redundantes (ex.: ano/local já contidos em ensaio) "
            "ou escolha ensaios com materiais em comum."
        )
    if len(dm) <= X.shape[1]:
        raise ValueError("Não há graus de liberdade residuais para este modelo.")

    levels = {c: sorted(dm[c].unique()) for c in random}
    codes = {c: pd.Categorical(dm[c], categories=levels[c]).codes for c in random}
    if interaction:
        pairs = list(zip(dm[GENOTYPE], dm[TRIAL]))
        levels[GXE] = sorted(set(pairs))
        lookup = {v: i for i, v in enumerate(levels[GXE])}
        codes[GXE] = np.array([lookup[v] for v in pairs])
        if len(levels[GXE]) == len(dm):
            raise ValueError("Sem repetições por genótipo × ensaio: desative a interação aleatória.")
    names = sorted(levels)
    matrices = [sparse.csr_matrix(
        (np.ones(len(dm)), (np.arange(len(dm)), codes[c])),
        shape=(len(dm), len(levels[c])),
    ) for c in names]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        if names:
            vc = VCSpec(names, [[list(map(str, levels[c]))] for c in names],
                        [[matrix] for matrix in matrices])
            model = sm.MixedLM(dm[response], X, groups=np.ones(len(dm)),
                               exog_re=np.empty((len(dm), 0)), exog_vc=vc)
            result = model.fit(reml=True, method=["lbfgs", "bfgs"], maxiter=300, disp=False)
            if not result.converged:
                raise ValueError("O modelo não convergiu. Simplifique os efeitos ou ajuste o datacut.")
            beta = np.asarray(result.fe_params)
            coefficients = np.asarray(result.random_effects[1.0])
            variance = dict(zip(names, result.vcomp))
        else:
            result = sm.OLS(dm[response], X).fit()
            beta = np.asarray(result.params)
            coefficients = np.array([])
            variance = {}
    if not np.isfinite(beta).all() or not np.isfinite(coefficients).all():
        raise ValueError("O ajuste produziu estimativas inválidas; reveja o modelo.")
    effects = {}
    offset = 0
    for name in names:
        effects[name] = dict(zip(levels[name], coefficients[offset:offset + len(levels[name])]))
        offset += len(levels[name])

    # All genotypes share the same nuisance-effect distribution within each trial.
    trial_design = X.groupby(dm[TRIAL]).mean()
    genotype_slice = X.design_info.term_name_slices.get(term(GENOTYPE))
    observed = set(zip(dm[GENOTYPE], dm[TRIAL]))
    geno_rows, cell_rows = [], []
    for genotype in sorted(dm[GENOTYPE].unique()):
        design = trial_design.to_numpy().copy()
        if genotype_slice is not None:
            genotype_design = X.loc[dm[GENOTYPE].eq(genotype)].iloc[0].to_numpy()
            design[:, genotype_slice] = genotype_design[genotype_slice]
        fixed_prediction = design @ beta
        genotype_effect = effects.get(GENOTYPE, {}).get(genotype, 0.0)
        geno_rows.append({GENOTYPE: genotype, "Estimativa": fixed_prediction.mean() + genotype_effect,
                          "Método": method, "Efeito genotípico": genotype_effect if method == "BLUP" else np.nan})
        for trial, pred in zip(trial_design.index, fixed_prediction):
            if (genotype, trial) in observed:
                cell_rows.append({GENOTYPE: genotype, TRIAL: trial,
                                  "predicted": pred + genotype_effect
                                  + effects.get(TRIAL, {}).get(trial, 0.0)
                                  + effects.get(GXE, {}).get((genotype, trial), 0.0)})
    genotypes = pd.DataFrame(geno_rows).sort_values("Estimativa", ascending=False).reset_index(drop=True)
    genotypes.insert(0, "Ranking", np.arange(1, len(genotypes) + 1))
    if method == "BLUE":
        genotypes = genotypes.drop(columns="Efeito genotípico")
    cells = pd.DataFrame(cell_rows).merge(
        dm.groupby([GENOTYPE, TRIAL], as_index=False).agg(
            raw_mean=(response, "mean"), n=(response, "count")),
        on=[GENOTYPE, TRIAL], validate="one_to_one")
    variance["Residual"] = float(result.scale)
    # statsmodels 0.14 fittedvalues concatenates sparse VC matrices as dense
    # objects. Compute X beta + sum(Z u) explicitly, retaining sparse products.
    fitted = X.to_numpy() @ beta
    offset = 0
    for name, matrix in zip(names, matrices):
        fitted += np.asarray(matrix @ coefficients[offset:offset + len(levels[name])]).ravel()
        offset += len(levels[name])
    if not np.isfinite(fitted).all() or not np.isfinite(cells["predicted"]).all():
        raise ValueError("As predições não são finitas; reveja o ajuste.")
    return {"result": result, "genotypes": genotypes, "cells": cells,
            "variance": pd.DataFrame({"Componente": list(variance), "Variância": list(variance.values())}),
            "fixed_coefficients": pd.DataFrame({"Efeito": X.columns, "Estimativa": beta,
                "EP": np.asarray(result.bse_fe if names else result.bse)}),
            "fitted": fitted, "residuals": dm[response].to_numpy() - fitted,
            "response": response, "method": method, "fixed": fixed, "random": random,
            "interaction": interaction, "nobs": len(dm), "omitted": len(data) - len(dm),
            "warnings": list(dict.fromkeys(str(w.message) for w in caught)),
            "signature": data_fingerprint(data)}


def environmental_data(data, fitted=None):
    """One value per observed genotype/trial; environments weight genotypes equally."""
    if fitted is not None:
        if fitted["signature"] != data_fingerprint(data) or fitted["response"] != "yield":
            raise ValueError("Reajuste a produtividade com o datacut atual.")
        return fitted["cells"][[GENOTYPE, TRIAL, "predicted"]].rename(columns={"predicted": "yield"})
    clean = data[[GENOTYPE, TRIAL, "yield"]].copy()
    clean["yield"] = pd.to_numeric(clean["yield"], errors="coerce")
    clean = clean.replace([np.inf, -np.inf], np.nan).dropna()
    return clean.groupby([GENOTYPE, TRIAL], as_index=False)["yield"].mean()
