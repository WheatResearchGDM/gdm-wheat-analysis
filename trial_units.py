"""Conditional trial identity and stable source-row identifiers."""
import hashlib
import json

import numpy as np
import pandas as pd

SOURCE_ROW = "_source_row_id"
TRIAL_KEY = "_trial_unit_key"
TRIAL_LABEL = "trial_unit_label"


def identifier(value):
    if pd.isna(value):
        return None
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)) and float(value).is_integer():
        return str(int(value))
    return str(value).strip() or None


def add_trial_unit_columns(data):
    """Prefix trial units with year and use DEV environment or location by area.

    A PROD-PLACEMENT trial_id may legitimately span multiple DEV environments.
    Human labels are unique for the technical keys, even in a mixed-area import.
    """
    required = {"trial_id", "trial_name", "year"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError("Colunas necessárias para identificar os ensaios ausentes: " + ", ".join(sorted(missing)))
    enriched = data.copy()
    area = enriched.get("area", pd.Series("", index=enriched.index)).astype("string")
    prod = area.str.strip().str.upper().eq("PROD-PLACEMENT").fillna(False)
    needed = ({"environment_dev_file"} if prod.any() else set()) | ({"location_name"} if (~prod).any() else set())
    if needed - set(enriched):
        raise ValueError("Colunas necessárias à unidade de ensaio: " + ", ".join(sorted(needed - set(enriched))))
    ids = enriched["trial_id"].map(identifier)
    if ids.isna().any():
        raise ValueError(f"A coluna trial_id contém {int(ids.isna().sum())} registro(s) sem identificação.")
    names = enriched["trial_name"].map(identifier)
    years = enriched["year"].map(identifier)
    if years.isna().any():
        raise ValueError(f"A coluna year contém {int(years.isna().sum())} registro(s) sem identificação.")
    location = enriched.get("location_name", pd.Series(None, index=enriched.index, dtype=object)).map(identifier)
    environment = enriched.get("environment_dev_file", pd.Series(None, index=enriched.index, dtype=object)).map(identifier)
    if (prod & (environment.isna() | names.isna())).any():
        count = int((prod & (environment.isna() | names.isna())).sum())
        raise ValueError(f"PROD-PLACEMENT: {count} registro(s) sem trial_name ou environment_dev_file. "
                         "Preencha a identificação; location_name não será usado como substituto.")
    second = location.where(~prod, environment)
    basis = pd.Series(np.where(prod, "DEV", "Local"), index=enriched.index)
    enriched[TRIAL_KEY] = [
        json.dumps([b, y, n, s], ensure_ascii=False)
        for b, y, n, s in zip(basis, years, names, second)
    ]
    labels = years + " | " + names.fillna("(Nulo)") + " | " + second.fillna("(Nulo)")
    units = pd.DataFrame({"key": enriched[TRIAL_KEY], "label": labels, "basis": basis}).drop_duplicates("key")
    collision = units["label"].duplicated(keep=False)
    units.loc[collision, "label"] += " [" + units.loc[collision, "basis"] + "]"
    collision = units["label"].duplicated(keep=False)
    units.loc[collision, "label"] += " [" + units.loc[collision, "key"].map(
        lambda key: hashlib.sha256(key.encode()).hexdigest()[:10]) + "]"
    enriched[TRIAL_LABEL] = enriched[TRIAL_KEY].map(units.set_index("key")["label"])
    regular = enriched.loc[~prod].assign(_normalized_trial_id=ids.loc[~prod])
    conflicts = regular.groupby("_normalized_trial_id")[TRIAL_KEY].nunique()
    conflicts = conflicts.loc[conflicts > 1]
    if not conflicts.empty:
        raise ValueError("O mesmo trial_id está associado a mais de uma combinação year | trial_name | location_name "
                         "fora de PROD-PLACEMENT. Revise: " + ", ".join(conflicts.index[:5]))
    if SOURCE_ROW not in enriched:
        enriched[SOURCE_ROW] = np.arange(2, len(enriched) + 2)
    return enriched
