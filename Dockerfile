# Imagem base: Python 3.11 versão slim (menor tamanho)
FROM python:3.11-slim

# Define a pasta de trabalho dentro do container
WORKDIR /app

# Copia e instala as dependências primeiro
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código
COPY . .

# Informa que a aplicação usa a porta 5000
EXPOSE 5000

# Comando que roda quando o container iniciar
CMD ["python", "app.py"]