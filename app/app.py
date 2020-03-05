import os
import sqlite3
import time
import warnings
# We disable FutureWarnings caused by Pandas 0.25.3 instructing us to replace our msgpack based deserialization with
# pyarrow. Unfortunately, pyarrow has a bug making its usage impossible for our use cases, so we stick to msgpack, but
# don't want to flood ourselves with warnings.
warnings.simplefilter(action='ignore', category=FutureWarning)

from cachelib import RedisCache
from flask import Flask, request
import pandas as pd

from .model import build_model, best_hour, overview_next_day


app = Flask(__name__,
            static_url_path='',
            static_folder='static')

# We hardcode the Redis hostname 'redis', matching what we get if we use Docker Compose to spin up the app.
cache = RedisCache('redis')

# Define identifiers used as keys for Redis throughout.
model_identifier = 'emission-intensity-model'
generating_identifier = 'emission-intensity-model-generating'
forecast_identifier = 'emission-intensity-forecast'


def execute_sql(sql, args):
    try:
        conn = sqlite3.connect('/data/subs.db')
        c = conn.cursor()
        c.execute(sql, args)
        conn.commit()
    finally:
        if conn:
            conn.close


db_exists = os.path.exists('/data/subs.db')

if not db_exists:
    execute_sql('CREATE TABLE subs (sub text)', [])


def wait_until_not_generating():
    """This sleeps until data is no longer being generated and added to the cache.

    The use of this is for the cases where we want to make sure that we do not spin up more than one process for
    adding data to the cache at a time.
    """
    counter = 0
    while True:
        generating = cache.get(generating_identifier)
        if not generating:
            break
        if counter > 50:
            raise RuntimeError('timeout while waiting for data to be generated')
        time.sleep(0.1)
        counter += 1


def update_data():
    """Generates all model data and caches the result for five minutes."""
    try:
        cache.set(generating_identifier, True)
        model, forecast = build_model()
        cache.set(model_identifier, model, timeout=5*60)
        cache.set(forecast_identifier, forecast.to_msgpack(compress='zlib'), timeout=5*60)
        return model, forecast
    finally:
        cache.delete(generating_identifier)


@app.route('/')
def root():
    return app.send_static_file('index.html')


@app.route('/api/v1/current-emission-intensity')
def current_emission_intensity():
    # Before getting the data from the cache (or recreating it if necessary), we ensure that no other thread is in the
    # process of generating data. This way, we avoid having two threads generating the same data.
    wait_until_not_generating()
    model = cache.get(model_identifier)
    if model:
        return model
    model, _ = update_data()
    return model


@app.route('/api/v1/greenest-period/<period>/<horizon>', methods=['GET'])
def greenest_hour(period, horizon):
    period = int(period)
    horizon = int(horizon)
    wait_until_not_generating()
    forecast = cache.get(forecast_identifier)
    if forecast:
        return best_hour(pd.read_msgpack(forecast), period, horizon)
    _, forecast = update_data()
    return best_hour(forecast, period, horizon)

@app.route('/api/v1/next-day')
def next_day():
    wait_until_not_generating()
    forecast = cache.get(forecast_identifier)
    if forecast:
        return overview_next_day(pd.read_msgpack(forecast))
    _, forecast = update_data()
    return overview_next_day(forecast)

@app.route('/api/v1/save-subscription', methods=['POST'])
def save_subscription():
    data = request.data.decode('ascii')
    execute_sql('INSERT INTO subs (sub) VALUES (?)', (data,))
    return {'message': 'success'}


@app.route('/api/v1/remove-subscription', methods=['POST'])
def remove_subscription():
    data = request.data.decode('ascii')
    execute_sql('DELETE FROM subs WHERE sub = ?', (data,))
    return {'message': 'success'}
