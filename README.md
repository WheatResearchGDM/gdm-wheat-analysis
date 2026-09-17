# GDM Wheat Phenotypic Analysis

Aplicativo em Streamlit para exploração de dados fenotípicos de trigo, comparação head-to-head de genótipos e ajuste de modelos mistos com `statsmodels`.

O aplicativo inicia com dados sintéticos, mas aceita arquivos Excel (`.xlsx`) enviados pelo usuário. Não há conexão com Databricks nem credenciais no repositório.

## Importar dados

Use **Arquivo Excel** na aba **Cenários / Datacut**. A primeira aba da planilha contém as observações e precisa ter:

- `trial_id`: identificador de referência da origem;
- `year`: ano do ensaio;
- `trial_name`: nome do ensaio;
- `location_name`: local do ensaio (obrigatório fora de PROD-PLACEMENT);
- `germplasm_name`: genótipo;
- `yield`: produtividade numérica.

Para `area = PROD-PLACEMENT`, a unidade de ensaio é `year | trial_name | environment_dev_file`.
Nas demais áreas (ou sem coluna `area`), é `year | trial_name | location_name`. Essa regra
vale para modelos, interação G×E, contagens, tabelas, gráficos e ensaios comuns.
O campo `year` deve estar preenchido em todas as áreas. Em PROD-PLACEMENT,
`environment_dev_file` e `trial_name` também devem estar preenchidos;
o app não substitui ambiente DEV ausente pelo local. Maiúsculas/minúsculas e espaços
externos em `area` são normalizados. O mesmo `trial_id` pode ter vários ambientes DEV,
e vários IDs com a mesma combinação pertencem ao mesmo ensaio. Fora dessa área,
a validação de um nome/local por ID continua ativa. Rótulos coincidentes entre as
duas regras são desambiguados, sem unir ensaios distintos.

Quando houver uma segunda aba, ela será usada como cadastro de materiais e precisa conter `gid`. A coluna `gid` da segunda aba é vinculada à coluna `gid` da primeira. A seleção de genótipos pode ser organizada por **Categoria** ou **Ciclo**, em listas independentes por grupo; os nomes são exibidos pelo `germplasm_name`, mas o vínculo continua sendo feito pelo GID. Todos os materiais começam selecionados, e Marca permanece disponível como filtro adicional. Materiais sem observações na primeira aba não aparecem como opções de análise. Nome de produção/comercial, região comercial, tipo de elemento e dias de espigamento/maturidade permanecem na fonte, mas não são filtros.

O botão **Baixar template Excel** fornece os 72 cabeçalhos do arquivo de referência, incluindo `environment_dev_file` e identificadores de parcelas. O índice ambiental compara dois genótipos apenas nas unidades de ensaio em que ambos foram avaliados.

Todos os controles ficam em **Cenários / Datacut**, em três blocos: cenário/materiais, datacut dos ensaios, e demais variáveis/qualidade. Os filtros são aplicados imediatamente e funcionam em cascata. O datacut inclui `pipeline_file` como **Pipeline** e `cycle_file` como **Ciclo**; `condition_file` não aparece mais como segmentação. Valores ausentes aparecem como **(Nulo)**. Quando disponíveis, **Parcela descartada SEEDS** começa com `plot_is_discarded = False` e **Parcela descartada DEV** com `missing_dev_file = no` **ou nulo**. O filtro Status foi removido, inclusive de Outras variáveis. Limpar um filtro inclui todas as suas opções. As abas preservam as seleções ao navegar. Defaults valem para novas seleções; um cenário carregado mantém os valores explicitamente salvos.

Na visão geral, o gráfico de médias por ensaio ocupa a largura da página, abaixo da distribuição de produtividade, com rolagem vertical para ler todas as barras.
Os indicadores de quantidade de genótipos usam `gid` como identidade, assim como a seleção de materiais;
nomes textuais repetidos não reduzem artificialmente essa contagem.

A navegação principal permanece no topo durante a rolagem, na ordem: **Cenários / Datacut → Visão geral → Conectividade → Modelo → Diagnósticos → Resultados → Produtividade × ciclo → Produtividade × proteína → Seleção → Índice ambiental**. País, estado e local não aparecem como filtros separados; use **Ano | Ensaio | Local / Ambiente DEV**, que também é a primeira coluna da Base filtrada.

## Conectividade entre ensaios

A aba **Conectividade** apresenta uma matriz ensaio × ensaio. Cada célula conta os `gid` distintos
presentes nos dois ensaios, sem contar repetições de parcela; a diagonal informa o total de genótipos
do próprio ensaio. A matriz pode ser exportada em CSV.

## Salvar e abrir cenários

