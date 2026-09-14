# GDM Wheat Phenotypic Analysis

Aplicativo em Streamlit para exploração de dados fenotípicos de trigo, comparação head-to-head de genótipos e ajuste de modelos mistos com `statsmodels`.

O aplicativo inicia com dados sintéticos, mas aceita arquivos Excel (`.xlsx`) enviados pelo usuário. Não há conexão com Databricks nem credenciais no repositório.

## Importar dados

Use **Arquivo Excel** na barra lateral. A primeira aba da planilha contém as observações e precisa ter:

- `trial_name`: ambiente ou ensaio;
- `germplasm_name`: genótipo;
- `yield`: produtividade numérica.

Quando houver uma segunda aba, ela será usada como cadastro de materiais e precisa conter `gid`. A coluna `gid` da segunda aba é vinculada à coluna `gid` da primeira. Na página **Cenário**, os genótipos são organizados por categoria ou ciclo, mas exibidos apenas pelo `germplasm_name` encontrado na primeira aba. Materiais sem observações na primeira aba são informados e não aparecem como opções de análise.

O botão **Baixar template Excel** fornece os 72 cabeçalhos do arquivo de referência. O índice ambiental compara dois genótipos apenas nos `trial_name` em que ambos foram avaliados. A média ambiental no eixo X considera todos os genótipos do datacut; o eixo Y mostra a produtividade média de cada genótipo selecionado.

Os filtros ficam na barra lateral e funcionam em cascata: cada seleção limita as opções disponíveis nos filtros seguintes. Valores ausentes aparecem como **(Nulo)**. Quando os campos estão disponíveis, o datacut começa com `plot_is_discarded = False` e `missing_dev_file = no`; basta limpar essas seleções para incluir todas as categorias.

## Salvar e abrir cenários

O botão **Salvar cenário (JSON)** baixa um arquivo com o nome do cenário, os GIDs e filtros selecionados, sem incluir os dados da planilha. Para recuperar o datacut, carregue a base e depois use **Arquivo de cenário**. Se o JSON tiver sido criado com outra base, apenas os valores existentes serão aplicados.

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
