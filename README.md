# 💱 Projeto de Pipeline de Dados - Cotações de Moedas (BACEN)

**Objetivo principal:**  
Executar um pipeline ETL que coleta, transforma e disponibiliza dados para análise da **comparação do Euro (EUR) em relação ao Dólar Comercial (USD)**, apresentando suas cotações diárias, taxas de câmbio e o status dos boletins diários.

Este projeto implementa um pipeline de dados completo que coleta, transforma, armazena e apresenta visualmente as **cotações diárias de moedas estrangeiras** por meio da API pública do Banco Central do Brasil (BACEN).

## 🧠 Visão Geral

A solução automatiza o processo de obtenção de cotações cambiais e torna os dados acessíveis de forma visual e interativa via dashboard. O pipeline é orquestrado para rodar diariamente de forma automática, buscando apenas os dados mais recentes para otimizar o processo.

---

## 🧰 Tecnologias Utilizadas

| Etapa | Ferramenta | Descrição |
| --- | --- | --- |
| Dados Externos | API BACEN | Fonte de dados de câmbio em tempo real |
| Linguagem | `Python` | Linguagem principal para o desenvolvimento do pipeline e dashboard |
| Dependências | `Poetry` | Gerenciamento de dependências do pipeline ETL |
| Extract | `requests` | Coleta os dados da API REST do BACEN |
| Transform | `Python` | Normalização e tratamento dos dados coletados |
| Load | `Supabase` | Banco de dados relacional (PostgreSQL) na nuvem |
| Dashboard | `Streamlit` | Visualização e análise interativa em tempo real |
| Orquestração | `GitHub Actions` | Automação e agendamento da execução diária do pipeline |
| Containerização | `Docker` | Empacotamento e execução isolada do pipeline e do dashboard |

---

## ⚙️ Configuração do Ambiente

Antes de executar o projeto, siga estes passos para configurar o banco de dados e as credenciais.

### 1. Configurando o Supabase (Banco de Dados)

Você precisará de uma conta gratuita no [Supabase](https://supabase.com/).

**Passo 1: Crie um novo projeto**
- Após fazer login, clique em "New project".
- Escolha um nome para o projeto e gere uma senha segura para o banco de dados. Guarde essa senha.
- Selecione a região mais próxima de você e clique em "Create new project".

**Passo 2: Crie a tabela de cotações**
- No menu lateral esquerdo, vá para **SQL Editor**.
- Clique em **New query**.
- Copie e cole o script SQL abaixo e clique em **RUN**. Isso criará a tabela `DollarQuotation` com a estrutura correta.

```sql
CREATE TABLE "DollarQuotation" (
    "paridadeCompra" float8,
    "paridadeVenda" float8,
    "cotacaoCompra" float8,
    "cotacaoVenda" float8,
    "dataHoraCotacao" timestamp with time zone NOT NULL,
    "tipoBoletim" text,
    CONSTRAINT "DollarQuotation_pkey" PRIMARY KEY ("dataHoraCotacao")
);
```

**Passo 3: Obtenha a URL e a Chave de API**
- No menu lateral esquerdo, vá para **Project Settings** (ícone de engrenagem).
- Selecione **API**.
- Você encontrará as informações que precisa:
    - Em **Project URL**, copie a URL.
    - Em **Project API Keys**, copie a chave `service_role`. **Atenção:** esta chave tem privilégios de administrador. Mantenha-a segura e não a exponha publicamente.

### 2. Configurando o Pipeline (Arquivo `.env`)

O pipeline ETL usa um arquivo `.env` para se conectar ao Supabase.

- Na raiz do seu projeto, crie um arquivo chamado `.env`.
- Adicione a URL e a chave que você copiou no passo anterior:

```properties
# filepath: .env
SUPABASE_URL="SUA_URL_DO_SUPABASE_AQUI"
SUPABASE_KEY="SUA_CHAVE_SERVICE_ROLE_AQUI"
```

### 3. Configurando o Dashboard (`secrets.toml`)

O dashboard Streamlit usa um arquivo de segredos para se conectar de forma segura.

- Na raiz do seu projeto, crie uma pasta chamada `.streamlit`.
- Dentro