FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOME=/app
ENV TMPDIR=/tmp

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . /app/

RUN addgroup --system django \
    && adduser --system --ingroup django --home /app django \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R django:django /app

USER django

EXPOSE 8000

ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]