"""GDM Wheat Phenotypic Analysis - Mixed Models (Streamlit + statsmodels)
Versao com dados demonstrativos embutidos (sem dependencia de SQL Warehouse).
"""

import hashlib
import html
import json
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import statsmodels.formula.api as smf
from scipy import stats

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="GDM Wheat Analysis",
    page_icon="\U0001F33E",
    layout="wide",
    initial_sidebar_state="expanded",
)

GDM_NAVY = "#09243B"
GDM_LIME = "#B5BE04"
GDM_GRAY = "#54595F"
GDM_OFFWHITE = "#F5F7F2"
GDM_SKY = "#DCE7EA"
GDM_CORAL = "#D55E45"
GDM_SCALE = [
    [0.0, "#E9EDB0"],
    [0.45, GDM_LIME],
    [1.0, GDM_NAVY],
]

APP_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = APP_DIR / "template_dados_fenotipicos.xlsx"
REQUIRED_UPLOAD_COLUMNS = {"trial_name", "germplasm_name", "yield"}
MATERIAL_GID_COLUMN = "gid"
NULL_FILTER_VALUE = "(Nulo)"
DEFAULT_FILTER_VALUES = {
    "plot_is_discarded": ["False"],
    "missing_dev_file": ["no"],
}

MATERIAL_FILTER_LABELS = {
    "business_region": "Região comercial",
    "production_name": "Nome de produção",
    "commercial_name": "Nome comercial",
    "category": "Categoria",
    "brand": "Marca",
    "cycle": "Ciclo",
    "days_to_spike": "Dias ao espigamento",
    "days_to_maturity": "Dias à maturidade",
    "Tipo de elemento": "Tipo de elemento",
}

OBSERVATION_FILTERS = [
    ("year", "Ano"),
    ("trial_type", "Tipo de ensaio"),
    ("signed_status", "Status"),
    ("plot_is_discarded", "Parcela descartada"),
    ("missing_dev_file", "Missing no arquivo DEV"),
    ("country_name", "País"),
    ("macroregion_name", "Macrorregião"),
    ("microregion_name", "Microrregião"),
    ("state_name", "Estado"),
    ("location_name", "Local"),
    ("germplasm_name", "Germoplasma"),
    ("gid", "GID"),
]

px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = [GDM_LIME, GDM_NAVY, "#6F7C80", "#DCE7EA", GDM_CORAL]

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap');

:root {
    --gdm-navy: #09243B;
    --gdm-lime: #B5BE04;
    --gdm-gray: #54595F;
    --gdm-bg: #F5F7F2;
    --gdm-line: #DDE4DF;
    --gdm-white: #FFFFFF;
}

html, body, [class*="css"] {
    font-family: "Montserrat", "Segoe UI", sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at 92% 0%, rgba(181, 190, 4, .10), transparent 24rem),
        var(--gdm-bg);
    color: var(--gdm-navy);
}

[data-testid="stHeader"] {
    background: rgba(245, 247, 242, .86);
    backdrop-filter: blur(12px);
}

.block-container {
    max-width: 1480px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(165deg, #09243B 0%, #0D304E 72%, #143E58 100%);
    border-right: 1px solid rgba(255,255,255,.08);
}

section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding: .4rem .55rem 1.5rem;
}

section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #FFFFFF;
}

.sidebar-brand {
    padding: 1rem .85rem 1.15rem;
    margin-bottom: .8rem;
    border-bottom: 1px solid rgba(255,255,255,.13);
}

.sidebar-brand__mark {
    color: var(--gdm-lime);
    font-size: 1.5rem;
    font-weight: 700;
    letter-spacing: -.04em;
}

.sidebar-brand__title {
    color: white;
    font-size: .95rem;
    font-weight: 600;
    margin-top: .25rem;
}

.sidebar-brand__meta {
    color: rgba(255,255,255,.60);
    font-size: .70rem;
    letter-spacing: .08em;
    margin-top: .2rem;
    text-transform: uppercase;
}

.sidebar-section {
    padding: .25rem .2rem .65rem;
}

.sidebar-section span {
    color: var(--gdm-lime);
    display: block;
    font-size: .65rem;
    font-weight: 700;
    letter-spacing: .14em;
    text-transform: uppercase;
}

.sidebar-section strong {
    color: #FFFFFF;
    display: block;
    font-size: .86rem;
    margin-top: .18rem;
}

section[data-testid="stSidebar"] div[role="radiogroup"] {
    gap: .32rem;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label {
    background: rgba(255,255,255,.055);
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 11px;
    padding: .58rem .72rem;
    transition: all .18s ease;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
    background: rgba(255,255,255,.10);
    border-color: rgba(181,190,4,.45);
}

section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
    background: var(--gdm-lime);
    border-color: var(--gdm-lime);
    box-shadow: 0 8px 20px rgba(0,0,0,.17);
}

section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {
    color: var(--gdm-navy) !important;
    font-weight: 700;
}

section[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: rgba(255,255,255,.97);
    border: 1px solid rgba(255,255,255,.18);
    border-radius: 10px;
}

section[data-testid="stSidebar"] span[data-baseweb="tag"] {
    background: var(--gdm-lime);
    color: var(--gdm-navy);
}

section[data-testid="stSidebar"] details {
    background: rgba(255,255,255,.045);
    border: 1px solid rgba(255,255,255,.10);
    border-radius: 11px;
}

section[data-testid="stSidebar"] [data-testid="stFileUploader"] {
    background: rgba(255,255,255,.055);
    border: 1px solid rgba(255,255,255,.10);
    border-radius: 12px;
    padding: .55rem;
}

section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
    background: rgba(255,255,255,.96);
    border-color: rgba(181,190,4,.55);
    border-radius: 10px;
}

/* Top navigation */
div[data-testid="stRadio"] {
    background: rgba(255,255,255,.78);
    border: 1px solid var(--gdm-line);
    border-radius: 14px;
    box-shadow: 0 8px 24px rgba(9,36,59,.055);
    margin-bottom: 1rem;
    padding: .35rem;
}

div[data-testid="stRadio"] div[role="radiogroup"] {
    gap: .35rem;
}

div[data-testid="stRadio"] div[role="radiogroup"] label {
    border-radius: 10px;
    color: var(--gdm-gray);
    font-weight: 600;
    min-height: 2.45rem;
    padding: .45rem .85rem;
}

div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
    background: var(--gdm-navy);
    box-shadow: 0 6px 16px rgba(9,36,59,.16);
    color: #FFFFFF;
}

