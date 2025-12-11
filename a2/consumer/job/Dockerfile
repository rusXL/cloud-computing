FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY job ./job
COPY shared ./shared

CMD ["python", "-m", "job.main", "-u"]
