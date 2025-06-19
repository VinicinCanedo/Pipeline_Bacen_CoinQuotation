FROM python:3.11-slim

RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Atualiza o pip e instala o Poetry
RUN pip install --upgrade pip
RUN pip install poetry

# Copia arquivos de dependências E README.md ANTES do poetry install
COPY pyproject.toml poetry.lock README.md ./

# Instala as dependências no ambiente global do container, sem instalar o projeto atual
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --no-root

# Copia o restante do código do projeto
COPY . .

CMD ["python", "Pipeline/consumeAPI.py"]