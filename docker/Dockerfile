FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY python ./python
COPY examples ./examples
COPY benchmarks ./benchmarks

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

ENTRYPOINT ["1dsra"]
