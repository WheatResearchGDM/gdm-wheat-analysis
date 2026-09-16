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
from analysis import (
    BLOCK, NESTED_BLOCK, YEAR, data_fingerprint, diagnostic_data,
    environmental_data, fit_trial_model, refit_without_outliers,
)
from reporting import (
    cycle_data, genotype_count, head_to_head_wins, model_equation,
    reference_regression,
)
from trial_units import add_trial_unit_columns, SOURCE_ROW
from scipy import stats

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="GDM Wheat Analysis",
    page_icon="\U0001F33E",
    layout="wide",
    initial_sidebar_state="collapsed",
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
REQUIRED_UPLOAD_COLUMNS = {
    "year", "trial_id", "trial_name", "germplasm_name", "yield"
}
MATERIAL_GID_COLUMN = "gid"
NULL_FILTER_VALUE = "(Nulo)"
TRIAL_KEY_COLUMN = "_trial_unit_key"
TRIAL_LABEL_COLUMN = "trial_unit_label"
TRIAL_DISPLAY_LABEL = "Ano | Ensaio | Local / Ambiente DEV"
TRIAL_DEFINITION = "PROD-PLACEMENT: year | trial_name | environment_dev_file. Demais áreas: year | trial_name | location_name."
TRIAL_UNIT_RULE = "area-year-dependent-v2"
IMPORT_CACHE_VERSION = "material-selection-v1"
MODEL_HIDDEN_COLUMNS = {"trial_id", "trial_name", TRIAL_KEY_COLUMN, SOURCE_ROW, "plot_id", "plot_number", "plot_id_in_source"}
DEFAULT_FILTER_VALUES = {
    "plot_is_discarded": ["False"],
    "missing_dev_file": ["no", NULL_FILTER_VALUE],
}

MATERIAL_FILTER_LABELS = {
    "category": "Categoria",
    "brand": "Marca",
    "cycle": "Ciclo",
}
GENOTYPE_SELECTION_MODES = {
    "Categoria": "category",
    "Ciclo": "cycle",
}
CATEGORY_GROUP_LABELS = {
    "commercial": "Comerciais",
    "comercial": "Comerciais",
    "check": "Checks",
    "testemunha": "Checks",
    "experimental": "Experimentais",
}
REMOVED_OBSERVATION_FILTERS = {
    "country_name", "state_name", "location_name", "signed_status", "condition_file",
}

OBSERVATION_FILTERS = [
    ("year", "Ano"),
    ("trial_type", "Tipo de ensaio"),
    ("plot_is_discarded", "Parcela descartada SEEDS"),
    ("missing_dev_file", "Parcela descartada DEV"),
    ("country_name", "País"),
    ("macroregion_name", "Macrorregião"),
    ("microregion_name", "Microrregião"),
    ("state_name", "Estado"),
    ("location_name", "Local"),
    (TRIAL_LABEL_COLUMN, TRIAL_DISPLAY_LABEL),
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

section[data-testid="stSidebar"] [data-testid="stDownloadButton"] button {
    background: var(--gdm-lime) !important;
    border: 1px solid var(--gdm-lime) !important;
    color: var(--gdm-navy) !important;
}

section[data-testid="stSidebar"] [data-testid="stDownloadButton"] button p,
section[data-testid="stSidebar"] [data-testid="stDownloadButton"] button span {
    color: var(--gdm-navy) !important;
    font-weight: 700 !important;
}

section[data-testid="stSidebar"] [data-testid="stButton"] button {
    background: rgba(255,255,255,.08) !important;
    border: 1px solid rgba(255,255,255,.20) !important;
}

section[data-testid="stSidebar"] [data-testid="stButton"] button p {
    color: #FFFFFF !important;
    font-weight: 700 !important;
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
    background: #FFFFFF;
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

div[data-testid="stRadio"] div[role="radiogroup"] label p {
    color: var(--gdm-gray) !important;
}

div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p {
    color: #FFFFFF !important;
}

.scenario-heading {
    background: #FFFFFF;
    border: 1px solid var(--gdm-line);
    border-radius: 18px;
    box-shadow: 0 16px 38px rgba(9,36,59,.08);
    margin-bottom: 1rem;
    padding: 1.4rem 1.5rem 1.15rem;
}

.scenario-heading__eyebrow {
    color: var(--gdm-lime);
    font-size: .7rem;
    font-weight: 700;
    letter-spacing: .12em;
    text-transform: uppercase;
}

.scenario-heading h2 {
    color: var(--gdm-navy);
    font-size: 1.45rem;
    margin: .3rem 0 .35rem;
}

.scenario-heading p {
    color: var(--gdm-gray);
    margin: 0;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255,255,255,.86);
    border-color: var(--gdm-line);
    border-radius: 16px;
    box-shadow: 0 12px 28px rgba(9,36,59,.055);
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

/* Only the main page navigation sticks; nested result tabs scroll normally. */
[data-testid="stTabs"]:not([data-testid="stTabs"] [data-testid="stTabs"]) > div > div:has(> [role="tablist"]) {
    position: sticky;
    top: 3.75rem;
    z-index: 990;
    background: #F5F7F2;
    padding: .5rem .2rem;
    box-shadow: 0 7px 14px rgba(9,36,59,.10);
    border-radius: 12px;
}
button[data-baseweb="tab"] p { color: inherit !important; }

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
    cycles = ["Precoce", "Médio", "Tardio"]
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
                cycle = cycles[(trial_counter - 1) % len(cycles)]
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
                            "trial_id": f"TRIAL-{trial_counter:04d}",
                            "plot_id": f"PLOT-{len(rows) + 1:06d}",
                            TRIAL_KEY_COLUMN: f"{yr} | {trial_name} | {loc_name}",
                            TRIAL_LABEL_COLUMN: f"{yr} | {trial_name} | {loc_name}",
                            "trial_name": trial_name,
                            "trial_type": tt,
                            "trial_number": trial_counter,
                            "pipeline_file": pipe,
                            "condition_file": cond,
                            "cycle_file": cycle,
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
    return add_trial_unit_columns(pd.DataFrame(rows))

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
        category=lambda frame: np.select(
            [
                frame["commercial_name"].str.startswith("GDM-"),
                frame["commercial_name"].isin(["TBIO Toruk", "TBIO Sonic"]),
            ],
            ["EXPERIMENTAL", "CHECK"],
            default="COMMERCIAL",
        ),
        cycle="Não informado",
        days_to_spike=lambda frame: 55 + np.arange(len(frame)) % 35,
        **{"Tipo de elemento": "Item"},
    )
)

CATEGORICAL_COLS = [
    "data_source", "trial_type", TRIAL_LABEL_COLUMN, "pipeline_file",
    "condition_file", "cycle_file", "signed_status", "location_name",
    "state_name", "country_name", "macroregion_name", "microregion_name",
    "germplasm_name", "gid", "company_name", "area",
    "plot_is_discarded", "missing_dev_file",
]


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------
def normalize_identifier_value(value):
    """Normalize numeric or textual identifiers without exposing float suffixes."""
    if pd.isna(value):
        return None
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)) and float(value).is_integer():
        return str(int(value))
    normalized = str(value).strip()
    return normalized or None


@st.cache_data(show_spinner=False)
def read_uploaded_excel(file_bytes: bytes, trial_unit_rule: str, cache_version: str):
    """Read observations from sheet 1 and, when present, materials from sheet 2."""
    if trial_unit_rule != TRIAL_UNIT_RULE:
        raise ValueError("Regra de identificação dos ensaios incompatível com esta versão do app.")
    if cache_version != IMPORT_CACHE_VERSION:
        raise ValueError("Versão do processamento da planilha incompatível com esta versão do app.")
    workbook = pd.ExcelFile(BytesIO(file_bytes), engine="openpyxl")
    df = pd.read_excel(workbook, sheet_name=0)
    df.columns = [str(column).strip() for column in df.columns]
    df = df.drop(columns=[SOURCE_ROW], errors="ignore").dropna(how="all")
    df[SOURCE_ROW] = df.index.to_numpy() + 2  # Excel row, accounting for the header and blank rows.
    df = df.reset_index(drop=True)

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

    df = add_trial_unit_columns(df)
    return df, invalid_yield, materials, material_sheet_name


