import requests

def extrair():
    url = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?@moeda='EUR'&@dataInicial='06-01-2025'&@dataFinalCotacao='07-31-2025'&$orderby=dataHoraCotacao%20desc&$format=json"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        print("Dados Acessados com Sucesso:")
        return data

def transformar(dados_json):
    # A API retorna os dados em 'value', que é uma lista
    if not dados_json or "value" not in dados_json or not dados_json["value"]:
        print("Nenhum dado encontrado.")
        return None

    # Pegando o primeiro registro da lista
    registro = dados_json["value"][0]

    dados_transformados = {
        "paridadeCompra": registro.get("paridadeCompra"),
        "paridadeVenda": registro.get("paridadeVenda"),
        "cotacaoCompra": registro.get("cotacaoCompra"),
        "cotacaoVenda": registro.get("cotacaoVenda"),
        "dataHoraCotacao": registro.get("dataHoraCotacao"),
        "tipoBoletim": registro.get("tipoBoletim")
    }

    return dados_transformados

if __name__ == "__main__":
    dados_json = extrair()
    if dados_json:
        dados_transformados = transformar(dados_json)
        if dados_transformados:
            print("Dados Transformados:")
            print(dados_transformados)
    else:
        print("Falha ao acessar os dados.")