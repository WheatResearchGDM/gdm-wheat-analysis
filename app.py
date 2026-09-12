"""GDM Wheat Phenotypic Analysis - Mixed Models (Streamlit + statsmodels)
Versao com dados demonstrativos embutidos (sem dependencia de SQL Warehouse).
"""

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

FULL_DATA = generate_sample_data()

CATEGORICAL_COLS = [
    "data_source", "trial_type", "trial_name", "pipeline_file",
    "condition_file", "signed_status", "location_name",
    "state_name", "country_name", "macroregion_name", "microregion_name",
    "germplasm_name", "gid", "company_name", "area",
]


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------
def distinct_values(column: str):
    if column not in FULL_DATA.columns:
        return []
    return sorted(FULL_DATA[column].dropna().astype(str).unique().tolist())


def load_data(filters: dict) -> pd.DataFrame:
    df = FULL_DATA.copy()
    for col, vals in filters.items():
        if vals and col in df.columns:
            df = df[df[col].astype(str).isin([str(v) for v in vals])]
    return df


def format_integer(value) -> str:
    """Format dashboard counts using Brazilian thousands separators."""
    if isinstance(value, (int, np.integer)):
        return f"{int(value):,}".replace(",", ".")
    return str(value)


def render_metric(container, icon: str, label: str, value, detail: str):
    container.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-card__top">
                <span class="metric-card__label">{label}</span>
                <span class="metric-card__icon">{icon}</span>
            </div>
            <div class="metric-card__value">{format_integer(value)}</div>
            <div class="metric-card__detail">{detail}</div>
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
    "Modelo Misto": "◈  Modelo misto",
    "Resultados": "↗  Resultados",
    "Diagnosticos": "⌁  Diagnósticos",
}
page = st.sidebar.radio(
    "Navegação",
    list(nav_labels),
    format_func=nav_labels.get,
    label_visibility="collapsed",
)
st.sidebar.markdown(
    """
    <div class="sidebar-section">
        <span>Filtros</span>
        <strong>Segmentação dos dados</strong>
    </div>
    """,
    unsafe_allow_html=True,
)

filters: dict = {}

years = distinct_values("year")
sel = st.sidebar.multiselect("Ano", years)
if sel:
    filters["year"] = sel

types = distinct_values("trial_type")
sel = st.sidebar.multiselect("Tipo Ensaio", types)
if sel:
    filters["trial_type"] = sel

signed = distinct_values("signed_status")
sel = st.sidebar.multiselect("Status", signed)
if sel:
    filters["signed_status"] = sel

with st.sidebar.expander("Localizacao"):
    for lc in ["country_name", "macroregion_name", "microregion_name",
               "state_name", "location_name"]:
        v = distinct_values(lc)
        s = st.multiselect(lc, v, key=f"f_{lc}")
        if s:
            filters[lc] = s

with st.sidebar.expander("Material Genetico"):
    for mc in ["germplasm_name", "gid"]:
        v = distinct_values(mc)
        s = st.multiselect(mc, v, key=f"f_{mc}")
        if s:
            filters[mc] = s

with st.sidebar.expander("Outros"):
    shown = set(filters.keys()) | {"year", "trial_type", "signed_status",
        "country_name", "macroregion_name", "microregion_name",
        "state_name", "location_name", "germplasm_name", "gid"}
    for oc in [c for c in CATEGORICAL_COLS if c not in shown]:
        v = distinct_values(oc)
        s = st.multiselect(oc, v, key=f"f_{oc}")
        if s:
            filters[oc] = s

if st.sidebar.button("Carregar Dados", type="primary", width="stretch"):
    with st.spinner("Filtrando..."):
        st.session_state["df"] = load_data(filters)

# Auto-load on first visit
if "df" not in st.session_state:
    st.session_state["df"] = FULL_DATA.copy()

st.markdown(
    """
    <div class="gdm-hero">
        <div class="gdm-hero__copy">
            <div class="gdm-eyebrow">GDM · Research Analytics</div>
            <h1>Wheat Phenotypic Analysis</h1>
            <p>Explore ensaios, compare germoplasmas e transforme dados fenotípicos em decisões de melhoramento mais claras.</p>
        </div>
        <div class="gdm-hero__badge"><span>● Dados demonstrativos</span></div>
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
