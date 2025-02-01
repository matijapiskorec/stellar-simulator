FROM ubuntu:latest
FROM python:3.12-slim

# could be also specified with src folder
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["python", "src/simulator.py"]
ENTRYPOINT ["pytest", "--maxfail=5", "--disable-warnings"]
