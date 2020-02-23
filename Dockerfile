FROM python:3.7-slim

RUN apt-get update \
    && apt-get install -y gcc \
    && pip install altair flask pandas requests uwsgi cachelib redis
WORKDIR /app
COPY . .
CMD ./start.sh