def normalize_gid_value(value):
    """Normalize numeric and textual GIDs to the same stable string representation."""
    return normalize_identifier_value(value)


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


def material_display_labels(
    materials: pd.DataFrame,
    observations: pd.DataFrame,
) -> dict:
    """Use germplasm_name as label while retaining GID as the stored value."""
    names_by_gid = {}
    if {"gid", "germplasm_name"}.issubset(observations.columns):
        name_rows = observations[["gid", "germplasm_name"]].dropna().copy()
        name_rows["gid"] = normalize_gid_series(name_rows["gid"])
        names_by_gid = (
            name_rows.drop_duplicates("gid").set_index("gid")["germplasm_name"].to_dict()
        )

    labels = {}
    for _, row in materials.iterrows():
        gid = normalize_gid_value(row.get(MATERIAL_GID_COLUMN))
        if gid is None:
            continue
        name = names_by_gid.get(gid)
        labels[gid] = str(name).strip() if pd.notna(name) else gid
    return labels


def material_selection_groups(materials: pd.DataFrame, group_column: str):
    """Group material GIDs for the category/cycle selector without dropping nulls."""
    if group_column not in materials.columns:
        return [("Todos os genótipos", materials["gid"].dropna().tolist())]

    grouped = {}
    for _, row in materials.iterrows():
        gid = normalize_gid_value(row.get("gid"))
        if gid is None:
            continue
        raw_group = row.get(group_column)
        if pd.isna(raw_group) or not str(raw_group).strip():
            label = "Sem categoria" if group_column == "category" else "Sem ciclo"
        else:
            value = str(raw_group).strip()
            label = CATEGORY_GROUP_LABELS.get(value.casefold(), value)
        grouped.setdefault(label, []).append(gid)

    category_order = {"Comerciais": 0, "Checks": 1, "Experimentais": 2, "Sem categoria": 98}
    return sorted(
        grouped.items(),
        key=lambda item: (category_order.get(item[0], 10), item[0].casefold()),
    )


def genotype_group_widget_label(mode: str, group_label: str) -> str:
    if mode == "Categoria":
        known = {
            "Comerciais": "Selecionar comerciais",
            "Checks": "Selecionar checks",
            "Experimentais": "Selecionar experimentais",
            "Sem categoria": "Selecionar sem categoria",
        }
        return known.get(group_label, f"Selecionar {group_label}")
    return f"Ciclo · {group_label}"


def scenario_payload(source_id, material_columns, observation_columns):
    """Save the live selection, including every datacut and quality filter."""
    datacut_columns = {
        "year", "trial_type", "country_name", "macroregion_name", "microregion_name",
        "state_name", "location_name", TRIAL_LABEL_COLUMN, "pipeline_file", "cycle_file",
    }
    observation_filters = {
        c: st.session_state.get(filter_state_key(c, source_id), [])
        for c in observation_columns
    }
    return {
        "app": "gdm-wheat-analysis", "version": 5, "trial_unit_rule": TRIAL_UNIT_RULE,
        "name": st.session_state.get(f"scenario_name_{source_id}") or "Cenário GDM",
        "saved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_fingerprint": source_id,
        "filters": {
            "material_selection_mode": st.session_state.get(
                filter_state_key("genotype_selection_mode", source_id, "material"),
                "Categoria",
            ),
            "material_attributes": {
                c: st.session_state.get(filter_state_key(c, source_id, "material"), [])
                for c in material_columns
            },
            "selected_gids": st.session_state.get(
                filter_state_key("selected_gids", source_id, "material"), []),
            "datacut": {c: v for c, v in observation_filters.items() if c in datacut_columns},
            "additional": {c: v for c, v in observation_filters.items() if c not in datacut_columns},
        },
    }


def load_scenario_into_state(payload, source_id, active_data=None):
    """Restore scenarios before widgets, replacing previous selections."""
    if not isinstance(payload, dict) or payload.get("app") != "gdm-wheat-analysis":
        raise ValueError("Este JSON não é um cenário do GDM Wheat Analysis.")
    if payload.get("version") not in [1, 2, 3, 4, 5]:
        raise ValueError("Versão de cenário não suportada.")
    filters = payload.get("filters")
    if not isinstance(filters, dict):
        raise ValueError("O cenário não contém filtros válidos.")
    groups = {name: filters.get(name, {}) for name in
              ["material_attributes", "observations", "datacut", "additional"]}
    if any(not isinstance(values, dict) for values in groups.values()):
        raise ValueError("Formato inválido dos filtros.")
    if any(not isinstance(v, list) for group in groups.values() for v in group.values()):
        raise ValueError("As seleções de cada filtro precisam ser listas.")
    gids = filters.get("selected_gids", [])
    if not isinstance(gids, list):
        raise ValueError("A seleção de genótipos precisa ser uma lista.")
    selection_mode = filters.get("material_selection_mode", "Categoria")
    if selection_mode not in GENOTYPE_SELECTION_MODES:
        selection_mode = "Categoria"
    observations = {**groups["observations"], **groups["datacut"], **groups["additional"]}
    if payload.get("trial_unit_rule") != TRIAL_UNIT_RULE and observations.get(TRIAL_LABEL_COLUMN):
        raise ValueError("Este cenário usa a regra antiga de identificação dos ensaios. "
                         "Recrie a seleção com o prefixo de ano e salve um novo cenário; "
                         "as seleções atuais não foram alteradas.")
    # Clear old values as well as widget values; an omitted filter must not leak.
    for key in list(st.session_state):
        if key.endswith("_" + source_id) and key.startswith(("cascade_", "material_")):
            del st.session_state[key]
    for column, values in groups["material_attributes"].items():
        st.session_state[filter_state_key(column, source_id, "material")] = values
    observations = {**groups["observations"], **groups["datacut"], **groups["additional"]}
    for column in CATEGORICAL_COLS + [c for c, _ in OBSERVATION_FILTERS]:
        if column not in {"gid", "germplasm_name"}:
            st.session_state[filter_state_key(column, source_id)] = observations.get(column, [])
    st.session_state[filter_state_key("selected_gids", source_id, "material")] = [
        normalize_gid_value(gid) for gid in gids
    ]
    st.session_state[filter_state_key(
        "genotype_selection_mode", source_id, "material",
    )] = selection_mode
    if payload.get("version", 1) < 5 and not gids:
        st.session_state[f"material_legacy_select_all_{source_id}"] = True
    st.session_state[f"scenario_name_{source_id}"] = str(payload.get("name") or "Cenário GDM")


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


def column_display_name(column: str) -> str:
    """Return a readable label for internal analysis columns."""
    if column == TRIAL_LABEL_COLUMN:
        return TRIAL_DISPLAY_LABEL
    if column == YEAR:
        return "Ano (categórico)"
    if column in {BLOCK, NESTED_BLOCK}:
        return "Bloco dentro de ensaio"
    if column == "germplasm_name":
        return "Genótipo"
    return column


def recommended_model_spec(data: pd.DataFrame):
    """Return the adaptive multi-environment selection model specification."""
    fixed = [YEAR] if YEAR in data and data[YEAR].dropna().nunique() > 1 else []
    random = [TRIAL_LABEL_COLUMN]
    has_nested_blocks = False
    if BLOCK in data:
        valid_blocks = data[[TRIAL_LABEL_COLUMN, BLOCK]].dropna()
        has_nested_blocks = (
            not valid_blocks.empty
            and valid_blocks.groupby(TRIAL_LABEL_COLUMN, observed=True)[BLOCK]
            .nunique().gt(1).any()
        )
        if has_nested_blocks:
            random.append(BLOCK)
    return fixed, random, has_nested_blocks


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
# Workspace: all controls live in Cenários / Datacut (tabs preserve widget state)
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="gdm-eyebrow">GDM · Wheat Research</div>',
    unsafe_allow_html=True,
)
(scenario_page, overview_page, model_page, diagnostics_page,
 results_page, cycle_page, environmental_page) = st.tabs([
    "◎ Cenários / Datacut", "▦ Visão geral", "◈ Modelo · BLUE / BLUP",
    "⌁ Diagnósticos", "↗ Resultados", "◷ Produtividade × ciclo", "⇄ Índice ambiental",
])

