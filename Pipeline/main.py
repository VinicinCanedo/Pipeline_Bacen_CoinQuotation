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
    """Transforma os dados brutos, removendo duplicatas antes de enviar ao banco."""
    if not dados_json or "value" not in dados_json:
        print("Nenhum dado para transformar.")
        return []

    print(f"Processando {len(dados_json['value'])} registros brutos...")
    
    # Usa um dicionário para garantir que cada dataHoraCotacao seja única.
    # Se uma chave duplicada aparecer, ela simplesmente substitui a anterior.
    registros_unicos = {}
    for registro in dados_json["value"]:
        chave_unica = registro.get("dataHoraCotacao")
        if chave_unica:  # Garante que o registro tem a chave
            registros_unicos[chave_unica] = {
                "paridadeCompra": registro.get("paridadeCompra"),
                "paridadeVenda": registro.get("paridadeVenda"),
                "cotacaoCompra": registro.get("cotacaoCompra"),
                "cotacaoVenda": registro.get("cotacaoVenda"),
                "dataHoraCotacao": chave_unica,
                "tipoBoletim": registro.get("tipoBoletim")
            }

    # Converte os valores do dicionário de volta para uma lista.
    dados_transformados = list(registros_unicos.values())
    
    print(f"Dados transformados com sucesso! {len(dados_transformados)} registros únicos encontrados.")
    return dados_transformados

def carregar_dados_supabase(supabase_client: Client, dados: list):
    """Verifica quais dados já existem e insere apenas os novos."""
    if not dados:
        print("Nenhum dado para carregar.")
        return

    try:
        # 1. Extrai as chaves (dataHoraCotacao) dos dados que vieram da API
        chaves_para_verificar = [registro['dataHoraCotacao'] for registro in dados]

        # 2. Consulta o banco para ver quais dessas chaves JÁ EXISTEM na tabela
        response = supabase_client.from_("DollarQuotation").select("dataHoraCotacao").in_("dataHoraCotacao", chaves_para_verificar).execute()

        if hasattr(response, 'error') and response.error:
            print(f"Erro ao verificar dados existentes: {response.error}")
            return

        # 3. Cria um conjunto com as chaves que já existem para uma busca rápida
        chaves_existentes = {registro['dataHoraCotacao'] for registro in response.data}

        # 4. Filtra a lista original, mantendo apenas os registros que NÃO estão no banco
        dados_novos = [registro for registro in dados if registro['dataHoraCotacao'] not in chaves_existentes]

        # 5. Verifica o resultado do filtro
        if not dados_novos:
            # Se a lista de dados novos estiver vazia, todos os registros já existem
            print("Os dados já constam na Base de Dados.")
            return
        
        # 6. Se houver dados novos, realiza a inserção deles
        print(f"Carregando {len(dados_novos)} novos registros no Supabase...")
        insert_response = supabase_client.from_("DollarQuotation").insert(dados_novos).execute()

        if hasattr(insert_response, 'error') and insert_response.error:
            print(f"Erro ao carregar novos dados: {insert_response.error}")
        else:
            print("Novos dados carregados com sucesso no Supabase!")

    except Exception as e:
        print(f"Falha na operação com o Supabase: {e}")

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