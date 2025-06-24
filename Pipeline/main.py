import os
import requests
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime, timedelta

def obter_data_mais_recente(supabase_client: Client) -> str:
    """Busca a data mais recente dos registros no Supabase para definir o início da próxima extração."""
    print("Buscando a data mais recente na base de dados...")
    try:
        # Ordena por dataHoraCotacao em ordem decrescente e pega o primeiro registro
        response = supabase_client.from_("DollarQuotation").select("dataHoraCotacao").order("dataHoraCotacao", desc=True).limit(1).execute()

        if response.data:
            # Extrai a data do registro mais recente
            data_recente_str = response.data[0]['dataHoraCotacao']
            # Converte a string para um objeto datetime
            data_recente = datetime.fromisoformat(data_recente_str)
            # Adiciona um dia para evitar buscar o último dia novamente
            proxima_data = data_recente + timedelta(days=1)
            # Formata a data para o formato exigido pela API do BACEN (MM-DD-YYYY)
            data_formatada = proxima_data.strftime('%m-%d-%Y')
            print(f"Última data encontrada: {data_recente_str}. A extração continuará a partir de {data_formatada}.")
            return data_formatada
        else:
            # Caso a tabela esteja vazia, define uma data de início padrão
            print("Nenhum registro encontrado. Usando data de início padrão: 01-01-2024.")
            return "06-01-2025"
    except Exception as e:
        print(f"Erro ao buscar data mais recente: {e}. Usando data de início padrão.")
        return "06-01-2025"

def extrair_dados_bacen(data_inicial: str):
    """Extrai os dados da API do BACEN a partir de uma data inicial até a data atual."""
    print(f"Iniciando extração de dados da API do BACEN a partir de {data_inicial}...")
    # Define a data final como a data de hoje
    data_final = datetime.now().strftime('%m-%d-%Y')
    
    # Monta a URL da API dinamicamente com as datas
    url = f"https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?@moeda='USD'&@dataInicial='{data_inicial}'&@dataFinalCotacao='{data_final}'&$orderby=dataHoraCotacao%20desc&$format=json"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Lança um erro para status HTTP 4xx/5xx
        print("Dados extraídos com sucesso!")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao extrair dados da API: {e}")
        return None

def transformar_dados(dados_json):
    """Transforma os dados brutos, removendo duplicatas da mesma carga."""
    if not dados_json or "value" not in dados_json or not dados_json["value"]:
        print("Nenhum dado para transformar.")
        return []

    print(f"Processando {len(dados_json['value'])} registros brutos...")
    
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

    dados_transformados = list(registros_unicos.values())
    print(f"Dados transformados com sucesso! {len(dados_transformados)} registros únicos encontrados.")
    return dados_transformados

def carregar_dados_supabase(supabase_client: Client, dados: list):
    """Verifica quais dados já existem no banco e insere apenas os novos."""
    if not dados:
        print("Nenhum dado para carregar.")
        return

    try:
        chaves_api = {registro['dataHoraCotacao'] for registro in dados}
        
        # Consulta o banco para ver quais dessas chaves JÁ EXISTEM na tabela
        response = supabase_client.from_("DollarQuotation").select("dataHoraCotacao").in_("dataHoraCotacao", list(chaves_api)).execute()

        if hasattr(response, 'error') and response.error:
            print(f"Erro ao verificar dados existentes no Supabase: {response.error}")
            return

        chaves_existentes = {registro['dataHoraCotacao'] for registro in response.data}
        
        # Filtra a lista original, mantendo apenas os registros que NÃO estão no banco
        dados_novos = [registro for registro in dados if registro['dataHoraCotacao'] not in chaves_existentes]

        if not dados_novos:
            print("Todos os dados extraídos já constam na base. Nenhuma inserção necessária.")
            return
        
        print(f"Carregando {len(dados_novos)} novos registros no Supabase...")
        insert_response = supabase_client.from_("DollarQuotation").insert(dados_novos).execute()

        if hasattr(insert_response, 'error') and insert_response.error:
            print(f"Erro ao carregar novos dados no Supabase: {insert_response.error}")
        else:
            print("Novos dados carregados com sucesso!")

    except Exception as e:
        print(f"Falha na operação de carga com o Supabase: {e}")

def main():
    """Função principal que orquestra o pipeline ETL."""
    print("--- Iniciando Pipeline ETL de Cotações ---")
    
    # Carrega as variáveis de ambiente
    load_dotenv()
    url: str = os.getenv("SUPABASE_URL")
    key: str = os.getenv("SUPABASE_KEY")

    if not all([url, key]):
        print("Erro: SUPABASE_URL ou SUPABASE_KEY não definidas no .env.")
        return

    # 1. Conexão com Supabase
    try:
        supabase: Client = create_client(url, key)
        print("Cliente Supabase criado com sucesso.")
    except Exception as e:
        print(f"Falha ao criar cliente Supabase: {e}")
        return

    # 2. Obtenção da data de início para a extração
    data_inicio_extracao = obter_data_mais_recente(supabase)

    # 3. Extração
    dados_brutos = extrair_dados_bacen(data_inicio_extracao)
    # Verifica se a extração retornou dados e se a lista 'value' não está vazia
    if not dados_brutos or not dados_brutos.get("value"):
        print("Nenhum dado novo foi extraído da API do BACEN. Finalizando pipeline.")
        return

    # 4. Transformação
    dados_para_inserir = transformar_dados(dados_brutos)
    if not dados_para_inserir:
        print("Nenhum dado novo para inserir após a transformação. Finalizando pipeline.")
        return

    # 5. Carga
    carregar_dados_supabase(supabase, dados_para_inserir)
    
    print("--- Pipeline ETL finalizado ---")

if __name__ == "__main__":
    main()