FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY iei/ /app/iei/
COPY frontend/ /app/frontend/
COPY data/sources/ /app/data/sources/
ENV PYTHONUNBUFFERED=1
