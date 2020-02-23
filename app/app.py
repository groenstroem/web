import time

from cachelib import RedisCache
from flask import Flask

from .model import build_model


app = Flask(__name__,
            static_url_path='',
            static_folder='static')
cache = RedisCache('redis')


@app.route('/')
def root():
    return app.send_static_file('index.html')


@app.route('/api/v1/current-emission-intensity')
def current_emission_intensity():
    model_identifier = 'emission-intensity-model'
    generating_identifier = 'emission-intensity-model-generating'
    # If someone is in the process of generating data, wait for them to finish.
    counter = 0
    while True:
        generating = cache.get(generating_identifier)
        if not generating:
            break
        if counter > 50:
            raise RuntimeError('timeout while waiting for data to be generated')
        time.sleep(0.1)
        counter += 1
    model = cache.get(model_identifier)
    if model:
        return model
    try:
        cache.set(generating_identifier, True)
        model = build_model()
        cache.set(model_identifier, model, timeout=5*60)
        return model
    finally:
        cache.delete(generating_identifier)
