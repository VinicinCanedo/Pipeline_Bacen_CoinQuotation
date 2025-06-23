import os
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

def extrair_dados_bacen():
    """Extrai os dados da API do BACEN para o período definido."""
    print("Iniciando extração de dados da API do BACEN...")
    url = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?@moeda='EUR'&@dataInicial='06-01-2025'&@dataFinalCotacao='07-31-2025'&$orderby=dataHoraCotacao%20desc&$format=json"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Lança um erro para status HTTP 4xx/5xx
        print("Dados extraídos com sucesso!")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao extrair dados da API: {e}")
        return None

def transformar_dados(dados_json):
    """Transforma os dados brutos da API em um formato limpo para o banco de dados."""
    if not dados_json or "value" not in dados_json:
        print("Nenhum dado para transformar.")
        return []

    print(f"Transformando {len(dados_json['value'])} registros...")
    dados_transformados = []
    for registro in dados_json["value"]:
        dados_transformados.append({
            "paridadeCompra": registro.get("paridadeCompra"),
            "paridadeVenda": registro.get("paridadeVenda"),
            "cotacaoCompra": registro.get("cotacaoCompra"),
            "cotacaoVenda": registro.get("cotacaoVenda"),
            "dataHoraCotacao": registro.get("dataHoraCotacao"),
            "tipoBoletim": registro.get("tipoBoletim")
        })
    print("Dados transformados com sucesso!")
    return dados_transformados

def carregar_dados_supabase(supabase_client: Client, dados: list):
    """Carrega os dados transformados na tabela do Supabase."""
    if not dados:
        print("Nenhum dado para carregar.")
        return

    print(f"Carregando {len(dados)} registros no Supabase...")
    try:
        # O método insert pode receber uma lista de dicionários diretamente
        response = supabase_client.from_("DollarQuotation").upsert(dados).execute()
        
        # Verifica se houve erro na resposta da API
        if hasattr(response, 'error') and response.error:
            print(f"Erro ao carregar dados: {response.error}")
        else:
            print("Dados carregados com sucesso no Supabase!")

    except Exception as e:
        print(f"Falha ao carregar dados no Supabase: {e}")

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

    # 2. Extração
    dados_brutos = extrair_dados_bacen()
    if not dados_brutos:
        return

    # 3. Transformação
    dados_para_inserir = transformar_dados(dados_brutos)
    if not dados_para_inserir:
        return

    # 4. Carga
    carregar_dados_supabase(supabase, dados_para_inserir)
    
    print("--- Pipeline ETL finalizado ---")

if __name__ == "__main__":
    main()