FROM python:3.7-slim

# Get all main requirements from pip. We need gcc in order to build uwsgi. Moreover, we pin the version
# of pandas to ensure that we have msgpack serialization available; this was deprecated in favor of
# pyarrow serialization in pandas 1.0.0, but pyarrow is buggy enough that our use case, serlaizing time series
# data frames, is still not possible.
RUN apt-get update \
    && apt-get install -y gcc \
    && pip install altair cachelib flask pandas==0.25.3 pywebpush redis requests uwsgi
RUN mkdir /data
WORKDIR /app
COPY . .
CMD ./start.sh