/* Hero */
.gdm-hero {
    align-items: stretch;
    background: linear-gradient(122deg, #09243B 0%, #0B2C47 68%, #16425A 100%);
    border-radius: 22px;
    box-shadow: 0 22px 55px rgba(9,36,59,.16);
    display: grid;
    grid-template-columns: 1fr auto;
    margin-bottom: 1.8rem;
    min-height: 190px;
    overflow: hidden;
    position: relative;
}

.gdm-hero::after {
    background: var(--gdm-lime);
    border-radius: 999px;
    content: "";
    height: 300px;
    opacity: .92;
    position: absolute;
    right: -185px;
    top: -108px;
    width: 300px;
}

.gdm-hero__copy {
    padding: 2rem 2.2rem;
    position: relative;
    z-index: 1;
}

.gdm-eyebrow {
    color: var(--gdm-lime);
    font-size: .68rem;
    font-weight: 700;
    letter-spacing: .16em;
    text-transform: uppercase;
}

.gdm-hero h1 {
    color: white;
    font-size: clamp(1.75rem, 3vw, 2.7rem);
    letter-spacing: -.045em;
    line-height: 1.08;
    margin: .55rem 0 .7rem;
}

.gdm-hero p {
    color: rgba(255,255,255,.68);
    font-size: .9rem;
    line-height: 1.65;
    margin: 0;
    max-width: 680px;
}

.gdm-hero__badge {
    align-items: center;
    display: flex;
    padding: 1.6rem 2.5rem 1.6rem 1rem;
    position: relative;
    z-index: 2;
}

.gdm-hero__badge span {
    background: rgba(255,255,255,.11);
    border: 1px solid rgba(255,255,255,.18);
    border-radius: 999px;
    color: white;
    font-size: .68rem;
    font-weight: 600;
    letter-spacing: .07em;
    padding: .62rem .9rem;
    text-transform: uppercase;
    white-space: nowrap;
}

/* Page titles and cards */
.page-intro {
    margin: .3rem 0 1.1rem;
}

.page-intro__kicker {
    color: var(--gdm-lime);
    font-size: .65rem;
    font-weight: 700;
    letter-spacing: .15em;
    text-transform: uppercase;
}

.page-intro h2 {
    color: var(--gdm-navy);
    font-size: 1.65rem;
    letter-spacing: -.035em;
    margin: .25rem 0 .3rem;
}

.page-intro p {
    color: var(--gdm-gray);
    font-size: .86rem;
    margin: 0;
}

.metric-card {
    background: #FFFFFF;
    border: 1px solid var(--gdm-line);
    border-radius: 16px;
    box-shadow: 0 10px 28px rgba(9,36,59,.06);
    min-height: 124px;
    padding: 1.15rem 1.2rem;
    position: relative;
    transition: transform .18s ease, box-shadow .18s ease;
}

.metric-card:hover {
    box-shadow: 0 16px 34px rgba(9,36,59,.10);
    transform: translateY(-2px);
}

.metric-card::before {
    background: var(--gdm-lime);
    border-radius: 0 16px 0 12px;
    content: "";
    height: 7px;
    position: absolute;
    right: 0;
    top: 0;
    width: 42px;
}

.metric-card__top {
    align-items: center;
    display: flex;
    justify-content: space-between;
}

.metric-card__label {
    color: var(--gdm-gray);
    font-size: .68rem;
    font-weight: 600;
    letter-spacing: .08em;
    text-transform: uppercase;
}

.metric-card__icon {
    align-items: center;
    background: rgba(181,190,4,.13);
    border-radius: 9px;
    color: var(--gdm-navy);
    display: flex;
    font-size: .92rem;
    height: 31px;
    justify-content: center;
    width: 31px;
}

.metric-card__value {
    color: var(--gdm-navy);
    font-size: 1.75rem;
    font-weight: 700;
    letter-spacing: -.045em;
    line-height: 1.15;
    margin-top: .55rem;
}

.metric-card__detail {
    color: #7A8589;
    font-size: .68rem;
    margin-top: .18rem;
}

.section-label {
    align-items: center;
    color: var(--gdm-navy);
    display: flex;
    font-size: .78rem;
    font-weight: 700;
    gap: .55rem;
    letter-spacing: .04em;
    margin: 1.65rem 0 .65rem;
    text-transform: uppercase;
}

.section-label::before {
    background: var(--gdm-lime);
    border-radius: 99px;
    content: "";
    height: 8px;
    width: 8px;
}

div[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid var(--gdm-line);
    border-radius: 15px;
    box-shadow: 0 9px 25px rgba(9,36,59,.055);
    padding: 1rem 1.1rem;
}

div[data-testid="stMetricValue"] {
    color: var(--gdm-navy);
    font-weight: 700;
}

div[data-testid="stDataFrame"],
div[data-testid="stPlotlyChart"] {
    background: #FFFFFF;
    border: 1px solid var(--gdm-line);
    border-radius: 16px;
    box-shadow: 0 10px 28px rgba(9,36,59,.05);
    overflow: hidden;
    padding: .45rem;
}

button[data-baseweb="tab"] {
    background: #FFFFFF;
    border: 1px solid var(--gdm-line);
    border-radius: 10px;
    color: var(--gdm-gray);
    font-weight: 600;
    margin-right: .4rem;
    padding: .55rem .9rem;
}

button[data-baseweb="tab"][aria-selected="true"] {
    background: var(--gdm-navy);
    color: #FFFFFF;
}

.stButton > button[kind="primary"],
.stDownloadButton > button {
    background: var(--gdm-lime);
    border: 1px solid var(--gdm-lime);
    border-radius: 11px;
    color: var(--gdm-navy);
    font-weight: 700;
    min-height: 2.65rem;
}

.stButton > button[kind="primary"]:hover,
.stDownloadButton > button:hover {
    background: #C4CD13;
    border-color: #C4CD13;
    color: var(--gdm-navy);
}

[data-testid="stAlert"] {
    border-radius: 13px;
}

@media (max-width: 850px) {
    .gdm-hero { grid-template-columns: 1fr; }
    .gdm-hero__badge { display: none; }
    .gdm-hero__copy { padding: 1.55rem; }
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sample data generator (realistic wheat phenotypic trials)
# ---------------------------------------------------------------------------
@st.cache_data
def generate_sample_data(n_plots=6000, seed=42):
    rng = np.random.default_rng(seed)
    years = [23, 24, 25]
    trial_types = ["VCU", "DHE", "AE", "PRE"]
    locations = {
        "Passo Fundo": ("RS", "Sul", "MR1", 687),
        "Londrina": ("PR", "Sul", "MR2", 610),
        "Cascavel": ("PR", "Sul", "MR2", 781),
        "Dourados": ("MS", "Centro-Oeste", "MR3", 430),
        "Cruz Alta": ("RS", "Sul", "MR1", 452),
        "Guarapuava": ("PR", "Sul", "MR4", 1098),
        "Campo Mourao": ("PR", "Sul", "MR2", 585),
        "Palotina": ("PR", "Sul", "MR2", 330),
    }
    genotypes = [f"GDM-{i:03d}" for i in range(1, 41)]
    checks = ["TBIO Toruk", "TBIO Sonic", "BRS 264", "ORS Vintecinco", "Quartzo"]
    all_germ = genotypes + checks
    germplasm_ids = {germ: f"G{i + 1000}" for i, germ in enumerate(all_germ)}
    companies = ["GDM Seeds", "Biotrigo", "OR Sementes"]
    signed_opts = ["OK", "NOT-OK", "NOT-SIGNED"]
    pipelines = ["Pipeline A", "Pipeline B", "Pipeline C"]
    conditions = ["Irrigado", "Sequeiro"]
    # Build rows
    rows = []
    trial_counter = 0
    for yr in years:
        for loc_name, (state, macro, micro, alt) in locations.items():
            for tt in rng.choice(trial_types, size=rng.integers(1, 3), replace=False):
                trial_counter += 1
                trial_name = f"{tt}_{loc_name[:3].upper()}_{yr}_{trial_counter}"
                n_reps = rng.choice([2, 3, 4])
                subset = list(rng.choice(all_germ, size=rng.integers(15, 30), replace=False))
                cond = rng.choice(conditions)
                pipe = rng.choice(pipelines)
                comp = rng.choice(companies)
                signed = rng.choice(signed_opts, p=[0.6, 0.15, 0.25])
                # Genotype effects
                geno_eff = {g: rng.normal(0, 300) for g in subset}
                loc_eff = rng.normal(0, 200)
                yr_eff = (yr - 24) * 50
                for rep in range(1, n_reps + 1):
                    for germ in subset:
                        base_yield = 3500 + yr_eff + loc_eff + geno_eff[germ]
                        rows.append({
                            "data_source": "cornerstone",
                            "year": yr,
                            "trial_name": trial_name,
                            "trial_type": tt,
                            "trial_number": trial_counter,
                            "pipeline_file": pipe,
                            "condition_file": cond,
                            "signed_status": signed,
                            "plot_is_discarded": bool(
                                rng.choice([False, True], p=[0.97, 0.03])
                            ),
                            "missing_dev_file": rng.choice(
                                ["no", "yes", None], p=[0.75, 0.08, 0.17]
                            ),
                            "location_name": loc_name,
                            "state_name": state,
                            "country_name": "Brasil",
                            "macroregion_name": macro,
                            "microregion_name": micro,
                            "altitude": alt + rng.normal(0, 5),
                            "num_repetitions": rep,
                            "germplasm_name": germ,
                            "gid": germplasm_ids[germ],
                            "company_name": comp,
                            "area": "Trigo",
                            "yield": round(max(800, base_yield + rng.normal(0, 350)), 2),
                            "protein": round(rng.normal(12.5, 1.5), 2),
                            "hectoliter_weight": round(rng.normal(78, 3), 2),
                            "thousand_seeds_weight": round(rng.normal(35, 5), 2),
                            "head_blast": int(rng.choice([0, 1, 2, 3, 5], p=[0.4, 0.25, 0.2, 0.1, 0.05])),
                            "yellow_rust": str(rng.choice([0, 1, 3, 5, 7], p=[0.3, 0.3, 0.2, 0.15, 0.05])),
                            "leaf_rust": str(rng.choice([0, 1, 3, 5, 7], p=[0.35, 0.3, 0.2, 0.1, 0.05])),
                            "fusarium_head_blight": str(rng.choice([0, 1, 3, 5], p=[0.4, 0.3, 0.2, 0.1])),
                            "lodging": str(rng.choice([0, 1, 3, 5], p=[0.5, 0.25, 0.15, 0.1])),
                        })
    return pd.DataFrame(rows)

SAMPLE_DATA = generate_sample_data()
SAMPLE_MATERIALS = (
    SAMPLE_DATA[["gid", "germplasm_name", "company_name"]]
    .drop_duplicates("gid")
    .rename(
        columns={
            "germplasm_name": "commercial_name",
            "company_name": "brand",
        }
    )
    .assign(
        business_region="Brasil",
        category=lambda frame: np.where(
            frame["commercial_name"].str.startswith("GDM-"),
            "EXPERIMENTAL",
            "CHECK",
        ),
        cycle="Não informado",
        **{"Tipo de elemento": "Item"},
    )
)

CATEGORICAL_COLS = [
    "data_source", "trial_type", "trial_name", "pipeline_file",
    "condition_file", "signed_status", "location_name",
    "state_name", "country_name", "macroregion_name", "microregion_name",
    "germplasm_name", "gid", "company_name", "area",
    "plot_is_discarded", "missing_dev_file",
]


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def read_uploaded_excel(file_bytes: bytes):
    """Read observations from sheet 1 and, when present, materials from sheet 2."""
    workbook = pd.ExcelFile(BytesIO(file_bytes), engine="openpyxl")
    df = pd.read_excel(workbook, sheet_name=0)
    df.columns = [str(column).strip() for column in df.columns]
    df = df.dropna(how="all").reset_index(drop=True)

    missing = sorted(REQUIRED_UPLOAD_COLUMNS.difference(df.columns))
    if missing:
        raise ValueError(
            "Colunas obrigatórias ausentes: " + ", ".join(missing)
        )

    original_yield = df["yield"].copy()
    df["yield"] = pd.to_numeric(original_yield, errors="coerce")
    invalid_yield = int(original_yield.notna().sum() - df["yield"].notna().sum())
    if df.empty:
        raise ValueError("A primeira aba do arquivo não contém registros.")
    if df["yield"].notna().sum() == 0:
        raise ValueError("A coluna yield não contém valores numéricos válidos.")

    materials = None
    material_sheet_name = None
    if len(workbook.sheet_names) > 1:
        material_sheet_name = workbook.sheet_names[1]
        materials = pd.read_excel(workbook, sheet_name=1)
        materials.columns = [str(column).strip() for column in materials.columns]
        materials = materials.dropna(how="all").reset_index(drop=True)
        if MATERIAL_GID_COLUMN not in materials.columns:
            raise ValueError(
                f"A segunda aba ({material_sheet_name}) precisa conter a coluna gid."
            )
        if MATERIAL_GID_COLUMN not in df.columns:
            raise ValueError(
                "A primeira aba precisa conter a coluna gid para vincular os materiais."
            )
        materials[MATERIAL_GID_COLUMN] = normalize_gid_series(
            materials[MATERIAL_GID_COLUMN]
        )
        materials = materials.dropna(subset=[MATERIAL_GID_COLUMN])
        materials = materials.drop_duplicates(MATERIAL_GID_COLUMN).reset_index(drop=True)
        df[MATERIAL_GID_COLUMN] = normalize_gid_series(df[MATERIAL_GID_COLUMN])

    return df, invalid_yield, materials, material_sheet_name


def normalize_gid_value(value):
    """Normalize numeric and textual GIDs to the same stable string representation."""
    if pd.isna(value):
        return None
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)) and float(value).is_integer():
        return str(int(value))
    normalized = str(value).strip()
    return normalized or None


