"""Contains the model (in the MVC sense) of the data presented in the web app.

In particular, this provides all post-processing of Energinet's data.
"""
from bisect import bisect
from collections import namedtuple
import math
import datetime

import altair as alt
import numpy as np
import pandas as pd

from .data import EmissionData, GenerationMixData


class EmissionIntensityModel:

    def __init__(self):
        self.data = EmissionData.build()
        self.forecast_length_hours = math.ceil(len(self.data.df_forecast) / 12)
        self.df = pd.concat([self.data.df_history, self.data.df_forecast])
        self.now_utc_int = self.data.df_history.Minutes5UTC.astype(int).max() / 1000000
        self.min_time = self.df.Minutes5DK.min()
        self.max_time = self.df.Minutes5DK.max()
        self.now = self.data.df_history.Minutes5DK.max()
        self.current_emission = int(self.data.df_forecast.iloc[0].CO2Emission)

    # Hardcoded quintiles of data distribution. These can be obtained through EmissionDataQuintiles,
    # but doing so takes so long that we'll want to cache the result (and hardcoding them is easier
    # than obtaining them from storage).
    quintiles = [0, 68, 112, 158, 227, 1000]

    def plot(self):
        df_combined = self.df
        m = self.now_utc_int

        start = m - 3600 * 1000 * 12
        max_time_unix = self.df.Minutes5UTC.astype(int).max() / 1000000
        end = min(m + 3600 * 1000 * 12, max_time_unix)
        # Convert np.int64 to int to ensure that result is JSON serializable
        height = max(250, int(df_combined.CO2Emission.max()) + 25)
        today = pd.DataFrame({'x': [self.now, self.now], 'y': [0, self.quintiles[-1]]})
        rects = [pd.DataFrame(
            {'x': [self.min_time], 'y': [self.quintiles[i]], 'x2': [self.max_time], 'y2': [self.quintiles[i+1]]})
            for i in range(5)]

        interval = alt.selection_interval(encodings=['x'],
                                          init={'x': [int(start), int(end)]})

        base = alt.Chart(df_combined).mark_line(strokeWidth=4).encode(
            alt.X('Minutes5DK:T', title=''),
            alt.Y('CO2Emission:Q', title='Udledningsintensitet [g CO2/kWh]', scale=alt.Scale(domain=(0, height))),
            alt.Color('Type:N'),
            tooltip=[alt.Tooltip('Minutes5DK:T', title='Tid', format='%Y-%m-%d %H:%M'),
                     alt.Tooltip('CO2Emission:Q', title='Intensitet [g CO2/kWh]')]
        )

        today_line = alt.Chart(today).mark_rule(clip=True).encode(x='x:T', y='y:Q')
        today_chart = alt.Chart(today).mark_rule(clip=True).encode(
            x=alt.X('x:T', scale=alt.Scale(domain=interval.ref())), y='y:Q')
        opacity = 0.15

        def make_rect(data, color):
            return alt.Chart(data).mark_rect(color=color, opacity=opacity).encode(
                x=alt.X('x:T', scale=alt.Scale(domain=interval.ref())), x2='x2:T', y='y:Q', y2='y2:Q')

        rect_charts = [make_rect(data, color)
                       for data, color in zip(rects, ['green', 'lightgreen', 'yellow', 'lightcoral', 'red'])]
        combined_rect_chart = rect_charts[0] + rect_charts[1] + rect_charts[2] + rect_charts[3] + rect_charts[4]
        top = base.properties(width='container', height=300) \
            .encode(x=alt.X('Minutes5DK:T',
                            axis=alt.Axis(format='%H'),
                            title='',
                            scale=alt.Scale(domain=interval.ref())))

        chart = top + today_chart + combined_rect_chart
        view = base.properties(width='container', height=50, selection=interval).encode(
            x=alt.X('Minutes5DK:T', axis=alt.Axis(format='%d/%m %H:%M'), title=''),
            y=alt.Y('CO2Emission:Q', title='', scale=alt.Scale(domain=(0, height))))

        full_chart = chart & (view + today_line)

        return full_chart.configure_axis(
            titleX=-25,
            titleY=-20,
            titleAlign='left',
            titleAngle=0,
            titleFont='Inter Regular',
            titleFontWeight='normal',
            titleFontSize=16,
            labelFont='Inter Regular',
        ).configure_legend(
            title=None,
            orient='top-right',
            labelFont='Inter Regular',
            labelFontSize=13
        )


def get_greenest(df_forecast, period: int, horizon: int):
    return get_extreme(df_forecast, period, horizon, False)


def get_blackest(df_forecast, period: int, horizon: int):
    return get_extreme(df_forecast, period, horizon, True)


