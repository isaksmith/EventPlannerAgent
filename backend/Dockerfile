FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
COPY skills ./skills
COPY start.sh ./start.sh

RUN pip install --no-cache-dir . && chmod +x start.sh

EXPOSE 8000

CMD ["./start.sh"]