def normalize_gid_series(series: pd.Series) -> pd.Series:
    return series.map(normalize_gid_value)


def filter_options(data: pd.DataFrame, column: str):
    """Return string options for a filter, including an explicit null choice."""
    if column not in data.columns:
        return []
    options = sorted(
        data[column].dropna().astype(str).unique().tolist(),
        key=str.casefold,
    )
    if data[column].isna().any():
        options.append(NULL_FILTER_VALUE)
    return options


def apply_column_filter(data: pd.DataFrame, column: str, selected):
    """Apply one cascading filter while preserving explicit null selections."""
    if not selected or column not in data.columns:
        return data
    non_null_values = [value for value in selected if value != NULL_FILTER_VALUE]
    mask = data[column].astype(str).isin(non_null_values)
    if NULL_FILTER_VALUE in selected:
        mask = mask | data[column].isna()
    return data.loc[mask]


def filter_state_key(column: str, source_id: str, prefix="cascade") -> str:
    return f"{prefix}_{column}_{source_id}"


def cascading_multiselect(
    container,
    data,
    column,
    label,
    source_id,
    defaults=None,
    key_prefix="cascade",
):
    """Render one filter and return the dataset available to the next filter."""
    if column not in data.columns:
        return data, []

    options = filter_options(data, column)
    key = filter_state_key(column, source_id, key_prefix)
    if key in st.session_state:
        valid_selection = [
            value for value in st.session_state[key] if value in options
        ]
        if valid_selection != st.session_state[key]:
            st.session_state[key] = valid_selection
    else:
        requested_defaults = defaults or []
        resolved_defaults = []
        for requested in requested_defaults:
            match = next(
                (
                    option for option in options
                    if option.casefold() == str(requested).casefold()
                ),
                None,
            )
            if match is not None:
                resolved_defaults.append(match)
        st.session_state[key] = resolved_defaults

    selected = container.multiselect(label, options, key=key)
    return apply_column_filter(data, column, selected), selected


def material_display_labels(materials: pd.DataFrame) -> dict:
    """Build concise, unique labels while retaining GID as the stored value."""
    labels = {}
    for _, row in materials.iterrows():
        gid = normalize_gid_value(row.get(MATERIAL_GID_COLUMN))
        if gid is None:
            continue
        name = next(
            (
                str(row.get(column)).strip()
                for column in ["commercial_name", "production_name", "germplasm_name"]
                if pd.notna(row.get(column)) and str(row.get(column)).strip()
            ),
            gid,
        )
        category = row.get("category")
        parts = [name, f"GID {gid}"]
        if pd.notna(category) and str(category).strip():
            parts.append(str(category).strip())
        labels[gid] = " · ".join(parts)
    return labels


