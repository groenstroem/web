import time
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

from cachelib import RedisCache
from flask import Flask
import pandas as pd

from .model import build_model, best_hour


app = Flask(__name__,
            static_url_path='',
            static_folder='static')
cache = RedisCache('redis')

model_identifier = 'emission-intensity-model'
generating_identifier = 'emission-intensity-model-generating'
forecast_identifier = 'emission-intensity-forecast'


@app.route('/')
def root():
    return app.send_static_file('index.html')


@app.route('/api/v1/current-emission-intensity')
def current_emission_intensity():
    wait_until_not_generating()
    model = cache.get(model_identifier)
    if model:
        return model
    model, _ = update_data()
    return model


def wait_until_not_generating():
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
    try:
        cache.set(generating_identifier, True)
        model, forecast = build_model()
        cache.set(model_identifier, model, timeout=5*60)
        cache.set(forecast_identifier, forecast.to_msgpack(compress='zlib'), timeout=5*60)
        return model, forecast
    finally:
        cache.delete(generating_identifier)


@app.route('/api/v1/greenest-hour/<period>/<horizon>', methods=['GET'])
def greenest_hour(period, horizon):
    period = int(period)
    horizon = int(horizon)
    wait_until_not_generating()
    forecast = cache.get(forecast_identifier)
    if forecast:
        return best_hour(pd.read_msgpack(forecast), period, horizon)
    _, forecast = update_data()
    return best_hour(forecast, period, horizon)
