"""Manages the web application cache.

We use Redis throughout to cache the main time-consuming parts of the web application's work. In particular,
we ensure that we will only generate new data (thus hit Energinet) only when what we have is getting stale.
"""
import time

from cachelib import RedisCache
import pyarrow as pa

from .model import build_model, build_current_generation_mix

# We hardcode the Redis hostname 'redis', matching what we get if we use Docker Compose to spin up the app.
REDIS_HOSTNAME = 'redis'

# Define identifiers used as keys for Redis throughout.
EMISSION_INTENSITY_MODEL_IDENTIFIER = 'emission-intensity-model'
EMISSION_INTENSITY_GENERATING_IDENTIFIER = 'emission-intensity-model-generating'
FORECAST_IDENTIFIER = 'emission-intensity-forecast'

GENERATION_MIX_IDENTIFIER = 'generation-mix-model'
GENERATION_MIX_GENERATING_IDENTIFIER = 'generation-mix-model-generating'

# For the emission intensity data model, we will use the same five minute timeout for all cache values. Energinet's data
# is updated about every 10-15 minutes, so this way we'll always be mostly fresh. For the generation mix, the data is
# updated only roughly once per hour, so there we can do with updating only every half hour.
EMISSION_INTENSITY_TIMEOUT = 5 * 60
GENERATION_MIX_TIMEOUT = 30 * 60

cache = RedisCache(REDIS_HOSTNAME)


def get_model():
    # Before getting the data from the cache (or recreating it if necessary), we ensure that no other thread is in the
    # process of generating data. This way, we avoid having two threads generating the same data.
    _wait_until_not_generating(EMISSION_INTENSITY_GENERATING_IDENTIFIER)
    model = cache.get(EMISSION_INTENSITY_MODEL_IDENTIFIER)
    if model:
        return model
    model, _ = _update_data()
    return model


def get_forecast():
    _wait_until_not_generating(EMISSION_INTENSITY_GENERATING_IDENTIFIER)
    forecast = cache.get(FORECAST_IDENTIFIER)
    if forecast:
        return pa.deserialize(forecast)
    _, forecast = _update_data()
    return forecast


def _wait_until_not_generating(identifier):
    """This sleeps until data is no longer being generated and added to the cache.

    The use of this is for the cases where we want to make sure that we do not spin up more than one process for
    adding data to the cache at a time. The identifier is a Redis key pointing to a boolean describing whether or not
    the relevant data is currently being generated.
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
        cache.set(EMISSION_INTENSITY_GENERATING_IDENTIFIER, True)
        model, forecast = build_model()
        cache.set(EMISSION_INTENSITY_MODEL_IDENTIFIER, model, timeout=EMISSION_INTENSITY_TIMEOUT)
        serialized = pa.serialize(forecast).to_buffer()
        cache.set(FORECAST_IDENTIFIER, serialized, timeout=EMISSION_INTENSITY_TIMEOUT)
        return model, forecast
    finally:
        cache.delete(EMISSION_INTENSITY_GENERATING_IDENTIFIER)


def get_current_generation_mix():
    _wait_until_not_generating(GENERATION_MIX_GENERATING_IDENTIFIER)
    current_generation_mix = cache.get(GENERATION_MIX_IDENTIFIER)
    if current_generation_mix:
        return current_generation_mix
    try:
        cache.set(GENERATION_MIX_GENERATING_IDENTIFIER, True)
        current_generation_mix = build_current_generation_mix()
        cache.set(GENERATION_MIX_IDENTIFIER, current_generation_mix, timeout=GENERATION_MIX_TIMEOUT)
        return current_generation_mix
    finally:
        cache.delete(GENERATION_MIX_GENERATING_IDENTIFIER)
