FROM python:3.7-slim

# Get all main requirements from pip. We need gcc in order to build uwsgi.
RUN apt-get update \
    && apt-get install -y gcc \
    && pip install altair cachelib flask pandas pyarrow pywebpush redis requests uwsgi
RUN mkdir /data
WORKDIR /app
COPY . .
CMD ./start.sh
