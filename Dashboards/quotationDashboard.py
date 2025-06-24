import streamlit as st
import pandas as pd
from supabase import create_client, Client
from agno.agent import Agent
from agno.models.groq import Groq
from agno.tools.duckduckgo import DuckDuckGoTools
import plotly.express as px
from datetime import datetime, timedelta


AGNO_KEY=st.secrets["AGNO_KEY"]

# --- 1. Carregar dados do Supabase
@st.cache_data # O cache é ótimo para não buscar os dados a cada interação
def carregar_dados():
    """Conecta ao Supabase e carrega todos os dados da tabela de cotações."""
    try:
        # Carrega as credenciais dos segredos do Streamlit
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]

        # Cria o cliente Supabase
        supabase: Client = create_client(url, key)

        # Busca todos os dados da tabela, ordenando pelos mais recentes
        response = supabase.from_("DollarQuotation").select("*").order("dataHoraCotacao", desc=True).execute()
        
        # Converte os dados para um DataFrame do Pandas
        df = pd.DataFrame(response.data)

        # Tratamento de erros e conversão de tipos
        if df.empty:
            st.error("Nenhum dado foi retornado do banco de dados.")
            return pd.DataFrame()

        # Converte a coluna de data e cria a coluna 'data' para os filtros
        df['dataHoraCotacao'] = pd.to_datetime(df['dataHoraCotacao'])
        df['data'] = df['dataHoraCotacao'].dt.date
        
        print("Dados carregados do Supabase com sucesso!")
        return df

    except Exception as e:
        st.error(f"Erro ao conectar ou buscar dados no Supabase: {e}")
        return pd.DataFrame()


df = carregar_dados()

# Se o dataframe estiver vazio, para a execução para evitar erros nos componentes abaixo
if df.empty:
    st.stop()

# --- 2. Layout do Dashboard
st.title("💱 Dashboard de Cotações USD - BACEN")
st.markdown("Visualize e explore os dados de câmbio entre Euro e Dólar")

# Filtro de período
periodo = st.slider("Selecione o período (meses)", 1, 2, 3, 4)
data_limite = datetime.now().date() - timedelta(days=30 * periodo)
df_filtrado = df[df['data'] >= data_limite]

# --- 3. Gráfico de Tendência
st.subheader("📈 Tendência do Dólar nos últimos meses")
fig1 = px.line(df_filtrado, x='data', y=['cotacaoCompra', 'cotacaoVenda'],
               labels={'value': 'Cotação (R$)', 'data': 'Data'},
               title="Cotação Compra vs Venda")
st.plotly_chart(fig1, use_container_width=True)

# --- 4. Variação Cambial (diferença entre compra/venda)
st.subheader("🔁 Variação Cambial Diária")
df_filtrado['varCotacao'] = df_filtrado['cotacaoVenda'].pct_change() * 100
fig2 = px.bar(df_filtrado, x='data', y='varCotacao',
              title='Variação Percentual Diária da Cotação de Venda (%)')
st.plotly_chart(fig2, use_container_width=True)

# --- 5. Médias Móveis
st.subheader("📊 Médias Móveis (7 e 30 dias)")
df_filtrado['MM7'] = df_filtrado['cotacaoVenda'].rolling(window=7).mean()
df_filtrado['MM30'] = df_filtrado['cotacaoVenda'].rolling(window=30).mean()
fig3 = px.line(df_filtrado, x='data', y=['cotacaoVenda', 'MM7', 'MM30'],
               title='Médias Móveis da Cotação de Venda')
st.plotly_chart(fig3, use_container_width=True)


# --- 6. Integração com Agente de IA

# ...existing code...
agent = Agent(
    model=Groq(
        "meta-llama/llama-4-scout-17b-16e-instruct",
        api_key=AGNO_KEY
    ),
    name="Agno",
    description="Você é um Analista de Câmbio responsável por acompanhar e avaliar diariamente as cotações de moedas estrangeiras com base em relatórios, contratos e regulamentações do Banco Central.",
    tools=[DuckDuckGoTools()]
)
# ...código anterior...

st.subheader("🤖 Pergunte ao Agente de IA (Agno)")
pergunta = st.text_input("Digite sua pergunta sobre as cotações:")

if pergunta:
    # 1. Seleciona um resumo ou fatia dos dados relevantes para o contexto
    # Exemplo: últimos 10 registros filtrados
    contexto_df = df_filtrado.tail(10)
    # 2. Converte para texto (pode ser CSV, tabela, ou resumo customizado)
    contexto_texto = contexto_df.to_string(index=False)

    # 3. Monta o prompt contextualizado
    prompt = (
        f"Considere os seguintes dados de cotações do dólar extraídos do Banco Central do Brasil:\n"
        f"{contexto_texto}\n\n"
        f"Pergunta do usuário: {pergunta}\n"
        f"Responda de forma clara e baseada nos dados acima."
    )

    with st.spinner("Agno está pensando..."):
        resposta = agent.run(prompt)
    st.success(resposta.content if hasattr(resposta, "content") else resposta)