def scenario_payload(source_id, material_columns, observation_columns):
    """Serialize current filters without any uploaded data or credentials."""
    material_filters = {
        column: st.session_state.get(
            filter_state_key(column, source_id, "material"), []
        )
        for column in material_columns
    }
    observation_filters = {
        column: st.session_state.get(filter_state_key(column, source_id), [])
        for column in observation_columns
    }
    return {
        "app": "gdm-wheat-analysis",
        "version": 1,
        "saved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_fingerprint": source_id,
        "filters": {
            "material_attributes": material_filters,
            "selected_gids": st.session_state.get(
                filter_state_key("selected_gids", source_id, "material"), []
            ),
            "observations": observation_filters,
        },
    }


def load_scenario_into_state(payload, source_id):
    """Load a versioned scenario into widget state before filters are rendered."""
    if payload.get("app") != "gdm-wheat-analysis":
        raise ValueError("Este JSON não é um cenário do GDM Wheat Analysis.")
    if payload.get("version") != 1:
        raise ValueError("Versão de cenário não suportada.")

    filters = payload.get("filters")
    if not isinstance(filters, dict):
        raise ValueError("O cenário não contém a seção filters.")

    material_filters = filters.get("material_attributes", {})
    observation_filters = filters.get("observations", {})
    selected_gids = filters.get("selected_gids", [])
    if not isinstance(material_filters, dict) or not isinstance(observation_filters, dict):
        raise ValueError("Os filtros do cenário têm formato inválido.")
    if not isinstance(selected_gids, list):
        raise ValueError("selected_gids precisa ser uma lista.")

    for column, values in material_filters.items():
        if isinstance(values, list):
            st.session_state[filter_state_key(column, source_id, "material")] = values
    for column, values in observation_filters.items():
        if isinstance(values, list):
            st.session_state[filter_state_key(column, source_id)] = values
    st.session_state[
        filter_state_key("selected_gids", source_id, "material")
    ] = [normalize_gid_value(value) for value in selected_gids]


def format_integer(value) -> str:
    """Format dashboard counts using Brazilian thousands separators."""
    if isinstance(value, (int, np.integer)):
        return f"{int(value):,}".replace(",", ".")
    return str(value)