with scenario_page:
    render_page_intro(
        "Configuração", "Cenários / Datacut",
        "Defina os materiais e os ensaios. As seleções são aplicadas imediatamente a todas as análises.",
    )
    with st.expander("Arquivo de dados e template", expanded=True):
        upload_column, template_column = st.columns([3, 1])
        uploaded_file = upload_column.file_uploader(
            "Arquivo Excel", type=["xlsx"],
            help="Primeira aba: observações. Segunda aba: cadastro de materiais, vinculado por gid.",
        )
        if TEMPLATE_PATH.exists():
            template_column.download_button(
                "Baixar template Excel", TEMPLATE_PATH.read_bytes(),
                "template_dados_fenotipicos.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
            )
    active_data = SAMPLE_DATA.copy()
    active_materials = SAMPLE_MATERIALS.copy()
    source_id = "demonstrative-data"
    source_badge = "Dados demonstrativos"
    if uploaded_file is not None:
        try:
            uploaded_bytes = uploaded_file.getvalue()
            active_data, invalid_yield_count, uploaded_materials, _ = read_uploaded_excel(
                uploaded_bytes, TRIAL_UNIT_RULE, IMPORT_CACHE_VERSION,
            )
            source_id = hashlib.sha256(uploaded_bytes).hexdigest()[:12]
            source_badge = uploaded_file.name
            if "gid" not in active_data:
                active_data["gid"] = active_data["germplasm_name"]
            active_materials = uploaded_materials if uploaded_materials is not None else (
                active_data[["gid", "germplasm_name"]].drop_duplicates("gid")
            )
            if invalid_yield_count:
                st.warning(f"{invalid_yield_count} valor(es) de produtividade inválido(s) serão omitidos.")
        except Exception as exc:
            st.error(f"Não foi possível importar o arquivo: {exc}")
            st.stop()

    active_data["gid"] = normalize_gid_series(active_data["gid"])
    active_materials["gid"] = normalize_gid_series(active_materials["gid"])
    available_materials = active_materials.dropna(subset=["gid"]).drop_duplicates("gid")
    available_materials = available_materials.loc[
        available_materials["gid"].isin(active_data["gid"].dropna())
    ].copy()
    st.caption(f"{source_badge} · {format_integer(len(active_data))} parcelas")

    with st.container(border=True):
        section_label("1 · Cenário — identificação e materiais")
        scenario_file = st.file_uploader(
            "Abrir cenário e datacut (JSON)", type=["json"], key="scenario_file_uploader",
        )
        if scenario_file is not None:
            try:
                scenario_bytes = scenario_file.getvalue()
                signature = hashlib.sha256(scenario_bytes + source_id.encode()).hexdigest()
                if st.session_state.get("applied_scenario_signature") != signature:
                    saved = json.loads(scenario_bytes.decode("utf-8-sig"))
                    load_scenario_into_state(saved, source_id, active_data)
                    st.session_state["applied_scenario_signature"] = signature
                    st.session_state["scenario_source_mismatch"] = saved.get("source_fingerprint") not in [None, source_id]
                st.success("Cenário e datacut restaurados.")
                if st.session_state.get("scenario_source_mismatch"):
                    st.info("A base difere da usada ao salvar. Apenas opções presentes são aplicadas.")
            except Exception as exc:
                st.error(f"Não foi possível abrir o cenário: {exc}")
        else:
            st.session_state.pop("applied_scenario_signature", None)
        st.text_input("Nome do cenário", key=f"scenario_name_{source_id}", placeholder="Ex.: BRA_VCU_2026")
        material_filter_columns = [c for c in ["brand"] if c in available_materials]
        material_cut = available_materials.copy()
        with st.expander("Filtro adicional de materiais", expanded=False):
            material_columns = st.columns(3)
            for index, column in enumerate(material_filter_columns):
                material_cut, _ = cascading_multiselect(
                    material_columns[index % 3], material_cut, column,
                    MATERIAL_FILTER_LABELS[column], source_id, key_prefix="material",
                )
        material_labels = material_display_labels(available_materials, active_data)
        selected_gid_key = filter_state_key("selected_gids", source_id, "material")
        had_saved_selection = selected_gid_key in st.session_state
        saved_gids = set(st.session_state.get(selected_gid_key, []))
        legacy_select_all_key = f"material_legacy_select_all_{source_id}"
        select_all_groups = not had_saved_selection or st.session_state.get(legacy_select_all_key, False)

        available_modes = [
            mode for mode, column in GENOTYPE_SELECTION_MODES.items()
            if column in material_cut and material_cut[column].notna().any()
        ]
        mode_key = filter_state_key("genotype_selection_mode", source_id, "material")
        if not available_modes:
            selection_mode = "Todos"
            group_column = ""
        else:
            if st.session_state.get(mode_key) not in available_modes:
                st.session_state[mode_key] = available_modes[0]
            if len(available_modes) > 1:
                selection_mode = st.radio(
                    "Selecionar genótipos por:", available_modes,
                    horizontal=True, key=mode_key,
                )
            else:
                selection_mode = available_modes[0]
                st.session_state[mode_key] = selection_mode
                st.caption(f"Selecionar genótipos por: **{selection_mode}**")
            group_column = GENOTYPE_SELECTION_MODES[selection_mode]

        groups = material_selection_groups(material_cut, group_column)
        group_columns = st.columns(min(3, max(1, len(groups))))
        selected_gids = []
        for index, (group_label, group_gids) in enumerate(groups):
            options = sorted(
                set(group_gids),
                key=lambda gid: material_labels.get(gid, gid).casefold(),
            )
            group_hash = hashlib.sha256(
                f"{group_column}|{group_label}".encode("utf-8")
            ).hexdigest()[:10]
            group_key = filter_state_key(
                f"selected_gids_{group_hash}", source_id, "material",
            )
            if group_key in st.session_state:
                st.session_state[group_key] = [
                    gid for gid in st.session_state[group_key] if gid in options
                ]
            else:
                st.session_state[group_key] = (
                    options if select_all_groups else [gid for gid in options if gid in saved_gids]
                )
            selected_gids.extend(group_columns[index % len(group_columns)].multiselect(
                genotype_group_widget_label(selection_mode, group_label),
                options,
                format_func=lambda gid: material_labels.get(gid, gid),
                key=group_key,
            ))

        effective_gids = list(dict.fromkeys(selected_gids))
        st.session_state[selected_gid_key] = effective_gids
        st.session_state.pop(legacy_select_all_key, None)
        filtered_data = active_data.loc[active_data["gid"].isin(effective_gids)].copy()
        if effective_gids:
            st.caption(f"{len(effective_gids)} genótipo(s) incluído(s).")
        else:
            st.warning("Nenhum genótipo selecionado. Escolha ao menos um material em um dos grupos.")

    with st.container(border=True):
        section_label("2 · Datacut — recorte dos ensaios")
        st.caption("Filtros em cascata: cada escolha limita as opções seguintes.")
        st.caption(TRIAL_DEFINITION)
        cut_columns = st.columns(3)
        datacut_filters = [
            ("year", "Ano"), ("trial_type", "Tipo de ensaio"),
            ("macroregion_name", "Macrorregião"),
            ("microregion_name", "Microrregião"), (TRIAL_LABEL_COLUMN, TRIAL_DISPLAY_LABEL),
            ("pipeline_file", "Pipeline"), ("cycle_file", "Ciclo"),
        ]
        for index, (column, label) in enumerate(datacut_filters):
            filtered_data, _ = cascading_multiselect(
                cut_columns[index % 3], filtered_data, column, label, source_id,
            )

    with st.container(border=True):
        section_label("3 · Demais variáveis e qualidade")
        quality_filters = [
            ("plot_is_discarded", "Parcela descartada SEEDS"),
            ("missing_dev_file", "Parcela descartada DEV"),
        ]
        quality_columns = st.columns(2)
        for column_ui, (column, label) in zip(quality_columns, quality_filters):
            filtered_data, _ = cascading_multiselect(
                column_ui, filtered_data, column, label, source_id,
                DEFAULT_FILTER_VALUES.get(column),
            )
        dedicated_filters = {c for c, _ in datacut_filters + quality_filters} | {"gid", "germplasm_name"}
        other_filters = [c for c in CATEGORICAL_COLS if c not in dedicated_filters
                         and c not in REMOVED_OBSERVATION_FILTERS and c in active_data]
        with st.expander("Outras variáveis"):
            other_columns = st.columns(3)
            for index, column in enumerate(other_filters):
                filtered_data, _ = cascading_multiselect(
                    other_columns[index % 3], filtered_data, column,
                    column_display_name(column), source_id,
                )
    observation_filter_columns = [
        c for c, _ in datacut_filters + quality_filters if c in active_data
    ] + other_filters
    st.session_state["df"] = filtered_data.copy()
    st.session_state["active_source_id"] = source_id
    scenario = scenario_payload(source_id, material_filter_columns, observation_filter_columns)
    scenario_file_stem = "".join(
        c if c.isalnum() or c in "-_" else "_" for c in scenario["name"]
    ).strip("_") or "cenario_gdm"
    st.download_button(
        "Salvar cenário + datacut (JSON)",
        json.dumps(scenario, ensure_ascii=False, indent=2).encode("utf-8"),
        f"{scenario_file_stem}.json", "application/json", width="stretch",
        help="Inclui nome, materiais, genótipos, datacut e demais filtros selecionados.",
    )
    st.success(
        f"Datacut ativo: {format_integer(len(filtered_data))} parcelas · "
        f"{filtered_data[TRIAL_KEY_COLUMN].nunique()} ensaios · "
        f"{genotype_count(filtered_data)} genótipos"
    )

