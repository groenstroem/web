"""Contains the logic necessary to turn Energinet's data into pandas dataframes."""
from dataclasses import dataclass

import pandas as pd
import requests


@dataclass
class EmissionData:
    df_history: pd.DataFrame
    df_forecast: pd.DataFrame

    @classmethod
    def build(cls):
        """Produces dataframes of emission intensities with 2 days of history and as long a forecast as possible."""
        base_url = 'https://api.energidataservice.dk/datastore_search'
        fields = 'Minutes5UTC,Minutes5DK,CO2Emission'
        sort = 'Minutes5UTC desc'
        limit = 576
        filters = '{"PriceArea": "DK2"}'
        data_history = requests.get(
            f'{base_url}?resource_id=co2emis&fields={fields}&sort={sort}&limit={limit}&filters={filters}').json()
        data_forecast = requests.get(
            f'{base_url}?resource_id=co2emisprog&fields={fields}&sort={sort}&limit={limit}&filters={filters}').json()
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
