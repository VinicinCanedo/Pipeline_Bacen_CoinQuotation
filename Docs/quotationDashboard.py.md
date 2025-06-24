# QuotationDashboard.py

## Visão Geral

Ele implementa um **dashboard interativo em Streamlit** para análise de cotações do dólar, utilizando dados extraídos de uma tabela no Supabase. O dashboard permite ao usuário:

- **Visualizar gráficos** de tendência, variação diária e médias móveis das cotações de compra e venda do dólar.
- **Filtrar o período de análise** usando um slider.
- **Consultar um agente de IA (Agno)**, que responde perguntas sobre as cotações com base nos dados mais recentes do banco, utilizando um modelo LLM hospedado na Groq.

O fluxo principal é:

1. Carrega os dados do Supabase e prepara o DataFrame.
2. Exibe gráficos interativos com Plotly.
3. Permite perguntas ao agente de IA, que recebe como contexto os últimos registros do DataFrame filtrado.

Assim, o código une análise visual, manipulação de dados e inteligência artificial para oferecer uma experiência rica e interativa ao usuário.

---

### 1. **Importações**

```python
import streamlit as st
import pandas as pd
from supabase import create_client, Client
from agno.agent import Agent
from agno.models.groq import Groq
from agno.tools.duckduckgo import DuckDuckGoTools
import plotly.express as px
from datetime import datetime, timedelta

```

- **streamlit**: Framework para criar dashboards web interativos em Python.
- **pandas**: Manipulação de dados em DataFrames.
- **supabase**: Cliente para acessar o banco de dados Supabase.
- **agno.agent, agno.models.groq, agno.tools.duckduckgo**: Integração com o agente de IA Agno, usando o modelo Groq e a ferramenta DuckDuckGo.
- **plotly.express**: Criação de gráficos interativos.
- **datetime, timedelta**: Manipulação de datas e períodos.

---

### 2. **Chave do Agno**

```python
AGNO_KEY=st.secrets["AGNO_KEY"]

```

- Carrega a chave de API do Agno dos segredos do Streamlit para autenticação do modelo Groq.

---

### 3. **Função para Carregar Dados do Supabase**

```python
@st.cache_data
def carregar_dados():
    ...

```

- **@st.cache_data**: Cacheia o resultado da função para evitar consultas repetidas ao banco a cada interação.
- **Conexão**: Usa as credenciais do Supabase armazenadas nos segredos do Streamlit.
- **Consulta**: Busca todos os dados da tabela `DollarQuotation`, ordenando do mais recente para o mais antigo.
- **Conversão**: Transforma os dados em um DataFrame do pandas.
- **Tratamento**: Se não houver dados, exibe erro e retorna DataFrame vazio.
- **Conversão de datas**: Garante que a coluna de data está no formato correto e cria uma coluna `data` apenas com a data (sem hora).

---

### 4. **Carregamento dos Dados**

```python
df = carregar_dados()
if df.empty:
    st.stop()

```

- Carrega os dados do Supabase.
- Se não houver dados, interrompe a execução do dashboard para evitar erros posteriores.

---

### 5. **Layout do Dashboard**

```python
st.title("💱 Dashboard de Cotações USD - BACEN")
st.markdown("Visualize e explore os dados de câmbio entre Euro e Dólar")

```

- Define o título e uma breve descrição do dashboard.

---

### 6. **Filtro de Período**

```python
periodo = st.slider("Selecione o período (meses)", 1, 2, 3, 4)
data_limite = datetime.now().date() - timedelta(days=30 * periodo)
df_filtrado = df[df['data'] >= data_limite]

```

- **Slider**: Permite ao usuário escolher o período de análise em meses.
- **Filtragem**: Seleciona apenas os dados dentro do período escolhido.

---

### 7. **Gráfico de Tendência**

```python
st.subheader("📈 Tendência do Dólar nos últimos meses")
fig1 = px.line(df_filtrado, x='data', y=['cotacaoCompra', 'cotacaoVenda'], ...)
st.plotly_chart(fig1, use_container_width=True)

```

- Cria um gráfico de linha mostrando a evolução das cotações de compra e venda do dólar no período filtrado.

---

### 8. **Variação Cambial Diária**

```python
st.subheader("🔁 Variação Cambial Diária")
df_filtrado['varCotacao'] = df_filtrado['cotacaoVenda'].pct_change() * 100
fig2 = px.bar(df_filtrado, x='data', y='varCotacao', ...)
st.plotly_chart(fig2, use_container_width=True)

```

- Calcula a variação percentual diária da cotação de venda.
- Exibe um gráfico de barras com essa variação.

---

### 9. **Médias Móveis**

```python
st.subheader("📊 Médias Móveis (7 e 30 dias)")
df_filtrado['MM7'] = df_filtrado['cotacaoVenda'].rolling(window=7).mean()
df_filtrado['MM30'] = df_filtrado['cotacaoVenda'].rolling(window=30).mean()
fig3 = px.line(df_filtrado, x='data', y=['cotacaoVenda', 'MM7', 'MM30'], ...)
st.plotly_chart(fig3, use_container_width=True)

```

- Calcula as médias móveis de 7 e 30 dias da cotação de venda.
- Exibe um gráfico de linha com a cotação e as médias móveis.

---

### 10. **Integração com Agente de IA (Agno)**

```python
agent = Agent(
    model=Groq(
        "meta-llama/llama-4-scout-17b-16e-instruct",
        api_key=AGNO_KEY
    ),
    name="Agno",
    description="Você é um Analista de Câmbio responsável por acompanhar e avaliar diariamente as cotações de moedas estrangeiras com base em relatórios, contratos e regulamentações do Banco Central.",
    tools=[DuckDuckGoTools()]
)

```

- Instancia o agente Agno, usando o modelo Groq e a ferramenta DuckDuckGo, com uma descrição personalizada para o papel do agente.

---

### 11. **Pergunta ao Agente de IA**

```python
st.subheader("🤖 Pergunte ao Agente de IA (Agno)")
pergunta = st.text_input("Digite sua pergunta sobre as cotações:")

if pergunta:
    contexto_df = df_filtrado.tail(10)
    contexto_texto = contexto_df.to_string(index=False)
    prompt = (
        f"Considere os seguintes dados de cotações do dólar extraídos do Banco Central do Brasil:\\n"
        f"{contexto_texto}\\n\\n"
        f"Pergunta do usuário: {pergunta}\\n"
        f"Responda de forma clara e baseada nos dados acima."
    )

    with st.spinner("Agno está pensando..."):
        resposta = agent.run(prompt)
    st.success(resposta.content if hasattr(resposta, "content") else resposta)

```

- Permite ao usuário digitar uma pergunta sobre as cotações.
- Seleciona os últimos 10 registros filtrados como contexto.
- Monta um prompt contextualizado para o agente de IA.
- Envia o prompt ao agente e exibe a resposta de forma amigável no dashboard.

---

## **Resumo**

O código cria um dashboard interativo que:

- Carrega e filtra dados do Supabase.
- Exibe gráficos de tendência, variação e médias móveis.
- Permite ao usuário consultar um agente de IA (Agno), que responde perguntas contextualizadas com base nos dados mais recentes do banco.

Se quiser explicações ainda mais detalhadas sobre algum trecho específico, é só pedir!