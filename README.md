# GDM Wheat Phenotypic Analysis

Aplicativo em Streamlit para exploração de dados fenotípicos de trigo, comparação head-to-head de genótipos e ajuste de modelos mistos com `statsmodels`.

O aplicativo inicia com dados sintéticos, mas aceita arquivos Excel (`.xlsx`) enviados pelo usuário. Não há conexão com Databricks nem credenciais no repositório.

## Importar dados

Use **Arquivo Excel** na aba **Cenários / Datacut**. A primeira aba da planilha contém as observações e precisa ter:

- `trial_id`: identificador único do ensaio;
- `trial_name`: nome do ensaio;
- `location_name`: local do ensaio;
- `germplasm_name`: genótipo;
- `yield`: produtividade numérica.

O app usa `trial_name | location_name` como unidade analítica de ensaio nos
filtros, tabelas, gráficos e comparações. O `trial_id` permanece como referência
técnica, e a importação valida que cada ID corresponda a uma única combinação de
nome e local.

Quando houver uma segunda aba, ela será usada como cadastro de materiais e precisa conter `gid`. A coluna `gid` da segunda aba é vinculada à coluna `gid` da primeira. Os filtros de materiais incluem categoria, ciclo e demais atributos disponíveis; os genótipos são exibidos pelo `germplasm_name`. Materiais sem observações na primeira aba não aparecem como opções de análise. Sem seleção individual, todos os materiais do recorte são incluídos.

O botão **Baixar template Excel** fornece os 72 cabeçalhos do arquivo de referência. O índice ambiental compara dois genótipos apenas nas combinações `trial_name | location_name` em que ambos foram avaliados.

Todos os controles ficam em **Cenários / Datacut**, em três blocos: cenário/materiais, datacut dos ensaios, e demais variáveis/qualidade. Os filtros são aplicados imediatamente e funcionam em cascata. Valores ausentes aparecem como **(Nulo)**. Quando disponíveis, o recorte começa com `plot_is_discarded = False` e `missing_dev_file = no`. Limpar um filtro inclui todas as suas opções. As abas preservam as seleções ao navegar.

Na visão geral, o gráfico de médias por ensaio ocupa a largura da página, abaixo da distribuição de produtividade, com rolagem vertical para ler todas as barras.

## Salvar e abrir cenários

**Salvar cenário + datacut (JSON)** baixa o nome, os filtros de materiais, GIDs, datacut e demais filtros/qualidade. O arquivo não contém observações nem um modelo ajustado. Para restaurar, carregue a planilha e use **Abrir cenário e datacut (JSON)**. A versão 2 separa `material_attributes`, `selected_gids`, `datacut` e `additional`; arquivos da versão 1 continuam aceitos. Abrir um cenário substitui as seleções anteriores. Se a base mudou, somente opções presentes são aplicadas.

## BLUE, BLUP e índice ambiental

Em **Modelo · BLUE / BLUP**, escolha a variável resposta e o efeito do genótipo:

- **Fixo → BLUE**: médias ajustadas para os efeitos fixos escolhidos, estimadas por GLS/REML quando há efeitos aleatórios, ou OLS quando todos os efeitos são fixos.
- **Aleatório → BLUP**: produtividade predita e efeito genotípico aleatório (desvio) apresentados separadamente.

Inclua **Ensaio | Local** como efeito fixo ou aleatório. Os fatores aleatórios são cruzados; não são aninhados automaticamente no primeiro fator. Para representar blocos/repetições dentro de ensaios, use uma coluna que combine ensaio e repetição. É possível incluir a interação genótipo × ensaio como componente aleatório; ela requer repetições. Sem interação, o modelo é aditivo.

As estimativas gerais de genótipo dão peso igual aos ensaios, usando a mesma distribuição dos demais efeitos fixos para todos os genótipos. Nas predições por ensaio, os efeitos fixos adicionais são padronizados pela média da matriz de delineamento dentro de cada ensaio. Somam-se os efeitos aleatórios estimados de genótipo, ensaio e interação, quando presentes. Outros efeitos aleatórios, como blocos, são fixados em zero para essa comparação. Só são exportadas predições de combinações genótipo × ensaio observadas no ajuste.

O índice ambiental inicia em **Preditos (BLUE / BLUP)** e exige um ajuste para `yield` com o datacut atual. **Dados brutos** permite consultar médias de parcelas sem ajustar. Em ambos os modos, o eixo X usa a média dos genótipos presentes no ensaio, com peso igual por genótipo; o eixo Y usa a predição ou a média bruta do genótipo. As médias dos cards dão peso igual aos ensaios comuns. Mudar a base ou o recorte invalida as predições anteriores.

Registros com valores ausentes/não finitos nas variáveis do modelo são omitidos com contagem explícita. Modelos sem convergência, com efeitos fixos confundidos ou sem graus de liberdade são recusados. A herdabilidade não é inferida a partir da variância de um fator arbitrário.

Referência técnica: [componentes de variância e fatores cruzados no statsmodels](https://www.statsmodels.org/stable/examples/notebooks/generated/variance_components.html).

## Verificar alterações

```bash
python -X utf8 -m unittest test_analysis test_app -v
```

Os testes verificam BLUE contra OLS independente, redução dos efeitos BLUP, predições contra modelo denso, cenários v1/v2, filtros e invalidação de predições.

## Executar localmente

Requer Python 3.12.

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Publicar

Envie os arquivos do projeto ao GitHub, incluindo **app.py e analysis.py** (ambos obrigatórios), `requirements.txt`, `.streamlit/config.toml` e o template. No Streamlit Community Cloud, escolha:

- repositório: este projeto;
- branch: a branch principal;
- arquivo principal: `app.py`.
