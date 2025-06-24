# Main.py

### Visão Geral

Este script é um pipeline de ETL (Extração, Transformação e Carga) projetado para ser robusto e flexível. Sua principal função é buscar dados da cotação do dólar na API do Banco Central (BACEN), processá-los e armazená-los em um banco de dados Supabase. Ele foi cuidadosamente construído para suportar duas operações essenciais:

1. **Extração Incremental**: Em sua operação normal, ele busca apenas os dados novos desde a última execução, sendo muito eficiente.
2. **Backfill Histórico**: Permite preencher o banco de dados com dados históricos caso a data de início seja alterada para uma data mais antiga, sem gerar erros de duplicidade.

---

### 1. Importações e Constante Global

```python
import os
import requests
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime, timedelta

# Define a data mínima para o início da extração.
# O formato é 'MM-DD-YYYY' para consistência com a API do BACEN.
MIN_START_DATE = "04-01-2025"

```

- **`import`**: O script começa importando as bibliotecas necessárias:
    - `os`, `dotenv`: Usadas para carregar de forma segura as credenciais (URL e chave da API) do Supabase a partir de um arquivo .env.
    - `requests`: A biblioteca padrão para fazer as chamadas HTTP à API do BACEN.
    - `supabase`: A biblioteca oficial para se comunicar com o banco de dados Supabase.
    - `datetime`, `timedelta`: Essenciais para toda a manipulação de datas, como calcular períodos de extração e normalizar timestamps.
- **`MIN_START_DATE`**: Esta é uma constante global que serve como a "data piso" do projeto. Ela tem duas finalidades:
    1. Se o banco de dados estiver vazio, a primeira busca de dados começará nesta data.
    2. É a chave para o *backfill*. Se você alterar esta data para uma mais antiga que os dados já existentes no banco, o pipeline irá automaticamente buscar e preencher os dados históricos que faltam.

---

### 2. Função `obter_data_inicio_extracao`

```python
def obter_data_inicio_extracao(supabase_client: Client) -> str:
    """
    Determina a data de início para a extração de dados, suportando extração incremental e backfill.
    """
    print("Determinando a data de início para a extração...")
    
    try:
        min_start_date_dt = datetime.strptime(MIN_START_DATE, '%m-%d-%Y')
        response_latest = supabase_client.from_("DollarQuotation").select("dataHoraCotacao").order("dataHoraCotacao", desc=True).limit(1).execute()
        response_earliest = supabase_client.from_("DollarQuotation").select("dataHoraCotacao").order("dataHoraCotacao", desc=False).limit(1).execute()

        if not response_latest.data:
            print(f"Nenhum registro encontrado. A extração iniciará a partir de: {MIN_START_DATE}.")
            return MIN_START_DATE

        latest_date_dt = datetime.fromisoformat(response_latest.data[0]['dataHoraCotacao'])
        earliest_date_dt = datetime.fromisoformat(response_earliest.data[0]['dataHoraCotacao'])

        print(f"Data mais antiga no banco: {earliest_date_dt.strftime('%d-%m-%Y')}")
        print(f"Data mais recente no banco: {latest_date_dt.strftime('%d-%m-%Y')}")

        if min_start_date_dt < earliest_date_dt:
            print(f"BACKFILL: A data mínima ({MIN_START_DATE}) é anterior à mais antiga no banco. Iniciando backfill.")
            return MIN_START_DATE
        
        proxima_data = latest_date_dt + timedelta(days=1)
        data_formatada = proxima_data.strftime('%m-%d-%Y')
        print(f"INCREMENTAL: A busca continuará a partir de {data_formatada}.")
        return data_formatada

    except Exception as e:
        print(f"Erro ao determinar a data de início: {e}. Usando a data mínima padrão: {MIN_START_DATE}.")
        return MIN_START_DATE
```

Esta é a função que define a inteligência do pipeline, decidindo a partir de qual data a extração deve começar.

- **Busca no Banco**: Ela executa duas consultas na tabela `DollarQuotation`: uma para obter a data **mais recente** (`order("dataHoraCotacao", desc=True)`) e outra para a **mais antiga** (`desc=False`).
- **Cenário 1: Tabela Vazia**: Se a primeira consulta (`response_latest`) não retornar dados, significa que o banco está vazio. A função então retorna a `MIN_START_DATE` para iniciar a carga inicial.
- **Cenário 2: Lógica de Backfill**: A função compara a `MIN_START_DATE` (convertida para um objeto `datetime`) com a data mais antiga encontrada no banco. Se a `MIN_START_DATE` for anterior, significa que o usuário deseja preencher dados históricos. Nesse caso, a função retorna a `MIN_START_DATE` para iniciar o processo de backfill.
- **Cenário 3: Extração Incremental (Normal)**: Se os cenários acima não forem verdadeiros, o pipeline está em modo de operação normal. A função pega a data mais recente do banco, adiciona um dia (`timedelta(days=1)`) e retorna essa nova data. Isso garante que a extração continue exatamente de onde parou.
- **Tratamento de Erro**: O bloco `try...except` garante que, se houver qualquer falha na comunicação com o banco, o pipeline não quebre, retornando a `MIN_START_DATE` como uma opção segura.

