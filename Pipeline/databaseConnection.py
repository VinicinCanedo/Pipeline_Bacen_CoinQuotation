from supabase import create_client, Client
from dotenv import load_dotenv
import os

# Carrega as variáveis de ambiente do .env
load_dotenv()

# Busca as variáveis de ambiente do Supabase
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")

# Verifica se todas as variáveis foram carregadas
if not all([url, key]):
    print("Erro: SUPABASE_URL ou SUPABASE_KEY não foram definidas. Verifique seu arquivo .env.")
else:
    try:
        # Cria o cliente Supabase
        supabase: Client = create_client(url, key)
        print("Cliente Supabase criado com sucesso.")

        # Testa a conexão lendo um registro da tabela 'DollarQuotation'
        # A chave 'anon' só pode ler dados se a RLS (Row Level Security) permitir
        response = supabase.from_("DollarQuotation").select("*").limit(1).execute()

        # Verifica se a API retornou dados
        if response.data:
            print("Conexão com a API do Supabase e acesso à tabela bem-sucedidos!")
            print("Exemplo de dado:", response.data[0])
        else:
            # Se não houver dados, pode ser uma tabela vazia ou um problema de permissão
            print("Conexão com a API do Supabase bem-sucedida, mas não foi possível ler dados da tabela 'DollarQuotation'.")
            print("Verifique se a tabela não está vazia e se as políticas de RLS permitem leitura para a chave 'anon'.")

    except Exception as e:
        print(f"Falha ao conectar ou executar a operação: {e}")