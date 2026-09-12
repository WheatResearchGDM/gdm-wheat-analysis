# GDM Wheat Phenotypic Analysis

Aplicativo demonstrativo em Streamlit para exploração de dados fenotípicos de trigo e ajuste de modelos mistos com `statsmodels`.

Os dados atuais são inteiramente sintéticos e gerados pelo próprio aplicativo. Não há conexão com Databricks nem credenciais no repositório.

## Executar localmente

Requer Python 3.12.

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Publicar

Envie este repositório ao GitHub e, no Streamlit Community Cloud, escolha:

- repositório: este projeto;
- branch: a branch principal;
- arquivo principal: `app.py`.