def format_decimal(value, decimals=1) -> str:
    """Format decimal values with Brazilian thousands and decimal separators."""
    if pd.isna(value):
        return "-"
    formatted = f"{float(value):,.{decimals}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def render_metric(container, icon: str, label: str, value, detail: str):
    safe_icon = html.escape(str(icon))
    safe_label = html.escape(str(label))
    safe_value = html.escape(format_integer(value))
    safe_detail = html.escape(str(detail))
    container.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-card__top">
                <span class="metric-card__label">{safe_label}</span>
                <span class="metric-card__icon">{safe_icon}</span>
            </div>
            <div class="metric-card__value">{safe_value}</div>
            <div class="metric-card__detail">{safe_detail}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_intro(kicker: str, title: str, description: str):
    st.markdown(
        f"""
        <div class="page-intro">
            <div class="page-intro__kicker">{kicker}</div>
            <h2>{title}</h2>
            <p>{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_label(text: str):
    st.markdown(f'<div class="section-label">{text}</div>', unsafe_allow_html=True)


def show_plot(fig):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FFFFFF",
        font=dict(family="Montserrat, Segoe UI, sans-serif", color=GDM_NAVY),
        title=dict(font=dict(size=16, color=GDM_NAVY)),
        margin=dict(l=24, r=24, t=58, b=28),
        legend_title_text="",
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


# ---------------------------------------------------------------------------
# Sidebar: navigation + filters
# ---------------------------------------------------------------------------
st.sidebar.markdown(
    """
    <div class="sidebar-brand">
        <div class="sidebar-brand__mark">GDM</div>
        <div class="sidebar-brand__title">Wheat Phenotypic Analysis</div>
        <div class="sidebar-brand__meta">Genética · Dados · Decisão</div>
    </div>
    """,
    unsafe_allow_html=True,
)

nav_labels = {
    "Dados": "▦  Visão geral",
    "Índice Ambiental": "⇄  Índice ambiental",
    "Modelo Misto": "◈  Modelo misto",
    "Resultados": "↗  Resultados",
    "Diagnosticos": "⌁  Diagnósticos",
}

st.sidebar.markdown(
    """
    <div class="sidebar-section">
        <span>Fonte de dados</span>
        <strong>Importar planilha</strong>
    </div>
    """,
    unsafe_allow_html=True,
)

uploaded_file = st.sidebar.file_uploader(
    "Arquivo Excel",
    type=["xlsx"],
    help="A primeira aba contém as observações. Se houver uma segunda aba, ela será usada como cadastro de materiais ligado pela coluna gid.",
)

if TEMPLATE_PATH.exists():
    st.sidebar.download_button(
        "Baixar template Excel",
        data=TEMPLATE_PATH.read_bytes(),
        file_name="template_dados_fenotipicos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )

active_data = SAMPLE_DATA.copy()
active_materials = SAMPLE_MATERIALS.copy()
source_id = "demonstrative-data"
source_badge = "● Dados demonstrativos"
material_sheet_name = "Materiais demonstrativos"

if uploaded_file is not None:
    try:
        uploaded_bytes = uploaded_file.getvalue()
        (
            active_data,
            invalid_yield_count,
            uploaded_materials,
            material_sheet_name,
        ) = read_uploaded_excel(uploaded_bytes)
        source_id = hashlib.sha256(uploaded_bytes).hexdigest()[:12]
        source_badge = "● Arquivo importado"
        if uploaded_materials is not None:
            active_materials = uploaded_materials
        elif "gid" in active_data.columns:
            fallback_columns = [
                column for column in ["gid", "germplasm_name", "company_name"]
                if column in active_data.columns
            ]
            active_materials = active_data[fallback_columns].drop_duplicates("gid")
            material_sheet_name = None
        st.sidebar.success(
            f"{uploaded_file.name}: {len(active_data):,} linhas".replace(",", ".")
        )
        if invalid_yield_count:
            st.sidebar.warning(
                f"{invalid_yield_count} valor(es) de yield não numérico(s) foram tratados como ausentes."
            )
        if uploaded_materials is None:
            st.sidebar.warning(
                "A segunda aba não foi encontrada. O seletor usará apenas os GIDs da primeira aba."
            )
    except Exception as exc:
        st.sidebar.error(f"Não foi possível importar o arquivo: {exc}")

if "gid" in active_data.columns:
    active_data["gid"] = normalize_gid_series(active_data["gid"])
if "gid" in active_materials.columns:
    active_materials["gid"] = normalize_gid_series(active_materials["gid"])
    active_materials = active_materials.dropna(subset=["gid"])
    active_materials = active_materials.drop_duplicates("gid").reset_index(drop=True)

if st.session_state.get("active_source_id") != source_id:
    st.session_state["active_source_id"] = source_id
    st.session_state["df"] = active_data.copy()

st.sidebar.markdown(
    """
    <div class="sidebar-section">
        <span>Cenários</span>
        <strong>Abrir filtros salvos</strong>
    </div>
    """,
    unsafe_allow_html=True,
)

scenario_file = st.sidebar.file_uploader(
    "Arquivo de cenário",
    type=["json"],
    help="Abra um JSON salvo neste app para restaurar os filtros.",
    key="scenario_file_uploader",
)
if scenario_file is not None:
    try:
        scenario_bytes = scenario_file.getvalue()
        scenario_signature = hashlib.sha256(
            scenario_bytes + source_id.encode("utf-8")
        ).hexdigest()
        if st.session_state.get("applied_scenario_signature") != scenario_signature:
            scenario = json.loads(scenario_bytes.decode("utf-8-sig"))
            load_scenario_into_state(scenario, source_id)
            st.session_state["applied_scenario_signature"] = scenario_signature
            st.session_state["scenario_source_mismatch"] = (
                scenario.get("source_fingerprint") not in [None, source_id]
            )
        st.sidebar.success(f"Cenário aberto: {scenario_file.name}")
        if st.session_state.get("scenario_source_mismatch"):
            st.sidebar.info(
                "O cenário foi criado com outra base. Somente valores existentes serão aplicados."
            )
    except Exception as exc:
        st.sidebar.error(f"Não foi possível abrir o cenário: {exc}")
else:
    st.session_state.pop("applied_scenario_signature", None)
    st.session_state.pop("scenario_source_mismatch", None)

st.sidebar.markdown(
    """
    <div class="sidebar-section">
        <span>Etapa 1</span>
        <strong>Selecionar genótipos</strong>
    </div>
    """,
    unsafe_allow_html=True,
)

available_materials = active_materials.copy()
if "gid" in active_data.columns and "gid" in available_materials.columns:
    data_gids = set(active_data["gid"].dropna())
    catalog_size = len(available_materials)
    available_materials = available_materials.loc[
        available_materials["gid"].isin(data_gids)
    ].copy()
    unmatched_materials = catalog_size - len(available_materials)
else:
    unmatched_materials = 0

preferred_material_columns = [
    column for column in MATERIAL_FILTER_LABELS
    if column in available_materials.columns
]
extra_material_columns = [
    column for column in available_materials.columns
    if column not in {"gid", *preferred_material_columns}
    and column not in {"germplasm_name"}
]
material_filter_columns = preferred_material_columns + extra_material_columns

material_filter_panel = st.sidebar.expander("Refinar catálogo de materiais")
filtered_materials = available_materials
for column in material_filter_columns:
    filtered_materials, _ = cascading_multiselect(
        material_filter_panel,
        filtered_materials,
        column,
        MATERIAL_FILTER_LABELS.get(column, column),
        source_id,
        key_prefix="material",
    )

material_labels = material_display_labels(filtered_materials)
material_gid_options = list(material_labels)
selected_gid_key = filter_state_key("selected_gids", source_id, "material")
if selected_gid_key in st.session_state:
    st.session_state[selected_gid_key] = [
        gid for gid in st.session_state[selected_gid_key]
        if gid in material_gid_options
    ]
else:
    st.session_state[selected_gid_key] = []

selected_gids = st.sidebar.multiselect(
    "Genótipos incluídos",
    material_gid_options,
    format_func=lambda gid: material_labels.get(gid, gid),
    key=selected_gid_key,
    help="A lista vem da segunda aba e é ligada às observações pela coluna gid. Vazio inclui todos os materiais disponíveis.",
)
effective_gids = selected_gids or material_gid_options
if material_sheet_name:
    st.sidebar.caption(
        f"{len(effective_gids)} de {len(available_materials)} materiais disponíveis na base."
    )
if unmatched_materials:
    st.sidebar.caption(
        f"{unmatched_materials} material(is) do cadastro não têm observações e foram ocultados."
    )

if "gid" in active_data.columns:
    filtered_data = active_data.loc[active_data["gid"].isin(effective_gids)].copy()
else:
    filtered_data = active_data.copy()

st.sidebar.markdown(
    """
    <div class="sidebar-section">
        <span>Etapa 2</span>
        <strong>Segmentar observações</strong>
    </div>
    """,
    unsafe_allow_html=True,
)

filtered_data, _ = cascading_multiselect(
    st.sidebar, filtered_data, "year", "Ano", source_id
)
filtered_data, _ = cascading_multiselect(
    st.sidebar, filtered_data, "trial_type", "Tipo de ensaio", source_id
)
filtered_data, _ = cascading_multiselect(
    st.sidebar, filtered_data, "signed_status", "Status", source_id
)

st.sidebar.markdown(
    """
    <div class="sidebar-section">
        <span>Qualidade</span>
        <strong>Elegibilidade dos registros</strong>
    </div>
    """,
    unsafe_allow_html=True,
)
filtered_data, _ = cascading_multiselect(
    st.sidebar,
    filtered_data,
    "plot_is_discarded",
    "Parcela descartada",
    source_id,
    DEFAULT_FILTER_VALUES["plot_is_discarded"],
)
filtered_data, _ = cascading_multiselect(
    st.sidebar,
    filtered_data,
    "missing_dev_file",
    "Missing no arquivo DEV",
    source_id,
    DEFAULT_FILTER_VALUES["missing_dev_file"],
)

location_panel = st.sidebar.expander("Localização")
for column, label in [
    ("country_name", "País"),
    ("macroregion_name", "Macrorregião"),
    ("microregion_name", "Microrregião"),
    ("state_name", "Estado"),
    ("location_name", "Local"),
]:
    filtered_data, _ = cascading_multiselect(
        location_panel, filtered_data, column, label, source_id
    )

dedicated_filters = {
    "year", "trial_type", "signed_status", "plot_is_discarded",
    "missing_dev_file", "country_name", "macroregion_name",
    "microregion_name", "state_name", "location_name",
    "germplasm_name", "gid",
}
other_panel = st.sidebar.expander("Outros")
for column in [
    candidate for candidate in CATEGORICAL_COLS
    if candidate not in dedicated_filters and candidate in active_data.columns
]:
    filtered_data, _ = cascading_multiselect(
        other_panel, filtered_data, column, column, source_id
    )

st.session_state["df"] = filtered_data.copy()
st.sidebar.caption(
    f"Datacut ativo: {len(filtered_data):,} de {len(active_data):,} registros".replace(",", ".")
)

observation_filter_columns = [
    column for column, _ in OBSERVATION_FILTERS
    if column not in {"germplasm_name", "gid"} and column in active_data.columns
] + [
    column for column in CATEGORICAL_COLS
    if column not in dedicated_filters and column in active_data.columns
]
scenario = scenario_payload(
    source_id,
    material_filter_columns,
    observation_filter_columns,
)
st.sidebar.download_button(
    "Salvar cenário (JSON)",
    data=json.dumps(scenario, ensure_ascii=False, indent=2).encode("utf-8"),
    file_name="cenario_filtros_gdm.json",
    mime="application/json",
    width="stretch",
    help="Salva apenas os filtros e GIDs selecionados; os dados não são incluídos.",
)

page = st.radio(
    "Navegação",
    list(nav_labels),
    format_func=nav_labels.get,
    horizontal=True,
    label_visibility="collapsed",
    key="top_navigation",
)

st.markdown(
    f"""
    <div class="gdm-hero">
        <div class="gdm-hero__copy">
            <div class="gdm-eyebrow">GDM · Research Analytics</div>
            <h1>Wheat Phenotypic Analysis</h1>
            <p>Explore ensaios, compare germoplasmas e transforme dados fenotípicos em decisões de melhoramento mais claras.</p>
        </div>
        <div class="gdm-hero__badge"><span>{html.escape(source_badge)}</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Page: Dados
# ---------------------------------------------------------------------------
if page == "Dados":
    render_page_intro(
        "Visão geral",
        "Dados fenotípicos · Trigo",
        "Resumo executivo da base ativa após a aplicação dos filtros laterais.",
    )
    df = st.session_state["df"]
    c1, c2, c3, c4 = st.columns(4)
    render_metric(c1, "▤", "Registros", len(df), "parcelas na seleção atual")
    render_metric(c2, "⌗", "Variáveis", len(df.columns), "atributos disponíveis")
    render_metric(
        c3,
        "◫",
        "Ensaios",
        df["trial_name"].nunique() if "trial_name" in df.columns else "-",
        "experimentos únicos",
    )
    render_metric(
        c4,
        "♧",
        "Genótipos",
        df["germplasm_name"].nunique() if "germplasm_name" in df.columns else "-",
        "materiais avaliados",
    )

    if not df.empty and {"yield", "location_name"}.issubset(df.columns):
        section_label("Panorama da seleção")
        chart_left, chart_right = st.columns([1.15, 1], gap="large")
        with chart_left:
            yield_fig = px.histogram(
                df,
                x="yield",
                nbins=32,
                title="Distribuição de produtividade",
                labels={"yield": "Produtividade"},
                color_discrete_sequence=[GDM_LIME],
            )
            show_plot(yield_fig)
        with chart_right:
            location_yield = (
                df.groupby("location_name", as_index=False)["yield"]
                .mean()
                .sort_values("yield", ascending=True)
            )
            location_fig = px.bar(
                location_yield,
                x="yield",
                y="location_name",
                orientation="h",
                title="Produtividade média por local",
                labels={"yield": "Produtividade média", "location_name": ""},
                color_discrete_sequence=[GDM_NAVY],
            )
            show_plot(location_fig)

    section_label("Base filtrada")
    st.dataframe(df, width="stretch", height=500)
    with st.expander("Estatísticas descritivas"):
        num = df.select_dtypes(include=[np.number]).columns.tolist()
        if num:
            st.dataframe(df[num].describe().round(3), width="stretch")
    st.download_button("Download CSV", df.to_csv(index=False), "wheat_data.csv", "text/csv")

# ---------------------------------------------------------------------------
# Page: Environmental index head-to-head
# ---------------------------------------------------------------------------
elif page == "Índice Ambiental":
    render_page_intro(
        "Comparação head-to-head",
        "Índice ambiental de produtividade",
        "Compare dois genótipos nos ambientes em que ambos foram avaliados.",
    )
    df = st.session_state["df"].copy()
    required = {"trial_name", "germplasm_name", "yield"}

    if not required.issubset(df.columns):
        missing = ", ".join(sorted(required.difference(df.columns)))
        st.warning(f"A base filtrada não contém as colunas necessárias: {missing}.")
    else:
        comparison_data = df[list(required)].copy()
        comparison_data["yield"] = pd.to_numeric(comparison_data["yield"], errors="coerce")
        comparison_data = comparison_data.dropna(
            subset=["trial_name", "germplasm_name", "yield"]
        )
        comparison_data["trial_name"] = comparison_data["trial_name"].astype(str)
        comparison_data["germplasm_name"] = comparison_data["germplasm_name"].astype(str)
        genotypes = sorted(comparison_data["germplasm_name"].unique().tolist())

        if len(genotypes) < 2:
            st.warning(
                "O datacut precisa conter pelo menos dois genótipos com produtividade válida."
            )
        else:
            presence = pd.crosstab(
                comparison_data["trial_name"],
                comparison_data["germplasm_name"],
            ).gt(0).astype(int)
            cooccurrence = presence.T.dot(presence)
            np.fill_diagonal(cooccurrence.values, -1)
            default_a_index, default_b_index = np.unravel_index(
                cooccurrence.to_numpy().argmax(),
                cooccurrence.shape,
            )
            default_a = cooccurrence.index[default_a_index]
            default_b = cooccurrence.columns[default_b_index]

            selector_left, selector_right = st.columns(2, gap="large")
            with selector_left:
                genotype_a = st.selectbox(
                    "Genótipo A",
                    genotypes,
                    index=genotypes.index(default_a),
                    key=f"environment_index_a_{source_id}",
                )
            with selector_right:
                genotype_b = st.selectbox(
                    "Genótipo B",
                    genotypes,
                    index=genotypes.index(default_b),
                    key=f"environment_index_b_{source_id}",
                )

            if genotype_a == genotype_b:
                st.info("Selecione dois genótipos diferentes para gerar a comparação.")
            else:
                pair_data = comparison_data[
                    comparison_data["germplasm_name"].isin([genotype_a, genotype_b])
                ]
                pair_means = (
                    pair_data.groupby(["trial_name", "germplasm_name"], as_index=False)["yield"]
                    .mean()
                    .rename(columns={"yield": "genotype_yield"})
                )
                common_trials = (
                    pair_means.groupby("trial_name")["germplasm_name"]
                    .nunique()
                    .loc[lambda values: values == 2]
                    .index
                )

                if len(common_trials) == 0:
                    st.warning(
                        "Os genótipos selecionados não aparecem juntos em nenhum trial_name do datacut."
                    )
                else:
                    environmental_mean = (
                        comparison_data[
                            comparison_data["trial_name"].isin(common_trials)
                        ]
                        .groupby("trial_name", as_index=False)["yield"]
                        .mean()
                        .rename(columns={"yield": "environmental_mean"})
                    )
                    plot_data = pair_means[
                        pair_means["trial_name"].isin(common_trials)
                    ].merge(environmental_mean, on="trial_name", how="inner")

                    mean_a = plot_data.loc[
                        plot_data["germplasm_name"] == genotype_a, "genotype_yield"
                    ].mean()
                    mean_b = plot_data.loc[
                        plot_data["germplasm_name"] == genotype_b, "genotype_yield"
                    ].mean()

                    m1, m2, m3, m4 = st.columns(4)
                    render_metric(m1, "◫", "Ambientes comuns", len(common_trials), "trial_name com ambos")
                    render_metric(m2, "A", "Média genótipo A", format_decimal(mean_a), genotype_a)
                    render_metric(m3, "B", "Média genótipo B", format_decimal(mean_b), genotype_b)
                    render_metric(
                        m4,
                        "Δ",
                        "Diferença A − B",
                        format_decimal(mean_a - mean_b),
                        "média nos ambientes comuns",
                    )

                    st.info(
                        "A média ambiental no eixo X usa todos os genótipos disponíveis em cada "
                        "trial_name após os filtros. O eixo Y mostra a produtividade média de cada "
                        "genótipo selecionado no mesmo ambiente."
                    )
                    section_label("Desempenho por ambiente")

                    colors = {genotype_a: GDM_LIME, genotype_b: GDM_NAVY}
                    fig = go.Figure()
                    for genotype in [genotype_a, genotype_b]:
                        genotype_data = plot_data[
                            plot_data["germplasm_name"] == genotype
                        ].sort_values("environmental_mean")
                        fig.add_trace(
                            go.Scatter(
                                x=genotype_data["environmental_mean"],
                                y=genotype_data["genotype_yield"],
                                mode="markers",
                                name=genotype,
                                customdata=genotype_data[["trial_name"]],
                                marker=dict(
                                    color=colors[genotype],
                                    size=11,
                                    line=dict(color="#FFFFFF", width=1.5),
                                ),
                                hovertemplate=(
                                    "<b>%{customdata[0]}</b><br>"
                                    "Média ambiental: %{x:,.1f}<br>"
                                    "Produtividade do genótipo: %{y:,.1f}<extra></extra>"
                                ),
                            )
                        )
                        if (
                            len(genotype_data) >= 2
                            and genotype_data["environmental_mean"].nunique() >= 2
                        ):
                            slope, intercept = np.polyfit(
                                genotype_data["environmental_mean"],
                                genotype_data["genotype_yield"],
                                1,
                            )
                            x_line = np.array([
                                genotype_data["environmental_mean"].min(),
                                genotype_data["environmental_mean"].max(),
                            ])
                            fig.add_trace(
                                go.Scatter(
                                    x=x_line,
                                    y=intercept + slope * x_line,
                                    mode="lines",
                                    line=dict(color=colors[genotype], width=2.5),
                                    hoverinfo="skip",
                                    showlegend=False,
                                )
                            )

                    axis_min = min(
                        plot_data["environmental_mean"].min(),
                        plot_data["genotype_yield"].min(),
                    )
                    axis_max = max(
                        plot_data["environmental_mean"].max(),
                        plot_data["genotype_yield"].max(),
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=[axis_min, axis_max],
                            y=[axis_min, axis_max],
                            mode="lines",
                            line=dict(color="#AAB3B6", width=1.5, dash="dot"),
                            name="Igual à média ambiental",
                            hoverinfo="skip",
                        )
                    )
                    fig.update_layout(
                        title="Produtividade dos genótipos × média ambiental",
                        xaxis_title="Média ambiental por trial_name",
                        yaxis_title="Produtividade média do genótipo",
                        hovermode="closest",
                    )
                    show_plot(fig)

                    section_label("Detalhamento dos ambientes comuns")
                    comparison_table = (
                        plot_data.pivot(
                            index=["trial_name", "environmental_mean"],
                            columns="germplasm_name",
                            values="genotype_yield",
                        )
                        .reset_index()
                        .rename_axis(None, axis=1)
                    )
                    comparison_table[f"Diferença · {genotype_a} − {genotype_b}"] = (
                        comparison_table[genotype_a] - comparison_table[genotype_b]
                    )
                    comparison_table = comparison_table.sort_values("environmental_mean")
                    st.dataframe(
                        comparison_table,
                        width="stretch",
                        hide_index=True,
                        column_config={
                            "environmental_mean": st.column_config.NumberColumn(
                                "Média ambiental", format="%.1f"
                            ),
                            genotype_a: st.column_config.NumberColumn(genotype_a, format="%.1f"),
                            genotype_b: st.column_config.NumberColumn(genotype_b, format="%.1f"),
                        },
                    )
                    st.download_button(
                        "Baixar comparação CSV",
                        comparison_table.to_csv(index=False),
                        "indice_ambiental_head_to_head.csv",
                        "text/csv",
                    )

