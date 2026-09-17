"""UI regression: live datacut, portable scenarios and prediction invalidation."""
import json
from pathlib import Path
import unittest
import pandas as pd

from streamlit.testing.v1 import AppTest


def multiselect(app, label):
    return next(w for w in app.multiselect if w.label == label)


class DatacutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
        # Exercise the same importer callback without automating an OS picker.
        cls.source = source + '''
st.session_state["test_export"] = scenario
if "test_saved" in st.session_state:
    st.button("Test restore", on_click=load_scenario_into_state,
              args=(st.session_state["test_saved"], source_id))
'''

    def test_datacut_roundtrip_and_legacy_json(self):
        app = AppTest.from_string(self.source, default_timeout=45).run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.sidebar), 0)
        self.assertEqual(multiselect(app, "Parcela descartada SEEDS").value, ["False"])
        self.assertEqual(multiselect(app, "Parcela descartada DEV").value, ["no", "(Nulo)"])
        app.text_input[0].set_value("Cenário teste").run()
        multiselect(app, "Ano").set_value(["23"]).run()
        multiselect(app, "Microrregião").set_value(["MR1"]).run()
        multiselect(app, "Parcela descartada SEEDS").set_value([]).run()
        multiselect(app, "Parcela descartada DEV").set_value(["no", "(Nulo)"]).run()
        # Grouped widgets show readable names while retaining GIDs as values.
        multiselect(app, "Selecionar comerciais").set_value([]).run()
        multiselect(app, "Selecionar checks").set_value([]).run()
        multiselect(app, "Selecionar experimentais").set_value(["G1000", "G1001"]).run()
        saved = json.loads(json.dumps(app.session_state["test_export"]))
        expected_rows = app.session_state["df"].index.tolist()
        self.assertEqual(saved["filters"]["datacut"]["year"], ["23"])
        self.assertIn("pipeline_file", saved["filters"]["datacut"])
        self.assertIn("cycle_file", saved["filters"]["datacut"])
        self.assertNotIn("condition_file", saved["filters"]["datacut"])
        self.assertEqual(saved["filters"]["additional"]["missing_dev_file"], ["no", "(Nulo)"])
        app.session_state["test_saved"] = saved
        multiselect(app, "Ano").set_value(["24"]).run()
        next(b for b in app.button if b.label == "Test restore").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["df"].index.tolist(), expected_rows)
        self.assertEqual(app.text_input[0].value, "Cenário teste")
        self.assertEqual(app.session_state["test_export"]["filters"], saved["filters"])
        legacy = dict(saved, version=1)
        legacy["filters"] = {
            "selected_gids": [], "material_attributes": {},
            "observations": {"year": ["25"], "plot_is_discarded": [], "missing_dev_file": []},
        }
        app.session_state["test_saved"] = legacy
        app.run()
        next(b for b in app.button if b.label == "Test restore").click().run()
        self.assertEqual(multiselect(app, "Ano").value, ["25"])
        self.assertEqual(multiselect(app, "Microrregião").value, [])
        self.assertEqual(len(app.exception), 0)

    def test_blue_ui_and_stale_predictions(self):
        app = AppTest.from_file("app.py", default_timeout=60).run()
        next(r for r in app.radio if r.label == "Estrutura do modelo").set_value("Personalizado").run()
        next(r for r in app.radio if r.label == "Efeito de genótipo").set_value("Fixo → BLUE").run()
        app.checkbox[0].uncheck().run()
        next(b for b in app.button if b.label == "Calcular BLUE").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["analysis"]["method"], "BLUE")
        self.assertEqual(len(app.error), 0)
        self.assertEqual(len(app.get("plotly_chart")), 12)
        self.assertEqual(len(app.latex), 1)
        self.assertIn("n", app.session_state["analysis"]["genotypes"])
        next(r for r in app.radio if r.label == "Valores do gráfico de ciclo").set_value("Dados brutos").run()
        multiselect(app, "Genótipos no gráfico de ciclo").set_value([]).run()
        self.assertEqual(len(app.exception), 0)
        multiselect(app, "Ano").set_value(["23"]).run()
        self.assertNotIn("analysis", app.session_state)
        self.assertTrue(app.session_state["analysis_invalidated"])
        next(r for r in app.radio if r.label == "Valores do índice ambiental").set_value("Dados brutos").run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.get("plotly_chart")), 4)

    def test_simplified_filters_and_cycle_controls(self):
        app = AppTest.from_file("app.py", default_timeout=45).run()
        labels = [w.label for w in app.multiselect]
        for removed in ["Região comercial", "Nome de produção", "Nome comercial", "Tipo de elemento",
                        "Dias ao espigamento", "Dias à maturidade", "País", "Estado", "Local", "Status"]:
            self.assertNotIn(removed, labels)
        self.assertIn("Ano | Ensaio | Local / Ambiente DEV", labels)
        self.assertIn("Pipeline", labels)
        self.assertIn("Ciclo", labels)
        self.assertNotIn("Condição", labels)
        genotype_mode = next(r for r in app.radio if r.label == "Selecionar genótipos por:")
        self.assertEqual(genotype_mode.value, "Categoria")
        model_structure = next(r for r in app.radio if r.label == "Estrutura do modelo")
        self.assertEqual(model_structure.value, "Seleção multiambiente (recomendada)")
        for group_label in ["Selecionar comerciais", "Selecionar checks", "Selecionar experimentais"]:
            self.assertIn(group_label, labels)
        genotype_mode.set_value("Ciclo").run()
        self.assertIn("Ciclo · Não informado", [w.label for w in app.multiselect])
        self.assertEqual([tab.label for tab in app.tabs[:7]], [
            "◎ Cenários / Datacut", "▦ Visão geral", "⌘ Conectividade",
            "◈ Modelo · BLUE / BLUP", "⌁ Diagnósticos", "↗ Resultados",
            "◉ Análises",
        ])
        tab_labels = [tab.label for tab in app.tabs]
        analysis_tabs = [
            "⇄ Índice ambiental", "◷ Produtividade × ciclo",
            "◉ Produtividade × proteína", "◆ Seleção",
        ]
        analysis_positions = [tab_labels.index(label) for label in analysis_tabs]
        self.assertEqual(analysis_positions, sorted(analysis_positions))
        base = next(table.value for table in app.dataframe if "trial_unit_label" in table.value.columns)
        self.assertEqual(base.columns[0], "trial_unit_label")
        next(r for r in app.radio if r.label == "Valores do gráfico de ciclo").set_value("Dados brutos").run()
        self.assertEqual(len(app.exception), 0)
        self.assertGreater(len(multiselect(app, "Genótipos no gráfico de ciclo").value), 0)

        multiselect(app, "Genótipos no gráfico de ciclo").set_value([]).run()
        self.assertEqual(len(app.exception), 0)
        next(b for b in app.button if b.label == "Incluir todos no gráfico de ciclo").click().run()
        self.assertGreater(len(multiselect(app, "Genótipos no gráfico de ciclo").value), 0)

        next(r for r in app.radio if r.label == "Valores de produtividade no gráfico de proteína").set_value(
            "Dados brutos"
        ).run()
        protein_threshold = next(n for n in app.number_input if n.label == "Threshold de proteína")
        self.assertEqual(protein_threshold.value, 14.0)
        self.assertNotIn("Exibir reta de regressão", [c.label for c in app.checkbox])
        self.assertGreater(len(multiselect(app, "Genótipos no gráfico de proteína").value), 0)
        protein_threshold.set_value(15.0).run()
        self.assertEqual(
            next(n for n in app.number_input if n.label == "Threshold de proteína").value,
            15.0,
        )
        self.assertEqual(len(app.exception), 0)
        next(r for r in app.radio if r.label == "Valores do gráfico de seleção").set_value(
            "Dados brutos"
        ).run()
        check_mean_toggle = next(c for c in app.checkbox if c.label == "Exibir média das testemunhas")
        self.assertTrue(check_mean_toggle.value)
        check_mean_toggle.uncheck().run()
        self.assertFalse(next(
            c for c in app.checkbox if c.label == "Exibir média das testemunhas"
        ).value)
        self.assertGreater(len(multiselect(app, "Genótipos no gráfico de seleção").value), 0)
        connectivity = next(
            table.value for table in app.dataframe
            if table.value.index.name == "Ano | Ensaio | Local / Ambiente DEV"
        )
        self.assertEqual(connectivity.shape[0], connectivity.shape[1])
        self.assertEqual(len(app.exception), 0)

    def test_reporting_module_is_reloaded_after_hot_deploy(self):
        stale_prefix = '''
import reporting as stale_reporting
for stale_name in ["REPORTING_API_VERSION", "genotype_connectivity", "protein_data", "selection_tiers"]:
    if hasattr(stale_reporting, stale_name):
        delattr(stale_reporting, stale_name)
'''
        app = AppTest.from_string(stale_prefix + self.source, default_timeout=45).run()
        self.assertEqual(len(app.exception), 0)
        self.assertIn("⌘ Conectividade", [tab.label for tab in app.tabs])

    def test_refit_and_restore_keep_datacut_intact(self):
        app = AppTest.from_file("app.py", default_timeout=90).run()
        next(r for r in app.radio if r.label == "Estrutura do modelo").set_value("Personalizado").run()
        next(r for r in app.radio if r.label == "Efeito de genótipo").set_value("Fixo → BLUE").run()
        next(c for c in app.checkbox if "interação" in c.label).uncheck().run()
        next(b for b in app.button if b.label == "Calcular BLUE").click().run()
        self.assertEqual(len(app.exception), 0)
        original = app.session_state["analysis"]
        base = app.session_state["df"].copy()
        selected = multiselect(app, "Parcelas sinalizadas a excluir do ajuste").value
        self.assertGreater(len(selected), 0)
        # Editing the current form must not change the specification of a diagnostic refit.
        next(r for r in app.radio if r.label == "Efeito de genótipo").set_value("Aleatório → BLUP").run()
        next(b for b in app.button if b.label == "Recalcular modelo removendo outliers").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 0)
        refit = app.session_state["analysis"]
        self.assertEqual(refit["method"], "BLUE")
        self.assertEqual(refit["nobs"], original["nobs"] - len(selected))
        self.assertEqual(refit["genotypes"]["n"].sum(), refit["nobs"])
        self.assertTrue(app.session_state["df"].equals(base))
        self.assertEqual(len(refit["exclusion_audit"]), len(selected))
        next(b for b in app.button if b.label == "Restaurar ajuste sem exclusões").click().run()
        self.assertEqual(app.session_state["analysis"]["fit_id"], original["fit_id"])
        self.assertNotIn("analysis_before_exclusions", app.session_state)
        self.assertEqual(len(app.exception), 0)
        # Another refit followed by a datacut change clears its undo/audit scope.
        next(b for b in app.button if b.label == "Recalcular modelo removendo outliers").click().run()
        multiselect(app, "Ano").set_value(["23"]).run()
        self.assertNotIn("analysis", app.session_state)
        self.assertNotIn("analysis_before_exclusions", app.session_state)

    def test_old_scenario_trial_selection_is_not_silently_expanded(self):
        source = self.source + '''
st.session_state["test_legacy_rejected"] = False
try:
    load_scenario_into_state({"app": "gdm-wheat-analysis", "version": 2,
        "filters": {"datacut": {"trial_unit_label": ["T | L"]}}},
        source_id, pd.DataFrame({"area": ["Trigo"]}))
except ValueError:
    st.session_state["test_legacy_rejected"] = True
'''
        app = AppTest.from_string(source, default_timeout=45).run()
        self.assertTrue(app.session_state["test_legacy_rejected"])
        self.assertEqual(multiselect(app, "Parcela descartada DEV").value, ["no", "(Nulo)"])
        self.assertEqual(len(app.exception), 0)


if __name__ == "__main__":
    unittest.main()
