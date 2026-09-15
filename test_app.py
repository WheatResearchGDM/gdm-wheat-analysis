"""UI regression: live datacut, portable scenarios and prediction invalidation."""
import json
from pathlib import Path
import unittest

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
        self.assertEqual(multiselect(app, "Parcela descartada").value, ["False"])
        self.assertEqual(multiselect(app, "Missing no arquivo DEV").value, ["no"])
        app.text_input[0].set_value("Cenário teste").run()
        multiselect(app, "Ano").set_value(["23"]).run()
        multiselect(app, "Microrregião").set_value(["MR1"]).run()
        multiselect(app, "Parcela descartada").set_value([]).run()
        multiselect(app, "Missing no arquivo DEV").set_value(["no", "(Nulo)"]).run()
        # Widget options are readable names; stored values are GIDs.
        multiselect(app, "Genótipos incluídos").set_value(["G1000", "G1001"]).run()
        saved = json.loads(json.dumps(app.session_state["test_export"]))
        expected_rows = app.session_state["df"].index.tolist()
        self.assertEqual(saved["filters"]["datacut"]["year"], ["23"])
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
        next(r for r in app.radio if r.label == "Efeito de genótipo").set_value("Fixo → BLUE").run()
        app.checkbox[0].uncheck().run()
        next(b for b in app.button if b.label == "Calcular BLUE").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["analysis"]["method"], "BLUE")
        self.assertEqual(len(app.error), 0)
        self.assertEqual(len(app.get("plotly_chart")), 10)
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
                        "Dias ao espigamento", "Dias à maturidade", "País", "Estado", "Local"]:
            self.assertNotIn(removed, labels)
        self.assertIn("Ensaio | Local", labels)
        base = next(table.value for table in app.dataframe if "trial_unit_label" in table.value.columns)
        self.assertEqual(base.columns[0], "trial_unit_label")
        next(r for r in app.radio if r.label == "Valores do gráfico de ciclo").set_value("Dados brutos").run()
        self.assertEqual(len(app.exception), 0)
        self.assertGreater(len(multiselect(app, "Genótipos no gráfico de ciclo").value), 0)
        multiselect(app, "Genótipos no gráfico de ciclo").set_value([]).run()
        self.assertEqual(len(app.exception), 0)
        next(b for b in app.button if b.label == "Incluir todos no gráfico de ciclo").click().run()
        self.assertGreater(len(multiselect(app, "Genótipos no gráfico de ciclo").value), 0)


if __name__ == "__main__":
    unittest.main()