# ---------------------------------------------------------------------------
# Page: Modelo Misto
# ---------------------------------------------------------------------------
elif page == "Modelo Misto":
    render_page_intro(
        "Modelagem",
        "Especificação do modelo misto",
        "Defina a variável resposta e combine efeitos fixos e aleatórios para o ajuste REML.",
    )
    if "df" not in st.session_state or st.session_state["df"].empty:
        st.warning("Carregue os dados primeiro na aba **Dados**.")
    else:
        df = st.session_state["df"].copy()
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = df.select_dtypes(include=["object", "string", "category"]).columns.tolist()
        all_cols = num_cols + cat_cols

        section_label("Estrutura do modelo")
        response = st.selectbox("Variavel dependente (numerica)", num_cols,
                                index=num_cols.index("yield") if "yield" in num_cols else 0)

        effects_left, effects_right = st.columns(2, gap="large")
        with effects_left:
            st.subheader("Efeitos fixos")
            fixed = st.multiselect(
                "Selecione efeitos fixos",
                [c for c in all_cols if c != response],
                help="Variáveis categóricas são tratadas como fatores (C()).",
            )
        with effects_right:
            st.subheader("Efeitos aleatórios")
            random_eff = st.multiselect(
                "Selecione efeitos aleatórios",
                [c for c in cat_cols if c != response and c not in fixed],
                help="O primeiro será o agrupamento principal. Ex.: germplasm_name, trial_name",
            )

        # Preview
        if response and fixed and random_eff:
            fx = " + ".join(f"C({f})" if f in cat_cols else f for f in fixed)
            st.code(f"{response} ~ {fx}  |  random: {', '.join(random_eff)}", language="r")

        # Warn large cardinality
        for re in random_eff:
            n_levels = df[re].nunique()
            if n_levels > 2000:
                st.warning(f"{re} tem {n_levels:,} niveis - pode ser lento.")

        if st.button("Ajustar Modelo", type="primary", width="stretch"):
            if not fixed:
                st.error("Selecione ao menos um efeito fixo.")
            elif not random_eff:
                st.error("Selecione ao menos um efeito aleatorio.")
            else:
                with st.spinner("Ajustando modelo misto (REML)..."):
                    try:
                        keep = [response] + fixed + random_eff
                        dm = df[keep].dropna(subset=[response]).copy()
                        dm[response] = pd.to_numeric(dm[response], errors="coerce")
                        dm = dm.dropna(subset=[response])
                        if len(dm) < 20:
                            st.error(f"Apenas {len(dm)} obs apos remover NAs. Minimo 20.")
                        else:
                            # Build formula
                            # Patsy, usado pelo statsmodels, exige Q() para nomes que também
                            # são palavras reservadas do Python, como a coluna "yield".
                            terms = [f'C(Q("{f}"))' if f in cat_cols else f'Q("{f}")' for f in fixed]
                            formula = f'Q("{response}") ~ {" + ".join(terms)}'
                            primary_re = random_eff[0]
                            vc = {}
                            for rv in random_eff[1:]:
                                vc[rv] = f'0 + C(Q("{rv}"))'
                            model = smf.mixedlm(
                                formula, dm,
                                groups=dm[primary_re],
                                vc_formula=vc if vc else None,
                            )
                            res = model.fit(reml=True)
                            st.session_state["mres"] = res
                            st.session_state["mdata"] = dm
                            st.session_state["mresp"] = response
                            st.session_state["mprimary"] = primary_re
                            st.session_state["mrandom"] = random_eff
                            st.success("Modelo ajustado! Va para **Resultados** e **Diagnosticos**.")
                    except Exception as exc:
                        st.error(f"Erro: {exc}")

