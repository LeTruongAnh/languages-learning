FROM python:3.12-slim

WORKDIR /app

# Non-root user
RUN addgroup --system app && adduser --system --ingroup app app

COPY pyproject.toml ./
RUN pip install --no-cache-dir . && pip cache purge

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

USER app
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