---

### 3. Função `extrair_dados_bacen`

```python
def extrair_dados_bacen(data_inicial: str):
    """Extrai os dados da API do BACEN a partir de uma data inicial até a data atual."""
    print(f"\nIniciando extração de dados da API do BACEN a partir de {data_inicial}...")
    data_final = datetime.now().strftime('%m-%d-%Y')
    url = f"https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?@moeda='USD'&@dataInicial='{data_inicial}'&@dataFinalCotacao='{data_final}'&$orderby=dataHoraCotacao%20desc&$format=json"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        print("Dados extraídos com sucesso!")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao extrair dados da API: {e}")
        return None
```

Esta função corresponde à etapa de **Extração (E)** do ETL.

- **Montagem da URL**: Ela recebe a `data_inicial` (definida pela função anterior) e usa a data atual como `data_final`. Com essas datas, ela constrói a URL completa da API do BACEN, solicitando as cotações do dólar ('USD') para o período especificado.
- **Chamada à API**: Utiliza `requests.get(url)` para fazer a requisição.
- **`response.raise_for_status()`**: Uma linha crucial para a robustez do código. Se a API retornar um código de erro (como 404 Not Found ou 500 Internal Server Error), esta linha irá gerar uma exceção, que será capturada pelo `try...except`, evitando que o pipeline continue com dados inválidos.
- **Retorno**: Se a chamada for bem-sucedida, retorna os dados em formato JSON. Se falhar, retorna `None`.

---

### 4. Função `transformar_dados`

```python
def transformar_dados(dados_json):
    """Transforma os dados brutos, removendo duplicatas da mesma carga."""
    if not dados_json or "value" not in dados_json or not dados_json["value"]:
        return []

    registros_unicos = {}
    for registro in dados_json["value"]:
        chave_unica = registro.get("dataHoraCotacao")
        if chave_unica:
            registros_unicos[chave_unica] = {
                "paridadeCompra": registro.get("paridadeCompra"),
                "paridadeVenda": registro.get("paridadeVenda"),
                "cotacaoCompra": registro.get("cotacaoCompra"),
                "cotacaoVenda": registro.get("cotacaoVenda"),
                "dataHoraCotacao": chave_unica,
                "tipoBoletim": registro.get("tipoBoletim")
            }
    return list(registros_unicos.values())
```

Esta é a etapa de **Transformação (T)**.

- **Remoção de Duplicatas**: A API do BACEN pode, ocasionalmente, retornar múltiplos registros para o mesmo timestamp. Para garantir a integridade dos dados, a função usa um dicionário (`registros_unicos`) onde a chave é a `dataHoraCotacao`. Como um dicionário não pode ter chaves repetidas, isso elimina automaticamente as duplicatas da carga de dados atual.
- **Seleção de Campos**: Para cada registro, ela extrai apenas os campos de interesse (`cotacaoCompra`, `cotacaoVenda`, etc.), criando um dicionário limpo e estruturado.
- **Retorno**: Retorna uma lista contendo os dicionários dos registros já limpos e únicos, pronta para ser carregada no banco.

---

### 5. Função `carregar_dados_supabase`

```python
def carregar_dados_supabase(supabase_client: Client, dados: list):
    """
    Verifica e insere apenas os registros novos, comparando objetos datetime para máxima precisão.
    """
    if not dados:
        print("Nenhum dado para carregar.")
        return

    print(f"\nIniciando verificação de {len(dados)} registros da API...")
    
    # 1. Normaliza todas as chaves da API para objetos datetime
    # O formato da API é 'YYYY-MM-DD HH:MM:SS.f'
    # Usamos um dicionário para mapear o objeto datetime de volta para o registro original
    api_datetime_map = {}
    for registro in dados:
        try:
            # O formato '%Y-%m-%d %H:%M:%S.%f' é flexível e lida com frações de segundo variáveis
            dt_obj = datetime.strptime(registro['dataHoraCotacao'], '%Y-%m-%d %H:%M:%S.%f')
            api_datetime_map[dt_obj] = registro
        except ValueError:
            # Tenta sem as frações de segundo, caso a API as omita
            dt_obj = datetime.strptime(registro['dataHoraCotacao'], '%Y-%m-%d %H:%M:%S')
            api_datetime_map[dt_obj] = registro

    # 2. Consulta o banco para buscar registros que possam ser duplicados
    chaves_api_str = [registro['dataHoraCotacao'] for registro in dados]
    response = supabase_client.from_("DollarQuotation").select("dataHoraCotacao").in_("dataHoraCotacao", chaves_api_str).execute()

    if hasattr(response, 'error') and response.error:
        print(f"Erro ao verificar dados existentes no Supabase: {response.error}")
        return

    # 3. Normaliza todas as chaves do banco para objetos datetime
    db_datetimes = set()
    for registro in response.data:
        # O formato do Supabase é ISO 8601, que fromisoformat lida perfeitamente
        db_datetimes.add(datetime.fromisoformat(registro['dataHoraCotacao']))

    print(f"Verificação no banco de dados encontrou {len(db_datetimes)} registros já existentes.")

    # 4. Determina quais registros são REALMENTE novos comparando os objetos datetime
    dados_para_inserir = []
    for dt_obj, registro_original in api_datetime_map.items():
        # Adiciona à lista de inserção apenas se o datetime não estiver no conjunto do banco
        if dt_obj not in db_datetimes:
            dados_para_inserir.append(registro_original)

    if not dados_para_inserir:
        print("Todos os dados extraídos já constam na base. Nenhuma inserção necessária.")
        return

    # 5. Insere os novos dados em lotes
    print(f"\nIniciando a carga de um total de {len(dados_para_inserir)} novos registros no Supabase...")
    TAMANHO_LOTE = 500
    try:
        for i in range(0, len(dados_para_inserir), TAMANHO_LOTE):
            lote = dados_para_inserir[i:i + TAMANHO_LOTE]
            print(f"Carregando lote {i // TAMANHO_LOTE + 1} com {len(lote)} registros...")
            insert_response = supabase_client.from_("DollarQuotation").insert(lote).execute()
            if hasattr(insert_response, 'error') and insert_response.error:
                print(f"ERRO CRÍTICO ao carregar lote: {insert_response.error}")
                return
        print("\nNovos dados carregados com sucesso!")
    except Exception as e:
        print(f"Falha inesperada na operação de carga: {e}")
```

