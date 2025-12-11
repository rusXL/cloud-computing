FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY api ./api
COPY shared ./shared

CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "80"]
