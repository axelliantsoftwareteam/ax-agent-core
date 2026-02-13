FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE /app/
COPY src /app/src
COPY examples /app/examples

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

CMD ["ax-agent", "run-demo"]
