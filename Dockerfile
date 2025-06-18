FROM python:3.11-slim

# Instala dependências do sistema
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala o Poetry
RUN pip install poetry

# Copia arquivos de dependências
COPY pyproject.toml poetry.lock ./

# Instala as dependências no ambiente global do container
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copia o restante do código do projeto
COPY . .

# Define variável de ambiente para o Poetry não pedir input
ENV POETRY_NO_INTERACTION=1

# Comando padrão (pode ser sobrescrito na execução)
CMD ["python", "pipeline.py"]