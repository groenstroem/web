"""Contains the logic necessary to turn Energinet's data into pandas dataframes."""
from dataclasses import dataclass

import numpy as np
import pandas as pd
import requests

# General parts of the data queries that will be used for all purposes below
BASE_URL = 'https://api.energidataservice.dk/dataset/'
EMISSION_INTENSITY_FILTERS = '{"PriceArea": "DK2"}'
GENERATION_MIX_FIELDS = 'HourDK,TotalLoad,Biomass,FossilGas,FossilHardCoal,FossilOil,HydroPower,OtherRenewable,' \
                      'SolarPower,Waste,OnshoreWindPower,OffshoreWindPower,ExchangeContinent,ExchangeGreatBelt,' \
                      'ExchangeNordicCountries'
GENERATION_MIX_SORT = 'HourUTC desc'
HISTORY_RESOURCE = 'co2emis'
FORECAST_RESOURCE = 'co2emisprog'
EMISSION_MIX_RESOURCE = 'electricitybalancenonv'


@dataclass
class EmissionData:
    df_history: pd.DataFrame
    df_forecast: pd.DataFrame

    @classmethod
    def build(cls):
        """Produces data frames of emission intensities with 2 days of history and as long a forecast as possible."""
        # The resolution of the data is 5 minutes, so we want (60/5) * 24 * 2 = 576 data points
        limit = 576
        query = f'?limit={limit}&filter={EMISSION_INTENSITY_FILTERS}'
        data_history = requests.get(f'{BASE_URL}/{HISTORY_RESOURCE}{query}').json()
        data_forecast = requests.get(f'{BASE_URL}/{FORECAST_RESOURCE}{query}').json()
        df_history = pd.DataFrame(data_history['records'])[::-1]
        df_history['Minutes5DK'] = pd.to_datetime(df_history.Minutes5DK).dt.tz_localize('Europe/Copenhagen', ambiguous='NaT')
        df_history['Minutes5UTC'] = pd.to_datetime(df_history.Minutes5UTC)
        df_history['Type'] = 'Målt'
        df_history = df_history.drop(['PriceArea'], axis=1)
        df_forecast = pd.DataFrame(data_forecast['records'])[::-1]
        df_forecast['Minutes5DK'] = pd.to_datetime(df_forecast.Minutes5DK).dt.tz_localize('Europe/Copenhagen', ambiguous='NaT')
        df_forecast['Minutes5UTC'] = pd.to_datetime(df_forecast.Minutes5UTC)
        df_forecast['Type'] = 'Prognose'
        df_forecast = df_forecast.drop(['PriceArea'], axis=1)
        df_forecast = df_forecast[df_forecast.Minutes5DK >= df_history.Minutes5DK.max()]
        # Replace forecasted value for current time with actual time, mainly to make it simpler to produce a connected
        # graph below.
        df_forecast.iloc[0] = [df_history.Minutes5UTC.max(),
                               df_history.Minutes5DK.max(),
                               df_history.iloc[-1]['CO2Emission'],
                               'Prognose']
        return cls(df_history, df_forecast)


@dataclass
class EmissionDataQuintiles:
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
        query = f'?limit={limit}'
        data = requests.get(f'{BASE_URL}/{HISTORY_RESOURCE}{query}').json()
        values = np.array([x['CO2Emission'] for x in data['records']])
        quintiles_all = np.percentile(values, [20, 40, 60, 80])
        daily_averages = values.reshape(24, limit//24).mean(0)
        quintiles_daily_averages = np.percentile(daily_averages, [20, 40, 60, 80])
        return cls(quintiles_all, quintiles_daily_averages)


@dataclass
class GenerationMixData:
    df_mix: pd.DataFrame

    @classmethod
    def build(cls):
        """Produces a data frame describing the most recent generation mix in Denmark."""
        # Arguably, it's a bit silly to keep track of a dataclass containing only a single attribute, and we do so only
        # for consistency with how we handle data elsewhere.
        # The production is split into the two Danish zones, so we'll want to pick  out the top two rows. Now, for
        # whatever reason, it very often happens that those two rows are a bunch of None's, in which case we'll want to
        # pick out the /next/ two rows. We therefore take the first four rows, and check which ones to use.9
        query = f'?fields={GENERATION_MIX_FIELDS}&sort={GENERATION_MIX_SORT}&limit=4'
        response = requests.get(f'{BASE_URL}/{EMISSION_MIX_RESOURCE}{query}').json()
        df = pd.DataFrame(response['records'])
        df_mix = df.iloc[2:] if pd.isna(df.iloc[0].TotalLoad) else df.iloc[:2]
        return cls(df_mix)