def get_extreme(df_forecast, period: int, horizon: int, idxmax: bool):
    """Given forecast data, determines the greenest/blackest period of a given length in the given horizon."""
    df_next_day = df_forecast[df_forecast.Minutes5UTC < df_forecast.Minutes5UTC.min() + pd.Timedelta(f'{horizon}H')]
    min_periods = period * 12
    rolling = df_next_day.set_index('Minutes5DK').CO2Emission\
                         .rolling(f'{period}H', min_periods=min_periods).mean()[min_periods-1:]
    lowest = rolling.idxmax() if idxmax else rolling.idxmin()
    lowest_mean = rolling.loc[lowest]
    lowest_interval_start = lowest - pd.Timedelta(f'{period}H') + pd.Timedelta('5m')
    lowest_interval_end = lowest + pd.Timedelta('5m')
    return lowest_mean, lowest_interval_start, lowest_interval_end


def build_model():
    model = EmissionIntensityModel()
    full_chart = model.plot()
    latest_data = model.now.strftime('%Y-%m-%d %H:%M')
    current_emission = model.current_emission
    quintiles = model.quintiles
    index = bisect(quintiles, current_emission) - 1
    bg_colors = [f'rgba(0, {i}, 0, 0.9)' for i in range(128, -32, -32)]
    border_colors = [f'rgba(0, {i+64}, 0, 0.9)' for i in range(128, 0, -32)] + ['#333']
    fg_colors = ['#FFF', '#FFF', '#EEE', '#EEE', '#EEE']
    levels = ['MEGET GRØN', 'GRØN', 'BÅDE GRØN OG SORT', 'PRIMÆRT SORT', 'KULSORT']
    emission_intensity = {'success': True,
                          'current-intensity': current_emission,
                          'intensity-level-bgcolor': bg_colors[index],
                          'intensity-level-fgcolor': fg_colors[index],
                          'intensity-level-border-color': border_colors[index],
                          'intensity-level': levels[index],
                          'forecast-length-hours': model.forecast_length_hours,
                          'latest-data': latest_data,
                          'plot-data': full_chart.to_dict()}
    return emission_intensity, model.data.df_forecast


# We explicitly keep track of all energy types that can appear in Energinet generation mix data.
EnergyType = namedtuple('EnergyType', ['danish_name', 'renewable'])

energy_types = {'Biomass': EnergyType('Biomasse', True),
                'FossilGas': EnergyType('Naturgas', False),
                'FossilHardCoal': EnergyType('Kul', False),
                'FossilOil': EnergyType('Olie', False),
                'HydroPower': EnergyType('Vandkraft', True),
                'OtherRenewable': EnergyType('Anden vedvarende', True),
                'SolarPower': EnergyType('Sol', True),
                'Waste': EnergyType('Affald', False),
                'OnshoreWindPower': EnergyType('Landvind', True),
                'OffshoreWindPower': EnergyType('Havvind', True)}


class GenerationMixModel:

    RENEWABLE_ENERGY_STR = 'Vedvarende energi'
    NON_RENEWABLE_ENERGY_STR = 'Ikke-vedvarende energi'

    def __init__(self):
        df_mix = GenerationMixData.build().df_mix
        # Energy sources with no generation are representated by NaNs; get rid of those, and combine the results for DK1
        # and DK2. If CO2 forecasts are ever split over DK1/DK2, we can treat the two separately here as well.
        total = df_mix.fillna(0).sum()
        # df_mix contains two rows representing the current time for each region; the times will always be the same, and
        # we can just take one of them. The format is almost what we want, so we parse it as a string rather than rely
        # on datetime libraries.
        self.data_time = df_mix.HourDK.iloc[0].replace('T', ' ')[:-3]
        df_total = pd.DataFrame(total).reset_index()
        df_total.columns = ['type', 'production_mw']
        # Remove exchange data from the data frame by only focussing on the hardcoded energy types; exchanges will be
        # included in import/export calculations later.
        self.data = df_total[df_total.type.isin(energy_types)]
        # Force production values to be floating points to avoid potential issues with attempting to serialize int64s
        self.data['production_mw'] = self.data['production_mw'].astype(np.float)
        self.data['danish_name'] = self.data.type.map(lambda x: energy_types[x].danish_name)
        self.data['renewable'] = self.data.type.map(lambda x: energy_types[x].renewable)
        self.total_prod = self.data.production_mw.sum()
        # Explicitly define the share percentage string. It would be nicer if our plotting framework could do this for
        # us, so we could keep the logic closer to the view, and indeed d3.js can automatically handle percentages, but
        # not without changing decimal points.
        self.data['share'] =\
            (self.data.production_mw / self.total_prod * 100).map('{:.2f} %'.format).str.replace('.', ',')
        self.data['renewable_desc_str'] =\
            self.data.renewable.map(lambda x: self.RENEWABLE_ENERGY_STR if x else self.NON_RENEWABLE_ENERGY_STR)
        self.data['is_renewable_str'] = self.data.renewable.map(lambda x: 'Ja' if x else 'Nej')
        self.data['production_str'] = self.data.production_mw.map('{:.2f} MW'.format).str.replace('.', ',')
        # Calculate import and export across each link separately; the double sum comes as a result of summing over all
        # rows (i.e. regions, DK1/DK2) and all columns (i.e. import/export destinations) at the same time.
        exchanges = df_mix[['ExchangeContinent', 'ExchangeNordicCountries']]
        self.imp = round(exchanges[exchanges > 0].sum().sum())
        self.exp = round(-exchanges[exchanges < 0].sum().sum())

    def plot(self):
        return alt.Chart(self.data).mark_bar().encode(
            # Use a format of "d" on the x axis to avoid using "," as
            # a thousands separator (which you wouldn't do in Danish)
            x=alt.X('production_mw:Q',
                    axis=alt.Axis(title=['Strømproduktionen i Danmark [MW]', self.data_time], format='d')),
            y=alt.Y('danish_name:O',
                    sort='-x',
                    axis=alt.Axis(title='')),
            color=alt.Color('renewable_desc_str:O',
                            scale=alt.Scale(domain=[self.RENEWABLE_ENERGY_STR, self.NON_RENEWABLE_ENERGY_STR],
                                            range=['#3B5', '#333'])),
            tooltip=[alt.Tooltip('danish_name', title='Energikilde'),
                     alt.Tooltip('production_str', title='Produktion'),
                     alt.Tooltip('share', title='Andel af produktion'),
                     alt.Tooltip('is_renewable_str', title='Vedvarende energikilde')]
        ).properties(width='container', height=300).configure_axis(
            titleX=-122,
            titleY=-353,
            titleAlign='left',
            titleAngle=0,
            titleFont='Inter Regular',
            titleFontWeight='normal',
            titleFontSize=16,
            labelFont='Inter Regular',
            labelFontSize=13
        ).configure_legend(
            title=None,
            orient='bottom-right',
            labelFont='Inter Regular',
            labelFontSize=13
        )


