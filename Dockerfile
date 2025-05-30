FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create data directory
RUN mkdir -p drone_data

EXPOSE 8000

CMD ["gunicorn", "main:app", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"] 