**Salvar cenário + datacut (JSON)** baixa o nome, o modo de seleção Categoria/Ciclo, os GIDs selecionados, o datacut e os demais filtros/qualidade. O arquivo não contém observações, modelo ou exclusões de outliers. Para restaurar, carregue a planilha e use **Abrir cenário e datacut (JSON)**. A versão 5 registra `trial_unit_rule = area-year-dependent-v2`. Cenários antigos continuam aceitos quando não possuem uma seleção de ensaios; quando possuem, essa seleção precisa ser recriada com o prefixo de ano, sem conversão silenciosa. Status e condição não são reaplicados como segmentações. Abrir um cenário válido substitui as seleções anteriores. Se a base mudou, somente opções presentes são aplicadas.

## BLUE, BLUP e índice ambiental

Em **Modelo · BLUE / BLUP**, a estrutura **Seleção multiambiente (recomendada)** aplica:

- genótipo aleatório para obter BLUP;
- `year` como efeito fixo **categórico**, estimando diferenças entre anos sem impor tendência linear;
- unidade `Ano | Ensaio | Local / Ambiente DEV` como efeito aleatório;
- `num_repetitions` como bloco aleatório aninhado na unidade de ensaio;
- interação genótipo × ensaio aleatória.

O ano é incluído somente quando o datacut contém pelo menos dois anos. O bloco é incluído somente
quando `num_repetitions` identifica mais de uma repetição dentro de pelo menos um ensaio. Valores
iguais de bloco em ensaios distintos são níveis diferentes (por exemplo, `Ensaio A | Bloco 1` e
`Ensaio B | Bloco 1`). Registros sem valor nas variáveis usadas pelo modelo são omitidos e contados.

Em **Personalizado**, escolha a variável resposta e o efeito do genótipo:

- **Fixo → BLUE**: médias ajustadas para os efeitos fixos escolhidos, estimadas por GLS/REML quando há efeitos aleatórios, ou OLS quando todos os efeitos são fixos.
- **Aleatório → BLUP**: produtividade predita e efeito genotípico aleatório (desvio) apresentados separadamente.

Inclua **Ano | Ensaio | Local / Ambiente DEV** como efeito fixo ou aleatório. Ao selecionar
`num_repetitions` como aleatório, o app cria automaticamente o bloco aninhado no ensaio. Os demais
fatores aleatórios são cruzados. `year`, quando fixo, é sempre tratado como fator categórico. É
possível incluir a interação genótipo × ensaio como componente aleatório; ela requer repetições.
Sem interação, o modelo é aditivo.

As estimativas gerais de genótipo dão peso igual aos ensaios, usando a mesma distribuição dos demais efeitos fixos para todos os genótipos. Nas predições por ensaio, os efeitos fixos adicionais são padronizados pela média da matriz de delineamento dentro de cada ensaio. Somam-se os efeitos aleatórios estimados de genótipo, ensaio e interação, quando presentes. Outros efeitos aleatórios, como blocos, são fixados em zero para essa comparação. Só são exportadas predições de combinações genótipo × ensaio observadas no ajuste.

O índice ambiental inicia em **Preditos (BLUE / BLUP)** e exige um ajuste para `yield` com o datacut atual. **Dados brutos** permite consultar médias de parcelas sem ajustar. Em ambos os modos, o eixo X usa a média dos genótipos presentes no ensaio, com peso igual por genótipo; o eixo Y usa a predição ou a média bruta do genótipo. As médias dos cards dão peso igual aos ensaios comuns. Mudar a base ou o recorte invalida as predições anteriores.

Registros com valores ausentes/não finitos nas variáveis do modelo são omitidos com contagem explícita. Modelos sem convergência, com efeitos fixos confundidos ou sem graus de liberdade são recusados. A herdabilidade não é inferida a partir da variância de um fator arbitrário.

A equação ilustrativa acompanha as escolhas de efeitos antes do ajuste. Na tabela de ranking, a estimativa recebe formatação condicional e **n** conta as parcelas realmente usadas para cada genótipo, após omitir ausências nas variáveis do modelo; também se mostra o número de ensaios observados. As predições por ensaio têm um gráfico de barras com seleção de **Ano | Ensaio | Local / Ambiente DEV** (a seleção não altera a tabela completa nem o datacut). O gráfico de variâncias inclui os componentes aleatórios e o resíduo, sem atribuir variância aos efeitos fixos; as proporções não representam R² ou herdabilidade.

O gráfico de rosca do índice ambiental conta uma vitória por ensaio comum, a partir do modo bruto ou predito selecionado. O denominador dos percentuais é o total de ensaios comuns, incluindo empates. Diferenças de até 1e-8 na unidade da resposta são tratadas como empates numéricos; isto não é um teste de significância.

