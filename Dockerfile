FROM python:3.7-slim

# Get all main requirements from pip. We need gcc in order to build uwsgi.
RUN apt-get update && apt-get install -y gcc
RUN pip install "altair<5" cachelib colorama flask "numpy<1.20" "pandas<2" "pyarrow<2" pywebpush redis requests uwsgi
RUN mkdir /data
WORKDIR /app
COPY . .
CMD ./start.sh
