FROM python:3.7-slim

RUN apt-get update \
    && apt-get install -y gcc \
    && pip install altair flask pandas==0.25.3 requests uwsgi cachelib redis
WORKDIR /app
COPY . .
CMD ./start.sh
