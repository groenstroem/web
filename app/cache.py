"""Manages the web application cache.

We use Redis throughout to cache the main time-consuming parts of the web application's work. In particular,
we ensure that we will only generate new data (thus hit Energinet) only when what we have is getting stale.
"""
import time

from cachelib import RedisCache
import pandas as pd

from .model import build_model, build_current_generation_mix

# We hardcode the Redis hostname 'redis', matching what we get if we use Docker Compose to spin up the app.
REDIS_HOSTNAME = 'redis'

# Define identifiers used as keys for Redis throughout.
MODEL_IDENTIFIER = 'emission-intensity-model'
GENERATING_IDENTIFIER = 'emission-intensity-model-generating'
FORECAST_IDENTIFIER = 'emission-intensity-forecast'

GENERATION_MIX_IDENTIFIER = 'generation-mix-model'
GENERATION_MIX_GENERATING_IDENTIFIER = 'generation-mix-model-generating'

# Use the same five minute timeout for all cache values. Energinet's data is updated about every 10-15 minutes,
# so this way we'll always be mostly fresh.
TIMEOUT = 5*60

cache = RedisCache(REDIS_HOSTNAME)


def get_model():
    # Before getting the data from the cache (or recreating it if necessary), we ensure that no other thread is in the
    # process of generating data. This way, we avoid having two threads generating the same data.
    _wait_until_not_generating(GENERATING_IDENTIFIER)
    model = cache.get(MODEL_IDENTIFIER)
    if model:
        return model
    model, _ = _update_data()
    return model


def get_forecast():
    _wait_until_not_generating(GENERATING_IDENTIFIER)
    forecast = cache.get(FORECAST_IDENTIFIER)
    if forecast:
        return pd.read_msgpack(forecast)
    _, forecast = _update_data()
    return forecast


def _wait_until_not_generating(identifier):
    """This sleeps until data is no longer being generated and added to the cache.

    The use of this is for the cases where we want to make sure that we do not spin up more than one process for
    adding data to the cache at a time.
    """
    counter = 0
    while True:
        generating = cache.get(identifier)
        if not generating:
            break
        if counter > 100:
            raise RuntimeError('timeout while waiting for data to be generated')
        time.sleep(0.1)
        counter += 1


def _update_data():
    """Generates all model data and caches the result for five minutes."""
    try:
        cache.set(GENERATING_IDENTIFIER, True)
        model, forecast = build_model()
        cache.set(MODEL_IDENTIFIER, model, timeout=TIMEOUT)
        cache.set(FORECAST_IDENTIFIER, forecast.to_msgpack(compress='zlib'), timeout=TIMEOUT)
        return model, forecast
    finally:
        cache.delete(GENERATING_IDENTIFIER)


def get_current_generation_mix():
    _wait_until_not_generating(GENERATION_MIX_GENERATING_IDENTIFIER)
    current_generation_mix = cache.get(GENERATION_MIX_IDENTIFIER)
    if current_generation_mix:
        return current_generation_mix
    try:
        cache.set(GENERATION_MIX_GENERATING_IDENTIFIER, True)
        current_generation_mix = build_current_generation_mix()
        cache.set(GENERATION_MIX_IDENTIFIER, current_generation_mix, timeout=30*60)
        return current_generation_mix
    finally:
        cache.delete(GENERATION_MIX_GENERATING_IDENTIFIER)
