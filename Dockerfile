FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY examples ./examples

RUN pip install --no-cache-dir .

RUN useradd --create-home --shell /bin/bash appuser
USER appuser

ENTRYPOINT ["ax-agent"]
CMD ["run-demo", "--scripted"]
