FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY plugins ./plugins
COPY deploy/replio-entrypoint.sh ./replio-entrypoint.sh

RUN pip install --no-cache-dir .

ENV REPLIO_HOST=0.0.0.0
ENV REPLIO_PORT=8787

EXPOSE 8787

ENTRYPOINT ["./replio-entrypoint.sh"]