# ---------------------------------------------------------------------------
# Page: Resultados
# ---------------------------------------------------------------------------
elif page == "Resultados":
    render_page_intro(
        "Pós-análise",
        "Resultados do modelo misto",
        "Componentes de variância, BLUPs, herdabilidade e ranking em uma única leitura.",
    )
    if "mres" not in st.session_state:
        st.warning("Ajuste um modelo primeiro.")
    else:
        res = st.session_state["mres"]
        dm = st.session_state["mdata"]
        resp = st.session_state["mresp"]
        primary = st.session_state["mprimary"]
        randoms = st.session_state["mrandom"]

        t1, t2, t3, t4, t5 = st.tabs(
            ["▤ Resumo", "◔ Variância", "◈ BLUPs", "◎ Herdabilidade", "↗ Ranking"]
        )

        # --- Resumo ---
        with t1:
            st.subheader("Resumo")
            st.text(str(res.summary()))
            c1, c2, c3 = st.columns(3)
            aic = -2 * res.llf + 2 * len(res.params)
            c1.metric("Log-Likelihood", f"{res.llf:.2f}")
            c2.metric("AIC", f"{aic:.2f}")
            c3.metric("Observacoes", f"{int(res.nobs):,}")

        # --- Variancia ---
        with t2:
            st.subheader("Componentes de Variancia")
            var_rows = []
            # primary RE
            gv = float(res.cov_re.iloc[0, 0]) if hasattr(res.cov_re, "iloc") else float(res.cov_re)
            var_rows.append({"Componente": f"{primary} (grupo)", "Variancia": gv})
            # additional VC
            if hasattr(res, "vcomp") and res.vcomp is not None:
                extra = randoms[1:]
                for i, vc_val in enumerate(res.vcomp):
                    nm = extra[i] if i < len(extra) else f"VC_{i}"
                    var_rows.append({"Componente": nm, "Variancia": float(vc_val)})
            # residual
            rv = float(res.scale)
            var_rows.append({"Componente": "Residual", "Variancia": rv})
            vdf = pd.DataFrame(var_rows)
            vdf["DP"] = np.sqrt(vdf["Variancia"].clip(lower=0))
            total = vdf["Variancia"].sum()
            vdf["%Total"] = (vdf["Variancia"] / total * 100).round(2)
            st.dataframe(vdf, width="stretch", hide_index=True)
            fig = px.pie(
                vdf,
                values="Variancia",
                names="Componente",
                title="Proporção dos componentes de variância",
                hole=.48,
            )
            show_plot(fig)

        # --- BLUPs ---
        with t3:
            st.subheader(f"BLUPs - {primary}")
            blups = []
            intercept = float(res.fe_params.get("Intercept", 0))
            for grp, eff in res.random_effects.items():
                val = float(eff.iloc[0]) if hasattr(eff, "iloc") else float(eff)
                blups.append({primary: grp, "BLUP": val, "Predito": intercept + val})
            bdf = pd.DataFrame(blups).sort_values("BLUP", ascending=False).reset_index(drop=True)
            bdf.index += 1
            bdf.index.name = "Rank"
            st.dataframe(bdf, width="stretch", height=400)
            fig = px.histogram(
                bdf,
                x="BLUP",
                nbins=30,
                title=f"Distribuição dos BLUPs · ({primary})",
                color_discrete_sequence=[GDM_LIME],
            )
            show_plot(fig)
            st.download_button("Download BLUPs", bdf.to_csv(), "blups.csv", "text/csv")

        # --- Herdabilidade ---
        with t4:
            st.subheader("Herdabilidade")
            Vg = gv
            Ve = rv
            avg_r = dm.groupby(primary).size().mean() if primary in dm.columns else 1
            H2 = Vg / (Vg + Ve) if (Vg + Ve) > 0 else 0
            H2m = Vg / (Vg + Ve / avg_r) if (Vg + Ve / avg_r) > 0 else 0
            c1, c2, c3 = st.columns(3)
            c1.metric("H2 (ampla)", f"{H2:.4f}")
            c2.metric("H2 (media)", f"{H2m:.4f}")
            c3.metric("Reps medias", f"{avg_r:.1f}")
            st.markdown(f"""
            **Formulas:**
            - H2 ampla = Vg / (Vg + Ve) = {Vg:.4f} / ({Vg:.4f} + {Ve:.4f}) = **{H2:.4f}**
            - H2 media = Vg / (Vg + Ve/r) = {Vg:.4f} / ({Vg:.4f} + {Ve:.4f}/{avg_r:.1f}) = **{H2m:.4f}**
            """)

        # --- Ranking ---
        with t5:
            st.subheader(f"Ranking ({resp})")
            max_top = max(1, min(200, len(bdf)))
            ntop = st.slider("Top N", 1, max_top, min(20, max_top))
            top = bdf.head(ntop).copy()
            fig = px.bar(top, x=primary, y="Predito",
                         title=f"Top {ntop} · Valor predito ({resp})",
                         color="BLUP", color_continuous_scale=GDM_SCALE)
            fig.update_layout(xaxis_tickangle=-45, height=600)
            show_plot(fig)

