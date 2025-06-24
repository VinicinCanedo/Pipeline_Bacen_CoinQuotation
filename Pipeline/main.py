import os
import requests
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime, timedelta

# Define a data mínima para o início da extração.
# O formato é 'MM-DD-YYYY' para consistência com a API do BACEN.
MIN_START_DATE = "04-01-2025"

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