## Produtividade e ciclo

Em **Produtividade × ciclo**, o eixo X usa `days_to_spike` da aba auxiliar, vinculada por `gid` (não a coluna textual `cycle`). Cada ponto é um genótipo. No modo estimado, o eixo Y usa a média ajustada/predita geral de yield, por BLUE ou BLUP, não apenas o desvio aleatório. No modo bruto, usa a média das médias por ensaio observado, com pesos iguais entre ensaios. Os dias demonstrativos são sintéticos.

O seletor de genótipos altera apenas o gráfico e sua regressão. A regressão linear com intercepto combina os **checks e comerciais incluídos**, com peso igual por genótipo, e exige pelo menos duas referências com dias distintos. Exibe equação, R² e número de referências; não extrapola a linha além do ciclo das referências. Materiais sem dias válidos ou com vínculo ambíguo entre nome e GID são omitidos com aviso, sem inventar valores. As categorias CHECK/TESTEMUNHA e COMERCIAL/COMMERCIAL são reconhecidas. As cores e a regressão não constituem teste de superioridade.

## Produtividade e proteína

A aba **Produtividade × proteína** permite alternar a produtividade entre dados brutos e a estimativa
BLUE/BLUP válida para o datacut. `protein` é sempre bruto: primeiro se calcula a média das parcelas
dentro de cada ensaio e depois a média entre ensaios, dando peso igual a cada ensaio. O gráfico tem
um ponto por genótipo, seletor independente, exportação CSV e regressão apenas dos checks e comerciais.

## Seleção

A aba **Seleção** replica a análise de produtividade × ciclo, com produtividade bruta ou estimada.
Checks e comerciais compartilham a legenda preta e são os únicos materiais usados na regressão.
Os demais materiais são classificados contra a média de produtividade das testemunhas do datacut:
ganho acima de 5% em verde, ganho acima de 0% até 5% em amarelo e ganho nulo ou negativo em vermelho.
O valor percentual e a categoria original permanecem no hover e no CSV.

Referência técnica: [componentes de variância e fatores cruzados no statsmodels](https://www.statsmodels.org/stable/examples/notebooks/generated/variance_components.html).

## Diagnósticos e revisão de outliers

O QQ plot e o gráfico de resíduos exibem o plot, a linha da primeira aba do Excel,
o genótipo, a unidade de ensaio, a resposta observada, o ajustado e o resíduo.
A correspondência com a linha original é preservada após omitir ausências e ordenar
o QQ plot. `plot_id` é preferido para exibição, com `plot_id_in_source` e `plot_number`
como alternativas; na ausência deles, a linha continua identificando o registro.
IDs repetidos não provocam exclusões em conjunto: cada exclusão usa a linha única da origem.

A sinalização inicial usa `abs(resíduo) / sqrt(variância residual) > 3`, com limite
ajustável de 1 a 10. É uma triagem exploratória dos resíduos condicionais, **não**
um teste formal, uma avaliação de influência ou um resíduo studentizado. Sem variância
residual positiva, não há sinalização por esse critério. A lista permite revisar
quais candidatos excluir. O [NIST recomenda investigar observações suspeitas](https://www.itl.nist.gov/div898/handbook/eda/section3/eda33a8.htm), não rejeitá-las automaticamente.

**Recalcular modelo removendo outliers** refaz uma única vez o modelo salvo, preservando
resposta, método BLUE/BLUP, efeitos e interação, mesmo que o formulário de Modelo
tenha sido editado depois. Predições, variâncias, n, ranking, diagnóstico, índice
ambiental estimado e ciclo estimado passam a usar o novo ajuste. Dados brutos e a
Base filtrada permanecem intactos. Falhas de ajuste mantêm o modelo anterior.
Novos candidatos exigem nova seleção e clique; não existe limpeza iterativa automática.

O histórico de exclusões (incluindo resíduos anteriores e limite usado) pode ser
baixado em CSV. **Restaurar ajuste sem exclusões** recupera o ajuste anterior à primeira
remoção. O diagnóstico compara n e variância residual antes/depois. Alterar datacut/base
invalida o ajuste e seu histórico; calcular novamente em Modelo recomeça sem exclusões.

## Verificar alterações

```bash
python -X utf8 -m unittest test_trial_units test_analysis test_diagnostics test_reporting test_app -v
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

Envie os arquivos do projeto ao GitHub, incluindo **app.py, analysis.py, reporting.py e trial_units.py** (obrigatórios), `requirements.txt`, `.streamlit/config.toml` e o template. No Streamlit Community Cloud, escolha:

- repositório: este projeto;
- branch: a branch principal;
- arquivo principal: `app.py`.
