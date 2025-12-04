FROM python:3.12-alpine

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

# copy build deps
COPY pyproject.toml README.md ./
COPY src ./src
# hubcast default logging config
COPY logging_config.json ./

# create venv and build hubcast and deps
RUN python -m venv /venv \
 && /venv/bin/pip install --upgrade pip setuptools wheel \
 && /venv/bin/pip install --no-cache-dir /app \
 && rm -rf /root/.cache /tmp/*

ENV PATH="/venv/bin:$PATH"
ENTRYPOINT ["python", "-m", "hubcast"]
