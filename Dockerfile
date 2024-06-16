# Dockerfile

FROM python:3.10-slim

ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

CMD ["python","-m","uvicorn","file_uploader.asgi:application","--port","8001","--reload"]
