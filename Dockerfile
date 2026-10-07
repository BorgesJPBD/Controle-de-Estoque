# Imagem base: Python 3.11 versão slim (menor tamanho)
FROM python:3.11-slim

# Logs aparecem na hora e o Python não grava arquivos .pyc
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Define a pasta de trabalho dentro do container
WORKDIR /app

# Copia e instala as dependências primeiro (aproveita o cache do Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código
COPY . .

# Roda a aplicação com um usuário sem privilégios de administrador
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

# Informa que a aplicação usa a porta 5000
EXPOSE 5000

# Servidor de produção (Gunicorn) no lugar do servidor de desenvolvimento do Flask.
# --preload: cria/atualiza as tabelas uma única vez antes de iniciar os workers.
CMD ["gunicorn", "--preload", "--workers", "2", "--threads", "4", "--bind", "0.0.0.0:5000", "--access-logfile", "-", "app:app"]