def build_current_generation_mix():
    model = GenerationMixModel()
    # We explicitly convert our import and export values to Python integers to avoid the possibility of them ending
    # up as np.int64, which can not be serialized to JSON.
    return {'success': True,
            'plot-data': model.plot().to_dict(),
            'total-production': round(model.total_prod),
            'import': int(round(model.imp)),
            'export': int(round(model.exp))}


def current_period_emission(df_forecast, period):
    return int(round(df_forecast.iloc[:12*period].CO2Emission.mean()))


def best_period(df_forecast, period, horizon):
    lowest_mean, lowest_interval_start, lowest_interval_end = get_greenest(df_forecast, period, horizon)
    best_period_start = f'{lowest_interval_start.strftime("%H:%M")}'
    best_period_end = f'{lowest_interval_end.strftime("%H:%M")}'
    best_period_intensity = int(round(lowest_mean))
    current = current_period_emission(df_forecast, period)
    improvement = f'{int(round(100*(1 - best_period_intensity/current)))} %'
    return {'success': True,
            'current-intensity': current,
            'improvement': improvement,
            'best-period-start': best_period_start,
            'best-period-end': best_period_end,
            'best-period-intensity': best_period_intensity}


def overview_next_day(df_forecast, short_title: bool = False):
    period = 3
    horizon = 24

    mean = df_forecast[df_forecast.Minutes5UTC < df_forecast.Minutes5UTC.min() + pd.Timedelta(f'{horizon}H')]\
        .CO2Emission.mean()
    lowest_mean, lowest_interval_start, lowest_interval_end = get_greenest(df_forecast, period, horizon)
    best_hour_start = f'{lowest_interval_start.strftime("%H:%M")}'
    best_hour_end = f'{lowest_interval_end.strftime("%H:%M")}'
    if lowest_interval_start.day != df_forecast.Minutes5UTC.min().day:
        best_hour_end += ' i morgen'
    best_hour_intensity = int(round(lowest_mean))
    highest_mean, highest_interval_start, highest_interval_end = get_blackest(df_forecast, period, horizon)
    worst_hour_start = f'{highest_interval_start.strftime("%H:%M")}'
    worst_hour_end = f'{highest_interval_end.strftime("%H:%M")}'
    if highest_interval_start.day != df_forecast.Minutes5UTC.min().day:
        worst_hour_end += ' i morgen'
    worst_hour_intensity = int(round(highest_mean))

    q = EmissionIntensityModel.quintiles
    index = bisect(q, mean) - 1
    if short_title:
        colors = ['Meget grøn 💚', 'Grøn 💚', 'Grøn og sort', 'Sort 🏭', 'Kulsort 🏭']
        general_color = colors[index]
        # New forecasts arrive around 16:00, so we change our title message accordingly.
        prefix = 'i dag' if datetime.datetime.now().hour < 16 else 'det næste døgn'
        title = f'Strømmen {prefix}: {general_color}'
    else:
        colors = ['meget grøn 💚', 'grøn 💚', 'både grøn og sort', 'ret sort 🏭', 'kulsort 🏭']
        general_color = colors[index]
        forecast_length = min(horizon, math.ceil(len(df_forecast) / 12))
        title = f'De næste {forecast_length} timer er strømmen generelt {general_color}'
    message = f'🟢 Grønnest: {best_hour_start}-{best_hour_end} ({best_hour_intensity} g CO2/kWh).\n' +\
        f'⚫ Sortest: {worst_hour_start}-{worst_hour_end} ({worst_hour_intensity} g CO2/kWh).'
    return {'title': title, 'message': message}