Esta é a etapa de **Carga (L)**, e é a mais sofisticada para garantir que o erro de "chave duplicada" não ocorra.

1. **Normalização da API**: Primeiro, ela percorre os dados vindos da API e converte cada string `dataHoraCotacao` em um objeto `datetime` real do Python. Isso é feito de forma flexível para lidar com variações nos milissegundos.
2. **Consulta ao Banco**: Ela coleta todas as chaves de data (como strings) da API e faz uma única consulta ao Supabase usando o filtro `.in_()`. Isso é muito eficiente, pois pede ao banco: "Desta lista de chaves, me diga quais você já tem".
3. **Normalização do Banco**: Em seguida, ela pega os resultados do banco e também converte cada `dataHoraCotacao` em um objeto `datetime`.
4. **Comparação Precisa**: Agora vem o passo crucial. A função compara os **objetos `datetime`** da API com os **objetos `datetime`** do banco. Como a comparação é feita entre objetos e não entre textos, ela é 100% precisa e imune a diferenças de formatação (como `.9` vs `.900` ou a presença de `T` e fuso horário). Apenas os registros cujos `datetime` não existem no banco são selecionados para inserção.
5. **Carga em Lotes**: Para lidar com grandes volumes de dados (especialmente durante um backfill), a inserção é feita em lotes de 500 registros. Isso evita sobrecarregar a rede ou o banco de dados e torna o processo mais seguro.

---

### 6. Função `main` e Ponto de Entrada

```python
def main():
    """Função principal que orquestra o pipeline ETL."""
    print("--- Iniciando Pipeline ETL de Cotações ---")
    
    load_dotenv()
    url: str = os.getenv("SUPABASE_URL")
    key: str = os.getenv("SUPABASE_KEY")

    if not all([url, key]):
        print("Erro: SUPABASE_URL ou SUPABASE_KEY não definidas no .env.")
        return

    try:
        supabase: Client = create_client(url, key)
        print("Cliente Supabase criado com sucesso.")
    except Exception as e:
        print(f"Falha ao criar cliente Supabase: {e}")
        return

    data_inicio_extracao = obter_data_inicio_extracao(supabase)
    dados_brutos = extrair_dados_bacen(data_inicio_extracao)

    if not dados_brutos or not dados_brutos.get("value"):
        print("Nenhum dado novo foi extraído da API do BACEN. Finalizando pipeline.")
        return

    dados_para_inserir = transformar_dados(dados_brutos)
    if not dados_para_inserir:
        print("Nenhum dado novo para inserir após a transformação. Finalizando pipeline.")
        return

    carregar_dados_supabase(supabase, dados_para_inserir)
    
    print("\n--- Pipeline ETL finalizado ---")

if __name__ == "__main__":
    main()
```

- **`main()`**: É o "maestro" que executa todo o processo em ordem.
    1. **Setup**: Carrega as credenciais do arquivo .env e cria o cliente de conexão com o Supabase.
    2. **Orquestração**: Chama as funções na sequência correta: `obter_data_inicio_extracao` -> `extrair_dados_bacen` -> `transformar_dados` -> `carregar_dados_supabase`.
    3. **Validações**: Entre as etapas, há verificações (`if not dados_brutos...`) para garantir que o pipeline pare de forma limpa se, por exemplo, a API não retornar dados novos, evitando processamento desnecessário.
- **`if __name__ == "__main__":`**: Esta é uma construção padrão em Python. Ela garante que a função `main()` seja executada apenas quando o script é rodado diretamente (ex: `python Pipeline/main.py`), e não quando ele é importado como um módulo por outro script.