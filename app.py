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
st.set_page_config(page_title="GDM Wheat Analysis", page_icon="\U0001F33E", layout="wide")

st.markdown("""
<style>
section[data-testid="stSidebar"] {background-color: #f0f2f6;}
.block-container {padding-top: 1rem;}
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


# ---------------------------------------------------------------------------
# Sidebar: navigation + filters
# ---------------------------------------------------------------------------
st.sidebar.title("\U0001F33E GDM Wheat Analysis")
st.sidebar.caption("Dados demonstrativos")
page = st.sidebar.radio("Navegacao", ["Dados", "Modelo Misto", "Resultados", "Diagnosticos"])
st.sidebar.markdown("---")
st.sidebar.subheader("Filtros de Dados")

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

# ---------------------------------------------------------------------------
# Page: Dados
# ---------------------------------------------------------------------------
if page == "Dados":
    st.header("Dados Fenotipicos - Trigo")
    df = st.session_state["df"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Registros", f"{len(df):,}")
    c2.metric("Colunas", len(df.columns))
    c3.metric("Ensaios", df["trial_name"].nunique() if "trial_name" in df.columns else "-")
    c4.metric("Genotipos", df["germplasm_name"].nunique() if "germplasm_name" in df.columns else "-")
    st.dataframe(df, width="stretch", height=500)
    with st.expander("Estatisticas Descritivas"):
        num = df.select_dtypes(include=[np.number]).columns.tolist()
        if num:
            st.dataframe(df[num].describe().round(3), width="stretch")
    st.download_button("Download CSV", df.to_csv(index=False), "wheat_data.csv", "text/csv")

# ---------------------------------------------------------------------------
# Page: Modelo Misto
# ---------------------------------------------------------------------------
elif page == "Modelo Misto":
    st.header("Especificacao do Modelo Misto")
    if "df" not in st.session_state or st.session_state["df"].empty:
        st.warning("Carregue os dados primeiro na aba **Dados**.")
    else:
        df = st.session_state["df"].copy()
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = df.select_dtypes(include=["object", "string", "category"]).columns.tolist()
        all_cols = num_cols + cat_cols

        st.subheader("Variavel Resposta")
        response = st.selectbox("Variavel dependente (numerica)", num_cols,
                                index=num_cols.index("yield") if "yield" in num_cols else 0)

        st.subheader("Efeitos Fixos")
        fixed = st.multiselect("Selecione efeitos fixos",
                               [c for c in all_cols if c != response],
                               help="Variaveis categoricas sao tratadas como fatores (C()).")

        st.subheader("Efeitos Aleatorios")
        st.caption("O primeiro sera o agrupamento principal (groups). Demais entram como componentes de variancia adicionais.")
        random_eff = st.multiselect("Selecione efeitos aleatorios",
                                    [c for c in cat_cols if c != response and c not in fixed],
                                    help="Ex: germplasm_name, trial_name")

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
    st.header("Resultados do Modelo Misto")
    if "mres" not in st.session_state:
        st.warning("Ajuste um modelo primeiro.")
    else:
        res = st.session_state["mres"]
        dm = st.session_state["mdata"]
        resp = st.session_state["mresp"]
        primary = st.session_state["mprimary"]
        randoms = st.session_state["mrandom"]

        t1, t2, t3, t4, t5 = st.tabs(
            ["Resumo", "Variancia", "BLUPs", "Herdabilidade", "Ranking"]
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
            fig = px.pie(vdf, values="Variancia", names="Componente",
                         title="Proporcao dos Componentes de Variancia")
            st.plotly_chart(fig, width="stretch")

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
            fig = px.histogram(bdf, x="BLUP", nbins=30,
                               title=f"Distribuicao BLUPs ({primary})")
            st.plotly_chart(fig, width="stretch")
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
                         title=f"Top {ntop} - Valor Predito ({resp})",
                         color="BLUP", color_continuous_scale="RdYlGn")
            fig.update_layout(xaxis_tickangle=-45, height=600)
            st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------------------
# Page: Diagnosticos
# ---------------------------------------------------------------------------
elif page == "Diagnosticos":
    st.header("Diagnosticos do Modelo")
    if "mres" not in st.session_state:
        st.warning("Ajuste um modelo primeiro.")
    else:
        res = st.session_state["mres"]
        residuals = res.resid
        fitted = res.fittedvalues

        dt1, dt2, dt3 = st.tabs(["Residuos", "Wald Test", "Efeitos Fixos"])

        with dt1:
            c1, c2 = st.columns(2)
            with c1:
                fig = px.scatter(x=fitted, y=residuals, opacity=0.4,
                                 labels={"x": "Ajustados", "y": "Residuos"},
                                 title="Residuos vs Ajustados")
                fig.add_hline(y=0, line_dash="dash", line_color="red")
                st.plotly_chart(fig, width="stretch")
            with c2:
                sr = np.sort(residuals)
                n = len(sr)
                tq = stats.norm.ppf(np.arange(1, n + 1) / (n + 1))
                fig = px.scatter(x=tq, y=sr,
                                 labels={"x": "Quantis Teoricos", "y": "Quantis Amostrais"},
                                 title="QQ Plot")
                mn, mx = min(tq.min(), sr.min()), max(tq.max(), sr.max())
                fig.add_trace(go.Scatter(x=[mn, mx], y=[mn, mx],
                              mode="lines", line=dict(color="red", dash="dash"),
                              showlegend=False))
                st.plotly_chart(fig, width="stretch")

            c3, c4 = st.columns(2)
            with c3:
                fig = px.histogram(x=residuals, nbins=40, title="Histograma Residuos",
                                   labels={"x": "Residuos"})
                st.plotly_chart(fig, width="stretch")
            with c4:
                fig = px.scatter(x=fitted, y=np.sqrt(np.abs(residuals)), opacity=0.4,
                                 labels={"x": "Ajustados", "y": "sqrt|Residuos|"},
                                 title="Scale-Location")
                st.plotly_chart(fig, width="stretch")

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
                    marker=dict(size=8, color="#1f77b4"),
                    error_x=dict(type="data", symmetric=False,
                                 array=(fe_df["hi"] - fe_df["Est"]).tolist(),
                                 arrayminus=(fe_df["Est"] - fe_df["lo"]).tolist()),
                    name="IC 95%"))
                fig.add_vline(x=0, line_dash="dash", line_color="red")
                fig.update_layout(height=max(350, len(fe_df) * 30))
                st.plotly_chart(fig, width="stretch")
