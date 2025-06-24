# 💱 Projeto de Pipeline de Dados - Cotações de Moedas (BACEN)

**Objetivo principal:**  
Executar um pipeline ETL que coleta, transforma e disponibiliza dados para análise da **cotação do Dólar (USD) em relação ao Real (BRL)**, apresentando suas cotações diárias, taxas de câmbio e o status dos boletins diários.

Este projeto implementa um pipeline de dados completo que coleta, transforma, armazena e apresenta visualmente as **cotações diárias do Dólar (USD)** por meio da API pública do Banco Central do Brasil (BACEN).

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
- Dentro da pasta `.streamlit`, crie um arquivo chamado `secrets.toml`.
- Adicione as mesmas credenciais do Supabase a este arquivo:

```toml
# filepath: .streamlit/secrets.toml
SUPABASE_URL="SUA_URL_DO_SUPABASE_AQUI"
SUPABASE_KEY="SUA_CHAVE_SERVICE_ROLE_AQUI"
```
**Importante:** Certifique-se de que este arquivo está salvo com a codificação **UTF-8**. No VS Code, você pode verificar e alterar a codificação na barra de status inferior direita.

---

## 🐳 Como Executar com Docker

Com o ambiente configurado, você pode construir e executar as aplicações com os seguintes comandos.

**1. Construa a imagem do Pipeline ETL:**
Este comando usa o `Dockerfile` principal para criar a imagem que executará o script de extração.

```bash
docker build -f Dockerfile -t pipeline-bacen .
```

**2. Execute o Pipeline ETL:**
Este comando executa o container, injetando as credenciais do seu arquivo `.env`. O pipeline buscará os dados e os salvará no seu banco Supabase.

```bash
docker run --env-file .env pipeline-bacen
```

**3. Construa a imagem do Dashboard:**
Este comando usa o `Dockerfile.dashboard` para criar a imagem que servirá a aplicação Streamlit.

```bash
docker build -f Dockerfile.dashboard -t dashboard-bacen .
```

**4. Inicie o Dashboard Streamlit:**
Este comando executa o container do dashboard e mapeia a porta `8501` para que você possa acessá-lo no seu navegador.

```bash
docker run -p 8501:8501 dashboard-bacen
```

- Após executar, acesse **`http://localhost:8501`** no seu navegador para ver o dashboard.

---

## 🔁 Etapas da Pipeline

1.  **Extração de Dados**
    O pipeline consulta o Supabase para obter a data do último registro. Em seguida, busca na API do BACEN apenas os dados a partir dessa data até o dia atual, otimizando a coleta.

2.  **Transformação de Dados**
    Os dados brutos em JSON são processados com Python: os tipos de dados são corrigidos, e duplicatas na mesma carga são removidas para garantir a integridade.

3.  **Carga em Supabase**
    Antes de inserir, o pipeline verifica novamente quais registros já existem no banco para evitar erros de duplicidade. Apenas os dados 100% novos são carregados na tabela `DollarQuotation`.

4.  **Visualização via Streamlit**
    O dashboard se conecta diretamente ao Supabase, garantindo que os dados exibidos estejam sempre atualizados. Ele oferece gráficos de linha, barras e médias móveis, com filtros interativos.

---

## 🚀 Execução Automática com GitHub Actions

Você pode agendar a execução diária do pipeline ETL de forma totalmente automática usando o GitHub Actions. Siga o passo a passo abaixo:

### 1. Crie o workflow do GitHub Actions

- No seu repositório, crie a pasta `.github/workflows` (caso ainda não exista).
- Dentro dela, crie um arquivo chamado `pipeline-etl.yml` com o seguinte conteúdo:

```yaml
name: Pipeline ETL Bacen

on:
  schedule:
    - cron: '0 8 * * *'  # Executa todos os dias às 8h UTC
  workflow_dispatch:      # Permite execução manual pelo GitHub

jobs:
  run-pipeline:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout do código
        uses: actions/checkout@v4

      - name: Configurar Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Instalar dependências
        run: |
          pip install poetry
          poetry install

      - name: Configurar variáveis de ambiente
        run: |
          echo "SUPABASE_URL=${{ secrets.SUPABASE_URL }}" >> $GITHUB_ENV
          echo "SUPABASE_KEY=${{ secrets.SUPABASE_KEY }}" >> $GITHUB_ENV

      - name: Executar pipeline ETL
        run: |
          poetry run python Pipeline/main.py
```

### 2. Configure os segredos do repositório

- No GitHub, acesse seu repositório > **Settings** > **Secrets and variables** > **Actions** > **New repository secret**.
- Adicione os segredos:
  - `SUPABASE_URL` (URL do seu projeto Supabase)
  - `SUPABASE_KEY` (chave service_role do Supabase)

### 3. Pronto!

- O pipeline será executado automaticamente todos os dias no horário agendado.
- Você também pode rodar manualmente em **Actions** > **Pipeline ETL Bacen** > **Run workflow**.

---