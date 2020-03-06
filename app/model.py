"""Contains the model (in the MVC sense) of the data presented in the web app.

In particular, this provides all post-processing of Energinet's data.
"""
from bisect import bisect
import math

import altair as alt
import pandas as pd
import requests

from .data import EmissionData


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

        # Add a dummy selection on the top plot, since otherwise tooltips will never show up, due to a bug in Vega-Lite:
        # https://github.com/vega/vega-lite/issues/6003
        top = top.add_selection(alt.selection_single())

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
            titleFontSize=13
        ).configure_legend(
            title=None,
            orient='top-right',
            labelFont='Inter Regular',
            labelFontSize=12
        )


def get_greenest(df_forecast, period: int, horizon: int):
    return get_extreme(df_forecast, period, horizon, False)


def get_blackest(df_forecast, period: int, horizon: int):
    return get_extreme(df_forecast, period, horizon, True)


def get_extreme(df_forecast, period: int, horizon: int, idxmax):
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
    emission_intensity = {'intensity-level-bgcolor': bg_colors[index],
                          'intensity-level-fgcolor': fg_colors[index],
                          'intensity-level-border-color': border_colors[index],
                          'intensity-level': levels[index],
                          'forecast-length-hours': model.forecast_length_hours,
                          'latest-data': latest_data,
                          'plot-data': full_chart.to_dict()}
    return emission_intensity, model.data.df_forecast


def current_period_emission(df_forecast, period):
    return int(round(df_forecast.iloc[:12*period].CO2Emission.mean()))


def best_period(df_forecast, period, horizon):
    lowest_mean, lowest_interval_start, lowest_interval_end = get_greenest(df_forecast, period, horizon)
    best_period_start = f'{lowest_interval_start.strftime("%H:%M")}'
    best_period_end = f'{lowest_interval_end.strftime("%H:%M")}'
    best_period_intensity = int(round(lowest_mean))
    current = current_period_emission(df_forecast, period)
    improvement = f'{int(round(100*(1 - best_period_intensity/current)))} %'
    return {'current-intensity': current,
            'improvement': improvement,
            'best-hour-start': best_period_start,
            'best-hour-end': best_period_end,
            'best-hour-intensity': best_period_intensity}


def overview_next_day(df_forecast):
    mean = df_forecast[df_forecast.Minutes5UTC < df_forecast.Minutes5UTC.min() + pd.Timedelta('1D')].CO2Emission.mean()
    lowest_mean, lowest_interval_start, lowest_interval_end = get_greenest(df_forecast, 1, 24)
    best_hour_start = f'{lowest_interval_start.strftime("%H:%M")}'
    best_hour_end = f'{lowest_interval_end.strftime("%H:%M")}'
    best_hour_intensity = int(round(lowest_mean))
    highest_mean, highest_interval_start, highest_interval_end = get_blackest(df_forecast, 1, 24)
    worst_hour_start = f'{highest_interval_start.strftime("%H:%M")}'
    worst_hour_end = f'{highest_interval_end.strftime("%H:%M")}'
    worst_hour_intensity = int(round(highest_mean))

    q = EmissionIntensityModel.quintiles
    colors = ['meget grøn', 'grøn', 'både grøn og sort', 'ret sort', 'kulsort']
    index = bisect(q, mean) - 1
    general_color = colors[index]
    data = f'Strømmen er de næste 24 timer generelt {general_color} ({int(round(mean))} g CO2/kWh).\n' +\
        f'Grønnest: {best_hour_start}-{best_hour_end} ({best_hour_intensity} g CO2/kWh).\n' +\
        f'Sortest: {worst_hour_start}-{worst_hour_end} ({worst_hour_intensity} g CO2/kWh).'
    return data
