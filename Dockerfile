FROM python:3.12-slim

WORKDIR /app

# Dependencies installed before the code to exploit Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# --reload: hot-reload in development (the code is bind-mounted by docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