current_signature = data_fingerprint(filtered_data)
if "analysis" in st.session_state and (st.session_state["analysis"]["signature"] != current_signature
                                      or "diagnostics" not in st.session_state["analysis"]):
    st.session_state.pop("analysis")
    st.session_state.pop("analysis_before_exclusions", None)
    st.session_state["analysis_invalidated"] = True

# ---------------------------------------------------------------------------
# Page: Dados
# ---------------------------------------------------------------------------
with overview_page:
    render_page_intro(
        "Visão geral",
        "Dados fenotípicos · Trigo",
        "Resumo da base após os filtros selecionados em Cenários / Datacut.",
    )
    df = st.session_state["df"]
    c1, c2, c3, c4 = st.columns(4)
    render_metric(c1, "▤", "Registros", len(df), "parcelas na seleção atual")
    render_metric(c2, "⌗", "Variáveis", len(df.columns), "atributos disponíveis")
    render_metric(
        c3,
        "◫",
        "Ensaios",
        df[TRIAL_KEY_COLUMN].nunique() if TRIAL_KEY_COLUMN in df.columns else "-",
        "nome + local ou ambiente DEV",
    )
    render_metric(
        c4,
        "♧",
        "Genótipos",
        genotype_count(df),
        "materiais avaliados",
    )

    if not df.empty and {"yield", TRIAL_LABEL_COLUMN}.issubset(df.columns):
        section_label("Panorama da seleção")
        yield_fig = px.histogram(
            df,
            x="yield",
            nbins=32,
            title="Distribuição de produtividade",
            labels={"yield": "Produtividade"},
            color_discrete_sequence=[GDM_LIME],
        )
        show_plot(yield_fig)
        with st.container(height=640, border=True):
            location_yield = (
                df.groupby([TRIAL_KEY_COLUMN, TRIAL_LABEL_COLUMN], as_index=False)["yield"]
                .mean()
                .sort_values("yield", ascending=True)
            )
            location_fig = px.bar(
                location_yield,
                x="yield",
                y=TRIAL_KEY_COLUMN,
                orientation="h",
                title="Produtividade média por ensaio",
                labels={"yield": "Produtividade média", TRIAL_KEY_COLUMN: ""},
                custom_data=[TRIAL_LABEL_COLUMN],
                color_discrete_sequence=[GDM_NAVY],
            )
            location_fig.update_traces(
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Produtividade média: %{x:,.1f}<extra></extra>"
                )
            )
            location_fig.update_yaxes(
                tickmode="array",
                tickvals=location_yield[TRIAL_KEY_COLUMN].tolist(),
                ticktext=location_yield[TRIAL_LABEL_COLUMN].tolist(),
            )
            location_fig.update_layout(height=max(480, 30 * len(location_yield)))
            show_plot(location_fig)

    section_label("Base filtrada")
    display_df = df.drop(columns=[TRIAL_KEY_COLUMN, SOURCE_ROW], errors="ignore")
    display_df = display_df[[TRIAL_LABEL_COLUMN] + [c for c in display_df if c != TRIAL_LABEL_COLUMN]]
    st.dataframe(
        display_df,
        width="stretch",
        height=500,
        column_config={TRIAL_LABEL_COLUMN: TRIAL_DISPLAY_LABEL},
    )
    with st.expander("Estatísticas descritivas"):
        num = df.select_dtypes(include=[np.number]).columns.tolist()
        if num:
            st.dataframe(df[num].describe().round(3), width="stretch")
    st.download_button(
        "Download CSV",
        display_df.to_csv(index=False),
        "wheat_data.csv",
        "text/csv",
    )