# ---------------------------------------------------------------------------
# Page: Diagnosticos
# ---------------------------------------------------------------------------
elif page == "Diagnosticos":
    render_page_intro(
        "Qualidade do ajuste",
        "Diagnósticos do modelo",
        "Inspecione resíduos, normalidade e incerteza dos efeitos fixos antes de interpretar o ranking.",
    )
    if "mres" not in st.session_state:
        st.warning("Ajuste um modelo primeiro.")
    else:
        res = st.session_state["mres"]
        residuals = res.resid
        fitted = res.fittedvalues

        dt1, dt2, dt3 = st.tabs(["⌁ Resíduos", "◈ Wald Test", "↗ Efeitos fixos"])

        with dt1:
            c1, c2 = st.columns(2)
            with c1:
                fig = px.scatter(x=fitted, y=residuals, opacity=0.4,
                                 labels={"x": "Ajustados", "y": "Residuos"},
                                 title="Residuos vs Ajustados")
                fig.add_hline(y=0, line_dash="dash", line_color=GDM_CORAL)
                show_plot(fig)
            with c2:
                sr = np.sort(residuals)
                n = len(sr)
                tq = stats.norm.ppf(np.arange(1, n + 1) / (n + 1))
                fig = px.scatter(x=tq, y=sr,
                                 labels={"x": "Quantis Teoricos", "y": "Quantis Amostrais"},
                                 title="QQ Plot")
                mn, mx = min(tq.min(), sr.min()), max(tq.max(), sr.max())
                fig.add_trace(go.Scatter(x=[mn, mx], y=[mn, mx],
                              mode="lines", line=dict(color=GDM_CORAL, dash="dash"),
                              showlegend=False))
                show_plot(fig)

            c3, c4 = st.columns(2)
            with c3:
                fig = px.histogram(x=residuals, nbins=40, title="Histograma Residuos",
                                   labels={"x": "Residuos"},
                                   color_discrete_sequence=[GDM_LIME])
                show_plot(fig)
            with c4:
                fig = px.scatter(x=fitted, y=np.sqrt(np.abs(residuals)), opacity=0.4,
                                 labels={"x": "Ajustados", "y": "sqrt|Residuos|"},
                                 title="Scale-Location")
                show_plot(fig)

            st.subheader("Testes de Normalidade")
            nr = len(residuals)
            if nr <= 5000:
                sw, sp = stats.shapiro(residuals)
                st.markdown(f"**Shapiro-Wilk:** W={sw:.4f}, p={sp:.2e}")
            else:
                st.info(f"Shapiro-Wilk nao aplicavel (n={nr:,} > 5000).")
            ks, kp = stats.kstest(residuals, "norm",
                                  args=(residuals.mean(), residuals.std()))
            st.markdown(f"**Kolmogorov-Smirnov:** D={ks:.4f}, p={kp:.2e}")

        with dt2:
            st.subheader("Wald Test - Efeitos Fixos")
            fe = res.fe_params
            try:
                se = res.bse_fe
            except Exception:
                se = res.bse.reindex(fe.index)
            z = fe / se
            pv = 2 * (1 - stats.norm.cdf(np.abs(z)))
            wdf = pd.DataFrame({"Coef": fe, "SE": se, "z": z, "P>|z|": pv})
            wdf["Sig"] = wdf["P>|z|"].apply(
                lambda p: "***" if p < 0.001 else "**" if p < 0.01
                else "*" if p < 0.05 else "ns")
            st.dataframe(wdf.round(4), width="stretch")
            st.caption("*** p<0.001 | ** p<0.01 | * p<0.05 | ns nao significativo")
            st.metric("Log-Likelihood", f"{res.llf:.4f}")
            st.metric("Convergiu", "Sim" if res.converged else "Nao")

        with dt3:
            st.subheader("Forest Plot - Efeitos Fixos")
            fe_df = pd.DataFrame({"Efeito": fe.index, "Est": fe.values, "SE": se.values})
            fe_df = fe_df[fe_df["Efeito"] != "Intercept"]
            if fe_df.empty:
                st.info("Apenas intercepto no modelo.")
            else:
                fe_df["lo"] = fe_df["Est"] - 1.96 * fe_df["SE"]
                fe_df["hi"] = fe_df["Est"] + 1.96 * fe_df["SE"]
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=fe_df["Est"], y=fe_df["Efeito"], mode="markers",
                    marker=dict(size=9, color=GDM_LIME, line=dict(color=GDM_NAVY, width=1)),
                    error_x=dict(type="data", symmetric=False,
                                 array=(fe_df["hi"] - fe_df["Est"]).tolist(),
                                 arrayminus=(fe_df["Est"] - fe_df["lo"]).tolist()),
                    name="IC 95%"))
                fig.add_vline(x=0, line_dash="dash", line_color=GDM_CORAL)
                fig.update_layout(height=max(350, len(fe_df) * 30))
                show_plot(fig)
