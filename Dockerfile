FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m pip install --upgrade pip && \
    pip install .

COPY run_pipeline.py export_powerbi.py ./
COPY dax ./dax
COPY tests ./tests

RUN mkdir -p \
    data/raw \
    data/bronze \
    data/silver \
    data/gold \
    powerbi_export

CMD ["python", "run_pipeline.py"]