# ---------------------------------------------------------------------------
# Page: Environmental index head-to-head
# ---------------------------------------------------------------------------
with environmental_page:
    render_page_intro(
        "Comparação head-to-head",
        "Índice ambiental de produtividade",
        "Compare dois genótipos nos ambientes em que ambos foram avaliados.",
    )
    df = st.session_state["df"].copy()
    value_source = st.radio(
        "Valores do índice ambiental", ["Preditos (BLUE / BLUP)", "Dados brutos"],
        horizontal=True, key="environment_value_source",
    )
    fitted_analysis = st.session_state.get("analysis")
    prediction_ready = (
        fitted_analysis is not None and fitted_analysis["response"] == "yield"
        and fitted_analysis["signature"] == current_signature
    )
    use_predicted = value_source == "Preditos (BLUE / BLUP)"
    if fitted_analysis is not None and fitted_analysis.get("excluded_rows"):
        st.caption(f"O ajuste atual exclui {len(fitted_analysis['excluded_rows'])} parcela(s). "
                   "Preditos usam esse ajuste; Dados brutos mantêm o datacut completo, sem essas exclusões.")
    if use_predicted and not prediction_ready:
        st.info("Calcule BLUE ou BLUP para yield na aba Modelo · BLUE / BLUP com o datacut atual. "
                "Para explorar antes do ajuste, selecione Dados brutos.")
        df = df.iloc[:0]
    else:
        df = environmental_data(df, fitted_analysis if use_predicted else None)
        df[TRIAL_KEY_COLUMN] = df[TRIAL_LABEL_COLUMN]
        if use_predicted:
            st.caption(f"Predições do ajuste {fitted_analysis['method']} · "
                       f"{fitted_analysis['nobs']} parcelas usadas no ajuste.")
    required = {TRIAL_KEY_COLUMN, TRIAL_LABEL_COLUMN, "germplasm_name", "yield"}

    if not required.issubset(df.columns):
        missing = ", ".join(sorted(required.difference(df.columns)))
        st.warning(f"A base filtrada não contém as colunas necessárias: {missing}.")
    else:
        comparison_data = df[list(required)].copy()
        comparison_data["yield"] = pd.to_numeric(comparison_data["yield"], errors="coerce")
        comparison_data = comparison_data.dropna(
            subset=[TRIAL_KEY_COLUMN, TRIAL_LABEL_COLUMN, "germplasm_name", "yield"]
        )
        comparison_data[TRIAL_KEY_COLUMN] = comparison_data[TRIAL_KEY_COLUMN].astype(str)
        comparison_data[TRIAL_LABEL_COLUMN] = comparison_data[TRIAL_LABEL_COLUMN].astype(str)
        comparison_data["germplasm_name"] = comparison_data["germplasm_name"].astype(str)
        genotypes = sorted(comparison_data["germplasm_name"].unique().tolist())

        if use_predicted and not prediction_ready:
            pass
        elif len(genotypes) < 2:
            st.warning(
                "O datacut precisa conter pelo menos dois genótipos com produtividade válida."
            )
        else:
            presence = pd.crosstab(
                comparison_data[TRIAL_KEY_COLUMN],
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
                    pair_data.groupby(
                        [TRIAL_KEY_COLUMN, TRIAL_LABEL_COLUMN, "germplasm_name"],
                        as_index=False,
                    )["yield"]
                    .mean()
                    .rename(columns={"yield": "genotype_yield"})
                )
                common_trials = (
                    pair_means.groupby(TRIAL_KEY_COLUMN)["germplasm_name"]
                    .nunique()
                    .loc[lambda values: values == 2]
                    .index
                )

                if len(common_trials) == 0:
                    st.warning(
                        "Os genótipos selecionados não aparecem juntos em nenhum ensaio do datacut."
                    )
                else:
                    environmental_mean = (
                        comparison_data[
                            comparison_data[TRIAL_KEY_COLUMN].isin(common_trials)
                        ]
                        .groupby(TRIAL_KEY_COLUMN, as_index=False)
                        .agg(
                            environmental_mean=("yield", "mean"),
                            **{TRIAL_LABEL_COLUMN: (TRIAL_LABEL_COLUMN, "first")},
                        )
                    )
                    plot_data = pair_means[
                        pair_means[TRIAL_KEY_COLUMN].isin(common_trials)
                    ].drop(columns=[TRIAL_LABEL_COLUMN]).merge(
                        environmental_mean,
                        on=TRIAL_KEY_COLUMN,
                        how="inner",
                    )

                    mean_a = plot_data.loc[
                        plot_data["germplasm_name"] == genotype_a, "genotype_yield"
                    ].mean()
                    mean_b = plot_data.loc[
                        plot_data["germplasm_name"] == genotype_b, "genotype_yield"
                    ].mean()

                    m1, m2, m3, m4 = st.columns(4)
                    render_metric(m1, "◫", "Ensaios comuns", len(common_trials), "ensaios com ambos")
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
                        "O eixo X é a média dos genótipos disponíveis em cada ensaio, com peso igual "
                        "por genótipo. O eixo Y usa " + (
                            "a predição ajustada por genótipo × ensaio. " if use_predicted else
                            "a média bruta das parcelas por genótipo × ensaio. "
                        ) + "A comparação inclui apenas ensaios com ambos os genótipos."
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
                                customdata=genotype_data[[TRIAL_LABEL_COLUMN]],
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
                        xaxis_title="Média ambiental por ensaio",
                        yaxis_title="Produtividade predita" if use_predicted else "Produtividade média bruta",
                        hovermode="closest",
                    )
                    show_plot(fig)

                    section_label("Vitórias nos ensaios comuns")
                    wins = head_to_head_wins(plot_data, genotype_a, genotype_b)
                    win_fig = go.Figure(go.Pie(
                        labels=wins["Resultado"], values=wins["Ensaios"], hole=.6, sort=False,
                        marker=dict(colors=[GDM_LIME, GDM_NAVY, GDM_GRAY]),
                        texttemplate="%{label}<br>%{percent:.1%} · %{value} ensaios",
                        textposition="outside", automargin=True,
                        hovertemplate="%{label}: %{value} ensaios (%{percent:.1%})<extra></extra>",
                    ))
                    win_fig.update_layout(title="Vitórias por genótipo", height=430,
                        annotations=[dict(text=f"{len(common_trials)}<br>ensaios", x=.5, y=.5,
                                          font_size=19, showarrow=False)])
                    show_plot(win_fig)
                    st.caption("Uma vitória por ensaio comum, usando o modo bruto/predito selecionado. "
                               "Empates são separados; diferenças até 0,00000001 são tratadas como empate numérico.")
                    st.dataframe(wins, hide_index=True, width="stretch",
                        column_config={"Percentual": st.column_config.NumberColumn("% dos ensaios", format="%.1f%%")})

                    section_label("Detalhamento dos ambientes comuns")
                    comparison_table = (
                        plot_data.pivot(
                            index=[
                                TRIAL_KEY_COLUMN,
                                TRIAL_LABEL_COLUMN,
                                "environmental_mean",
                            ],
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
                    comparison_table = comparison_table.drop(columns=[TRIAL_KEY_COLUMN])
                    comparison_table = comparison_table.rename(
                        columns={TRIAL_LABEL_COLUMN: TRIAL_DISPLAY_LABEL}
                    )
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
                        "indice_ambiental_predito.csv" if use_predicted else "indice_ambiental_bruto.csv",
                        "text/csv",
                    )

# ---------------------------------------------------------------------------
# Page: Modelo Misto
# ---------------------------------------------------------------------------
with model_page:
    render_page_intro(
        "Modelagem", "Calcular BLUE e BLUP",
        "A escolha do efeito de genótipo determina a estimativa. " + TRIAL_DEFINITION,
    )
    df = st.session_state["df"].copy()
    if df.empty:
        st.warning("Selecione um datacut com observações.")
    else:
        numeric = [c for c in df.select_dtypes(include=[np.number]).columns
                   if c not in MODEL_HIDDEN_COLUMNS and c not in {"gid", "trial_number"}]
        response = st.selectbox("Variável resposta", numeric,
                                index=numeric.index("yield") if "yield" in numeric else 0)
        model_structure = st.radio(
            "Estrutura do modelo",
            ["Seleção multiambiente (recomendada)", "Personalizado"],
            horizontal=True,
        )
        model_factor_columns = list(dict.fromkeys(CATEGORICAL_COLS + [YEAR, BLOCK]))
        selectable = [c for c in model_factor_columns if c in df and c != "germplasm_name"
                      and c != "gid" and df[c].nunique() > 1]
        numeric_effects = [c for c in numeric if c != response and c not in model_factor_columns
                           and df[c].nunique() > 1]
        if model_structure.startswith("Seleção multiambiente"):
            genotype_mode = st.radio(
                "Efeito de genótipo", ["Fixo → BLUE", "Aleatório → BLUP"],
                index=1, horizontal=True, disabled=True, key="recommended_genotype_mode",
            )
            method = "BLUP"
            fixed, random_eff, has_nested_blocks = recommended_model_spec(df)
            include_gxe = st.checkbox(
                "Incluir interação genótipo × ensaio (aleatória)", value=True,
                disabled=True, key="recommended_gxe",
            )
            st.info(
                "Estrutura aplicada: genótipo aleatório; ano fixo categórico; ensaio aleatório; "
                + ("bloco aninhado no ensaio; " if has_nested_blocks else "")
                + "interação genótipo × ensaio aleatória."
            )
            if not fixed:
                st.warning("O datacut possui menos de dois anos; o efeito fixo de ano foi omitido.")
            if not has_nested_blocks:
                st.warning(
                    "num_repetitions não está disponível ou não identifica mais de um bloco por ensaio; "
                    "o componente de bloco foi omitido."
                )
        else:
            genotype_mode = st.radio(
                "Efeito de genótipo", ["Fixo → BLUE", "Aleatório → BLUP"],
                index=1, horizontal=True,
            )
            method = "BLUE" if genotype_mode.startswith("Fixo") else "BLUP"
            fixed_column, random_column = st.columns(2)
            with fixed_column:
                fixed = st.multiselect(
                    "Demais efeitos fixos",
                    list(dict.fromkeys([c for c in selectable if c != BLOCK] + numeric_effects)),
                    default=[TRIAL_LABEL_COLUMN] if TRIAL_LABEL_COLUMN in selectable else [],
                    format_func=column_display_name,
                )
            with random_column:
                random_eff = st.multiselect(
                    "Demais efeitos aleatórios", [c for c in selectable if c not in fixed],
                    format_func=column_display_name,
                    help=(
                        "num_repetitions é tratado automaticamente como bloco aninhado no ensaio. "
                        "Os demais fatores aleatórios são cruzados."
                    ),
                )
            include_gxe = st.checkbox("Incluir interação genótipo × ensaio (aleatória)", value=True)
        with st.container(border=True):
            section_label("Equação ilustrativa do modelo selecionado")
            st.latex(model_equation(method, fixed, random_eff, include_gxe))
            st.caption(f"y: {response} · μ: intercepto · "
                       + ("G: efeito fixo de genótipo (BLUE)" if method == "BLUE" else
                          "uᵍ: efeito aleatório de genótipo (BLUP)") + " · ε: resíduo da parcela.")
            for j, effect in enumerate(fixed, 1):
                st.caption(f"F{j}: {column_display_name(effect)} — fixo (fator ou covariável).")
            for j, effect in enumerate(random_eff, 1):
                st.caption(f"U{j}: {column_display_name(effect)} — aleatório.")
            if include_gxe:
                st.caption("uᵍ×ᵉ: interação aleatória genótipo × unidade de ensaio.")
            st.caption("i identifica a parcela; g(i) e e(i) são seu genótipo e ensaio. "
                       "Ilustração das escolhas acima, não uma confirmação de que o modelo já foi ajustado.")
        st.caption(
            "BLUE: médias ajustadas com genótipo fixo. BLUP: médias preditas com genótipo aleatório "
            "e efeito genotípico separado. As médias gerais dão peso igual aos ensaios; "
            "as predições do índice ambiental são específicas de cada genótipo × ensaio observado."
        )
        if not include_gxe:
            st.info("Sem interação, o modelo é aditivo: a diferença ajustada entre dois genótipos "
                    "é constante entre ensaios.")
        if st.session_state.get("analysis_invalidated"):
            st.info("O datacut mudou. Calcule novamente para atualizar predições e resultados.")
        if st.button(f"Calcular {method}", type="primary", width="stretch"):
            with st.spinner(f"Calculando {method} e predições por ensaio…"):
                try:
                    analysis = fit_trial_model(
                        df, response=response, method=method, fixed=fixed,
                        random=random_eff, interaction=include_gxe,
                    )
                    st.session_state["analysis"] = analysis
                    st.session_state.pop("analysis_before_exclusions", None)
                    st.session_state["analysis_invalidated"] = False
                    st.rerun()
                except Exception as exc:
                    st.error(f"Não foi possível ajustar: {exc}")
        if "analysis" in st.session_state:
            saved_fit = st.session_state["analysis"]
            st.success(f"{saved_fit['method']} calculado para {saved_fit['response']} · "
                       f"{saved_fit['nobs']} parcelas. Consulte Resultados e Índice ambiental.")
            if saved_fit["omitted"]:
                st.warning(f"{saved_fit['omitted']} parcela(s) excluída(s) por valores ausentes "
                           "ou não finitos nas variáveis do modelo.")
            if saved_fit.get("excluded_rows"):
                st.warning(f"Ajuste sem {len(saved_fit['excluded_rows'])} parcela(s) excluída(s) no diagnóstico. "
                           "Calcular novamente nesta aba inclui todas as parcelas válidas do datacut.")
            if saved_fit["warnings"]:
                with st.expander("Avisos do ajuste"):
                    for message in saved_fit["warnings"]:
                        st.write(message)
# ---------------------------------------------------------------------------
# Page: Resultados
# ---------------------------------------------------------------------------
with results_page:
    render_page_intro("Estimativas", "Resultados · BLUE / BLUP",
                      "Médias ajustadas, predições por ensaio e componentes de variância.")
    analysis = st.session_state.get("analysis")
    if analysis is None:
        st.info("Calcule BLUE ou BLUP na aba Modelo com o datacut atual.")
    else:
        if analysis.get("excluded_rows"):
            st.info(f"Resultados recalculados sem {len(analysis['excluded_rows'])} parcela(s) selecionada(s) "
                    "no diagnóstico. n e predições refletem somente as parcelas usadas no ajuste atual.")
        result_tabs = st.tabs(["Genótipos e ranking", "Predições por ensaio", "Variâncias", "Resumo"])
        with result_tabs[0]:
            estimates = analysis["genotypes"]
            estimate_min, estimate_max = estimates["Estimativa"].round(1).min(), estimates["Estimativa"].round(1).max()
            def estimate_color(value):
                value = round(value, 1)
                fraction = (value - estimate_min) / (estimate_max - estimate_min) if estimate_max > estimate_min else .5
                color = GDM_NAVY if fraction >= .75 else GDM_LIME if fraction >= .4 else GDM_SKY
                foreground = "#FFFFFF" if fraction >= .75 else GDM_NAVY
                return f"background-color: {color}; color: {foreground}; font-weight: bold"
            st.dataframe(estimates.style.map(estimate_color, subset=["Estimativa"]),
                width="stretch", hide_index=True, height=480,
                column_config={"germplasm_name": "Genótipo",
                    "Estimativa": st.column_config.NumberColumn(f"Estimativa · {analysis['method']}", format="%.1f"),
                    "n": st.column_config.NumberColumn("n · parcelas", help="Parcelas válidas efetivamente usadas no ajuste para este genótipo.", format="%d"),
                    "Ensaios": st.column_config.NumberColumn("n · ensaios", format="%d")})
            st.caption("Cor da estimativa: valores menores em azul-claro, intermediários em verde e maiores em azul-escuro. "
                       "n conta as parcelas usadas após excluir ausências nas variáveis do modelo; não é o número de predições.")
            st.caption(
                "Estimativa: média sobre os ensaios com pesos iguais e a mesma distribuição "
                "dos demais efeitos fixos para todos os genótipos. Interações aleatórias e "
                "outros efeitos aleatórios têm média zero na estimativa geral."
            )
            if analysis["method"] == "BLUP":
                st.caption("Efeito genotípico: desvio aleatório (BLUP), separado da produtividade predita.")
            top_n = st.number_input("Número de genótipos no gráfico", min_value=1,
                                    max_value=len(estimates), value=min(20, len(estimates)))
            rank_fig = px.bar(
                estimates.head(top_n).sort_values("Estimativa"),
                x="Estimativa", y="germplasm_name", orientation="h",
                labels={"Estimativa": f"{analysis['method']} · {analysis['response']}",
                        "germplasm_name": "Genótipo"},
                title=f"Ranking por {analysis['method']}", color_discrete_sequence=[GDM_NAVY],
            )
            rank_fig.update_layout(height=max(400, top_n * 28))
            with st.container(height=600, border=True):
                show_plot(rank_fig)
            st.download_button("Baixar estimativas CSV", estimates.to_csv(index=False),
                               f"estimativas_{analysis['method'].lower()}.csv", "text/csv")
        with result_tabs[1]:
            cells = analysis["cells"].rename(columns={
                TRIAL_LABEL_COLUMN: TRIAL_DISPLAY_LABEL, "predicted": "Predito",
                "raw_mean": "Média bruta", "n": "Parcelas",
            })
            trial_choices = sorted(cells[TRIAL_DISPLAY_LABEL].unique())
            chosen_trial = st.selectbox(f"{TRIAL_DISPLAY_LABEL} — predições", trial_choices, key="prediction_trial")
            selected_cells = cells.loc[cells[TRIAL_DISPLAY_LABEL].eq(chosen_trial)].sort_values("Predito")
            trial_fig = px.bar(selected_cells, x="Predito", y="germplasm_name", orientation="h",
                color="Predito", color_continuous_scale=GDM_SCALE,
                hover_data=["Parcelas", "Média bruta"],
                labels={"germplasm_name": "Genótipo", "Predito": f"{analysis['method']} · {analysis['response']}"},
                title=f"Predições · {chosen_trial}")
            trial_fig.update_layout(height=max(420, 29 * len(selected_cells)), coloraxis_showscale=False)
            with st.container(height=610, border=True):
                show_plot(trial_fig)
            st.caption("O filtro acima altera somente o gráfico. A tabela e o download abaixo incluem todos os ensaios do ajuste.")
            st.dataframe(cells, width="stretch", hide_index=True)
            st.caption("Somente combinações observadas no ajuste. Outros efeitos aleatórios "
                       "(ex.: blocos) são fixados em zero para comparar genótipos.")
            st.download_button("Baixar predições por ensaio", cells.to_csv(index=False),
                               "predicoes_por_ensaio.csv", "text/csv")
        with result_tabs[2]:
            variance = analysis["variance"].copy()
            variance["Componente"] = variance["Componente"].map(column_display_name)
            st.dataframe(variance, width="stretch", hide_index=True)
            if variance["Variância"].ge(0).all() and variance["Variância"].sum() > 0:
                variance_fig = px.pie(variance, names="Componente", values="Variância", hole=.55,
                    color_discrete_sequence=[GDM_LIME, GDM_NAVY, GDM_GRAY, GDM_CORAL, GDM_SKY],
                    title="Proporção dos componentes de variância")
                variance_fig.update_traces(texttemplate="%{label}<br>%{percent:.1%}", textposition="outside", automargin=True,
                    hovertemplate="%{label}<br>Variância: %{value:,.2f}<br>%{percent:.1%}<extra></extra>")
                variance_fig.update_layout(height=460)
                show_plot(variance_fig)
                st.caption("Proporções calculadas sobre a soma dos componentes aleatórios e do resíduo. "
                           "Efeitos fixos não entram nesta soma; isto não representa R² nem herdabilidade.")
            else:
                st.info("Não há componentes positivos de variância para representar em pizza.")
            if analysis["method"] == "BLUE":
                st.caption("Genótipo fixo: não se estima variância genotípica nem herdabilidade neste ajuste.")
            else:
                st.caption("A herdabilidade exige definição do delineamento e da variância de "
                           "erro das predições; não é inferida apenas da variância do primeiro fator.")
        with result_tabs[3]:
            st.text(str(analysis["result"].summary()))
            st.write("Efeitos fixos: " + ", ".join(map(column_display_name, analysis["fixed"])))
            st.write("Efeitos aleatórios: " + ", ".join(map(column_display_name, analysis["random"])))
            st.write("Interação genótipo × ensaio: " + ("Sim" if analysis["interaction"] else "Não"))

with diagnostics_page:
    render_page_intro("Qualidade", "Diagnósticos do ajuste",
                      "Resíduos por parcela e incerteza dos coeficientes fixos.")
    analysis = st.session_state.get("analysis")
    if analysis is None:
        st.info("Calcule BLUE ou BLUP na aba Modelo com o datacut atual.")
    else:
        st.caption(f"Ajuste exibido: {analysis['method']} para {analysis['response']} · "
                   f"{analysis['nobs']} parcelas usadas · {analysis['omitted']} omitidas por dados ausentes · "
                   f"{len(analysis.get('excluded_rows', []))} excluídas pelo diagnóstico.")
        threshold = st.number_input("Limite de sinalização |resíduo / σ residual|",
                                    min_value=1., max_value=10., value=3., step=.25, key="outlier_threshold")
        diagnostic = diagnostic_data(analysis, threshold)
        diagnostic["Sinalização"] = np.where(diagnostic["outlier"], "Candidato a outlier", "Demais parcelas")
        if not np.isfinite(diagnostic["scaled_residual"]).all():
            st.warning("Variância residual nula ou inválida: não é possível sinalizar outliers por esse critério.")
        st.caption("Critério exploratório: |resíduo| / √variância residual acima do limite. "
                   "Não é um teste formal nem um resíduo studentizado; revise as parcelas antes de excluir. "
                   "Cada ponto mostra o plot e a linha do Excel, inclusive quando plot_id se repete.")
        hover_columns = ["plot_label", SOURCE_ROW, TRIAL_LABEL_COLUMN, "germplasm_name",
                         "observed", "fitted", "residual", "scaled_residual"]
        hover_template = ("Plot: %{customdata[0]}<br>Linha: %{customdata[1]}<br>"
                          "%{customdata[2]}<br>Genótipo: %{customdata[3]}<br>"
                          "Observado: %{customdata[4]:,.2f}<br>Ajustado: %{customdata[5]:,.2f}<br>"
                          "Resíduo: %{customdata[6]:,.2f}<br>Resíduo / σ: %{customdata[7]:.3f}<extra></extra>")
        diagnostic_colors = {"Candidato a outlier": GDM_CORAL, "Demais parcelas": GDM_NAVY}
        chart_left, chart_right = st.columns(2)
        with chart_left:
            fig = px.scatter(diagnostic, x="fitted", y="residual", color="Sinalização", opacity=.7,
                             color_discrete_map=diagnostic_colors, custom_data=hover_columns,
                             labels={"fitted": "Ajustados por parcela", "residual": "Resíduos"},
                             title="Resíduos × ajustados")
            fig.update_traces(hovertemplate=hover_template)
            fig.add_hline(y=0, line_dash="dash", line_color=GDM_CORAL)
            show_plot(fig)
        with chart_right:
            qq = diagnostic.sort_values("residual", kind="stable").copy()
            qq["quantile"] = stats.norm.ppf((np.arange(len(qq)) + .5) / len(qq))
            qq_fig = px.scatter(qq, x="quantile", y="residual", color="Sinalização",
                                color_discrete_map=diagnostic_colors, custom_data=hover_columns,
                                labels={"quantile": "Quantis normais", "residual": "Resíduos ordenados"},
                                title="QQ plot · identificação das parcelas")
            qq_fig.update_traces(hovertemplate=hover_template)
            sigma = np.sqrt(float(analysis["result"].scale))
            if np.isfinite(sigma) and sigma > 0:
                reference_x = np.array([qq["quantile"].min(), qq["quantile"].max()])
                qq_fig.add_trace(go.Scatter(x=reference_x, y=sigma * reference_x, mode="lines",
                    line=dict(color=GDM_GRAY, dash="dash"), name="Referência normal", hoverinfo="skip"))
            show_plot(qq_fig)
        flagged = diagnostic.loc[diagnostic["outlier"]].sort_values(
            "scaled_residual", key=lambda value: value.abs(), ascending=False)
        display_names = {SOURCE_ROW: "Linha de origem", "plot_label": "Plot",
                         TRIAL_LABEL_COLUMN: TRIAL_DISPLAY_LABEL, "germplasm_name": "Genótipo",
                         "observed": "Observado", "fitted": "Ajustado", "residual": "Resíduo",
                         "scaled_residual": "Resíduo / σ residual", "threshold": "Limite usado"}
        section_label("Revisar parcelas sinalizadas")
        if flagged.empty:
            st.info("Nenhuma parcela foi sinalizada com o limite atual.")
        else:
            st.dataframe(flagged[hover_columns].rename(columns=display_names), width="stretch", hide_index=True)
        row_labels = {row[SOURCE_ROW]: f"Plot {row['plot_label']} · linha {row[SOURCE_ROW]} · "
                      f"{row[TRIAL_LABEL_COLUMN]} · {row['germplasm_name']}" for _, row in flagged.iterrows()}
        chosen_outliers = st.multiselect("Parcelas sinalizadas a excluir do ajuste", list(row_labels),
            default=list(row_labels), format_func=lambda key: row_labels[key],
            key=f"outliers_{analysis['fit_id']}_{threshold}",
            help="Exclusão por linha, não por plot_id. Limpar a seleção não exclui nenhuma parcela.")
        st.caption("O botão refaz uma única vez o mesmo modelo salvo (resposta, BLUE/BLUP e efeitos), "
                   "sem as parcelas selecionadas. Não altera o Excel nem a Base filtrada. "
                   "Novos candidatos após o ajuste exigem outra revisão; não há remoção automática em sequência.")
        refit_column, restore_column = st.columns(2)
        if refit_column.button("Recalcular modelo removendo outliers", type="primary",
                               disabled=not chosen_outliers, width="stretch"):
            with st.spinner("Recalculando o modelo sem as parcelas selecionadas…"):
                try:
                    new_fit = refit_without_outliers(st.session_state["df"], analysis, chosen_outliers, threshold)
                    st.session_state.setdefault("analysis_before_exclusions", analysis)
                    st.session_state["analysis"] = new_fit
                    st.rerun()
                except Exception as exc:
                    st.error(f"Não foi possível recalcular: {exc}. O ajuste anterior foi mantido.")
        if restore_column.button("Restaurar ajuste sem exclusões", width="stretch",
                                 disabled="analysis_before_exclusions" not in st.session_state):
            st.session_state["analysis"] = st.session_state.pop("analysis_before_exclusions")
            st.rerun()
        if analysis.get("excluded_rows"):
            baseline = st.session_state.get("analysis_before_exclusions")
            if baseline is not None:
                st.dataframe(pd.DataFrame({"Ajuste": ["Antes das exclusões", "Atual"],
                    "Parcelas utilizadas": [baseline["nobs"], analysis["nobs"]],
                    "Variância residual": [float(baseline["result"].scale), float(analysis["result"].scale)]}),
                    hide_index=True, width="stretch")
            with st.expander("Histórico das parcelas excluídas", expanded=True):
                audit = analysis["exclusion_audit"].rename(columns=display_names)
                st.dataframe(audit, hide_index=True, width="stretch")
                st.download_button("Baixar histórico de exclusões", audit.to_csv(index=False),
                                   "exclusoes_outliers.csv", "text/csv")
            st.caption("As exclusões pertencem ao ajuste atual e não são salvas no JSON de filtros. "
                       "Mudar o datacut invalida o ajuste e suas exclusões.")
        with st.expander("Diagnóstico completo por parcela"):
            diagnostic_export = diagnostic.rename(columns=display_names)
            st.dataframe(diagnostic_export, hide_index=True, width="stretch")
            st.download_button("Baixar diagnóstico CSV", diagnostic_export.to_csv(index=False),
                               "diagnostico_parcelas.csv", "text/csv")
        st.dataframe(analysis["fixed_coefficients"], width="stretch", hide_index=True)


with cycle_page:
    render_page_intro("Ciclo dos materiais", "Produtividade × dias ao espigamento",
                      "Um ponto por genótipo, vinculado ao cadastro auxiliar pelo gid.")
    cycle_source = st.radio("Valores do gráfico de ciclo", ["Estimados (BLUE / BLUP)", "Dados brutos"],
                            horizontal=True, key="cycle_value_source")
    cycle_fit = st.session_state.get("analysis") if cycle_source.startswith("Estimados") else None
    if st.session_state.get("analysis", {}).get("excluded_rows"):
        st.caption("Estimados usam o ajuste após as exclusões do diagnóstico. Dados brutos preservam "
                   "o datacut completo, incluindo as parcelas excluídas apenas do modelo.")
    cycle_ready = cycle_source == "Dados brutos" or (
        cycle_fit is not None and cycle_fit["response"] == "yield"
        and cycle_fit["signature"] == current_signature)
    if not cycle_ready:
        st.info("Calcule BLUE ou BLUP para yield no datacut atual ou escolha Dados brutos.")
    else:
        try:
            cycle_points, excluded_cycle = cycle_data(st.session_state["df"], available_materials, cycle_fit)
        except ValueError as exc:
            st.info(str(exc))
        else:
            if excluded_cycle:
                st.warning(f"{excluded_cycle} genótipo(s) sem dias ao espigamento válidos ou com vínculo gid ambíguo "
                           "foram omitidos deste gráfico. A base e o ajuste não foram alterados.")
            if cycle_points.empty:
                st.info("Não há materiais com dias ao espigamento válidos neste recorte.")
            else:
                cycle_options = sorted(cycle_points["germplasm_name"].unique())
                cycle_key = f"cycle_genotypes_{source_id}"
                if cycle_key not in st.session_state:
                    st.session_state[cycle_key] = cycle_options
                else:
                    st.session_state[cycle_key] = [g for g in st.session_state[cycle_key] if g in cycle_options]
                if st.button("Incluir todos no gráfico de ciclo"):
                    st.session_state[cycle_key] = cycle_options
                included_cycle = st.multiselect("Genótipos no gráfico de ciclo", cycle_options, key=cycle_key,
                    help="Altera somente este gráfico e sua regressão, sem mudar o cenário ou recalcular o modelo. Limpar remove todos.")
                cycle_plot = cycle_points.loc[cycle_points["germplasm_name"].isin(included_cycle)]
                if cycle_plot.empty:
                    st.info("Inclua pelo menos um genótipo para exibir o gráfico.")
                else:
                    cycle_label = f"Produtividade estimada · {cycle_fit['method']}" if cycle_fit else "Produtividade média bruta"
                    label_points = st.checkbox("Exibir nomes dos genótipos", value=False, key="cycle_show_names")
                    cycle_fig = px.scatter(cycle_plot, x="days_to_spike", y="Estimativa", color="Categoria",
                        symbol="Categoria", hover_name="germplasm_name",
                        hover_data={"gid": True, "n": True, "Ensaios": True,
                                    "days_to_spike": ":.1f", "Estimativa": ":.1f"},
                        text="germplasm_name" if label_points else None,
                        color_discrete_map={"Check": GDM_NAVY, "Comercial": GDM_LIME,
                                            "Experimental": GDM_CORAL, "Não informada": GDM_GRAY},
                        labels={"days_to_spike": "Dias ao espigamento · aba auxiliar", "Estimativa": cycle_label,
                                "n": "Parcelas", "Ensaios": "Ensaios"},
                        title="Produtividade e ciclo dos genótipos")
                    cycle_fig.update_traces(marker_size=11, textposition="top center")
                    regression = reference_regression(cycle_plot)
                    if regression is not None:
                        line_x = np.array([regression["xmin"], regression["xmax"]])
                        cycle_fig.add_trace(go.Scatter(x=line_x,
                            y=regression["intercept"] + regression["slope"] * line_x,
                            mode="lines", name="Regressão · checks + comerciais",
                            line=dict(color=GDM_NAVY, width=2, dash="dash")))
                    cycle_span = cycle_plot["Estimativa"].max() - cycle_plot["Estimativa"].min()
                    cycle_padding = max(1., .08 * cycle_span)
                    cycle_fig.update_layout(height=580)
                    cycle_fig.update_yaxes(tickformat=",.1f", range=[
                        cycle_plot["Estimativa"].min() - cycle_padding,
                        cycle_plot["Estimativa"].max() + cycle_padding])
                    show_plot(cycle_fig)
                    if regression is not None:
                        r2 = format_decimal(regression["r2"], 3) if np.isfinite(regression["r2"]) else "não definido (resposta constante)"
                        st.caption(f"Regressão conjunta dos checks e comerciais incluídos: "
                                   f"y = {regression['intercept']:.2f} + ({regression['slope']:.2f}) × dias. "
                                   f"R² = {r2} · n = {regression['n']} genótipos. "
                                   "Peso igual por genótipo; a linha fica no intervalo observado das referências.")
                    else:
                        st.info("A regressão exige pelo menos dois checks/comerciais incluídos, "
                                "com dias ao espigamento distintos.")
                    st.caption("Estimados: média ajustada/predita geral do genótipo, não apenas o desvio BLUP. "
                               "Brutos: média das produtividades por ensaio, com peso igual aos ensaios observados. "
                               "O ciclo vem exclusivamente de days_to_spike da aba auxiliar, não de cycle.")
                    st.download_button("Baixar dados do gráfico de ciclo", cycle_plot.to_csv(index=False),
                                       "produtividade_por_ciclo.csv", "text/csv")
