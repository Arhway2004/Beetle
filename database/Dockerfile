# One-shot migration runner. Build from the repository root.
FROM python:3.13-slim
RUN pip install --no-cache-dir "psycopg[binary]>=3.2,<4"
WORKDIR /database
COPY database/migrate.py ./
COPY database/migrations ./migrations
COPY database/seeds ./seeds
RUN useradd --system --uid 10001 app
USER app
ENTRYPOINT ["python", "migrate.py"]
