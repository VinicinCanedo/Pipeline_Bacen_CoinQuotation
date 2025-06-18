# 💱 Projeto de Pipeline de Dados - Cotações de Moedas (BACEN)

Este projeto implementa um pipeline de dados completo que coleta, transforma, armazena e apresenta visualmente as **cotações diárias de moedas estrangeiras** por meio da API pública do Banco Central do Brasil (BACEN). Além disso, conta com um agente de IA que responde perguntas sobre os dados, ampliando a análise exploratória.

## 🧠 Visão Geral

A solução automatiza o processo de obtenção de cotações cambiais e torna os dados acessíveis de forma visual e interativa via dashboard. Este projeto pode ser expandido para análises financeiras, previsão de mercado e integrações com relatórios econômicos.

---

## 🧰 Tecnologias Utilizadas

| Etapa | Ferramenta | Descrição |
| --- | --- | --- |
| Dados Externos | API BACEN | Fonte de dados de câmbio em tempo real |
| Extract | `requests` (Python) | Coleta os dados da API REST do BACEN |
| Transform | `Python` | Normalização e tratamento dos dados coletados |
| Load | `Supabase` | Banco de dados relacional (PostgreSQL) na nuvem |
| Dashboard | `Streamlit` | Visualização e análise interativa em tempo real |
| AI Agent | `Agno (Groq)` | Agente de IA que responde perguntas sobre os dados |

---

## 🔁 Etapas da Pipeline

1. **Extração de Dados**
    
    Utiliza a biblioteca `requests` para consultar a API do BACEN diariamente e obter as cotações de moedas como USD, EUR, ARS, entre outras.
    
2. **Transformação de Dados**
    
    Os dados brutos são tratados com Python, convertidos para tipos apropriados (datas, floats), removidos dados inconsistentes e padronizados os nomes das moedas.
    
3. **Carga em Supabase**
    
    Após o tratamento, os dados são inseridos em tabelas no Supabase utilizando a API REST ou cliente Python. Há controle de duplicidade por data e código da moeda.
    
4. **Visualização via Streamlit**
    
    Criação de gráficos de linha, tabelas e filtros por moeda e intervalo de datas. Interface simples e responsiva hospedada localmente ou em nuvem.
    
5. **Interação com Agente de IA (Agno/Groq)**
    
    O agente Agno, executado na infraestrutura Groq, permite ao usuário realizar perguntas em linguagem natural como:
    
    > “Qual foi a média do dólar nos últimos 30 dias?”
    > 
    > 
    > “Qual moeda teve a maior variação este mês?”
    > 

---

## 🐳 Como Executar com Docker

1. **Construa a imagem Docker:**

    ```bash
    docker build -t pipeline-bacen .
    ```

2. **Crie um arquivo `.env` com suas credenciais do Supabase e chave da API (caso necessário) na raiz do projeto.**

3. **Execute o pipeline ETL:**

    ```bash
    docker run --env-file .env pipeline-bacen
    ```

4. **Inicie o dashboard Streamlit:**

    ```bash
    docker run -p 8501:8501 --env-file .env pipeline-bacen streamlit run dashboard.py
    ```

---

## 📊 Exemplos de Visualizações

- Tendência do dólar nos últimos 6 meses
- Comparativo de variações cambiais
- Médias móveis para moedas específicas
- Análises interativas com ajuda da IA

---

## 🤖 Sobre o Agente de IA (Agno)

Agno é um agente conversacional inteligente integrado ao pipeline, capaz de interpretar os dados armazenados e gerar insights automaticamente com base em consultas em linguagem natural. Ele utiliza a infraestrutura de processamento de linguagem da Groq, proporcionando respostas