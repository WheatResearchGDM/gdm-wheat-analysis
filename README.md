# GDM Wheat Phenotypic Analysis

Aplicativo em Streamlit para exploração de dados fenotípicos de trigo, comparação head-to-head de genótipos e ajuste de modelos mistos com `statsmodels`.

O aplicativo inicia com dados sintéticos, mas aceita arquivos Excel (`.xlsx`) enviados pelo usuário. Não há conexão com Databricks nem credenciais no repositório.

## Importar dados

Use **Arquivo Excel** na barra lateral. A primeira aba da planilha será importada e precisa conter:

- `trial_name`: ambiente ou ensaio;
- `germplasm_name`: genótipo;
- `yield`: produtividade numérica.

O botão **Baixar template Excel** fornece os 72 cabeçalhos do arquivo de referência. O índice ambiental compara dois genótipos apenas nos `trial_name` em que ambos foram avaliados. A média ambiental no eixo X considera todos os genótipos do datacut; o eixo Y mostra a produtividade média de cada genótipo selecionado.

Os filtros ficam na barra lateral e funcionam em cascata: cada seleção limita as opções disponíveis nos filtros seguintes. Valores ausentes aparecem como **(Nulo)**. Quando os campos estão disponíveis, o datacut começa com `plot_is_discarded = False` e `missing_dev_file = no`; basta limpar essas seleções para incluir todas as categorias.

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
