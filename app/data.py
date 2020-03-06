"""Contains the logic necessary to turn Energinet's data into pandas dataframes."""
from dataclasses import dataclass

import numpy as np
import pandas as pd
import requests

# General parts of the data queries that will be used for all purposes below
BASE_URL = 'https://api.energidataservice.dk/datastore_search'
FIELDS = 'Minutes5UTC,Minutes5DK,CO2Emission'
SORT = 'Minutes5UTC desc'
FILTERS = '{"PriceArea": "DK2"}'
HISTORY_RESOURCE = 'co2emis'
FORECAST_RESOURCE = 'co2emisprog'

@dataclass
class EmissionData:
    df_history: pd.DataFrame
    df_forecast: pd.DataFrame

    @classmethod
    def build(cls):
        """Produces dataframes of emission intensities with 2 days of history and as long a forecast as possible."""
        # The resolution of the data is 5 minutes, so we want (60/5) * 24 * 2 = 576 data points
        limit = 576
        query = f'&fields={FIELDS}&sort={SORT}&limit={limit}&filters={FILTERS}'
        data_history = requests.get(f'{BASE_URL}?resource_id={HISTORY_RESOURCE}{query}').json()
        data_forecast = requests.get(f'{BASE_URL}?resource_id={FORECAST_RESOURCE}{query}').json()
        df_history = pd.DataFrame(data_history['result']['records'])[::-1]
        df_history['Minutes5DK'] = pd.to_datetime(df_history.Minutes5DK).dt.tz_localize('Europe/Copenhagen')
        df_history['Minutes5UTC'] = pd.to_datetime(df_history.Minutes5UTC)
        df_history['Type'] = 'Målt'
        df_forecast = pd.DataFrame(data_forecast['result']['records'])[::-1]
        df_forecast['Minutes5DK'] = pd.to_datetime(df_forecast.Minutes5DK).dt.tz_localize('Europe/Copenhagen')
        df_forecast['Minutes5UTC'] = pd.to_datetime(df_forecast.Minutes5UTC)
        df_forecast['Type'] = 'Prognose'
        df_forecast = df_forecast[df_forecast.Minutes5DK >= df_history.Minutes5DK.max()]
        # Replace forecasted value for current time with actual time, mainly to make it simpler to produce a connected
        # graph below.
        df_forecast.iloc[0] = [df_history.Minutes5UTC.max(),
                               df_history.Minutes5DK.max(),
                               df_history.iloc[-1]['CO2Emission'],
                               'Prognose']
        return cls(df_history, df_forecast)


@dataclass
class EmissionDataQuintiles():
    """Represents quintiles of the complete data, as well as its daily averages, for the last three years."""
    quintiles_all: [float]
    quintiles_daily_averages: [float]

    @classmethod
    def calculate(cls):
        """Calculate the quintiles.
        
        Note that getting all the data can take a long while.
        """
        # We want three years of data or, ignoring leap years, (60/5) * 24 * 365 * 3 = 315360 data points.
        limit = 315360
        data = requests.get(
            f'{BASE_URL}?resource_id={HISTORY_RESOURCE}&fields={FIELDS}&sort={SORT}&limit={limit}').json()
        values = np.array([x['CO2Emission'] for x in data['result']['records']])
        quintiles_all = np.percentile(values, [20, 40, 60, 80])
        daily_averages = values.reshape(24, limit//24).mean(0)
        quintiles_daily_averages = np.percentile(daily_averages, [20, 40, 60, 80])
        return cls(quintiles_all, quintiles_daily_averages)
