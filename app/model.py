import altair as alt
import pandas as pd
import requests


class EmissionData:

    def __init__(self):
        base_url = 'https://api.energidataservice.dk/datastore_search'
        fields = 'Minutes5UTC,Minutes5DK,CO2Emission'
        sort = 'Minutes5UTC desc'
        limit = 500
        filters = '{"PriceArea": "DK2"}'
        data = requests.get(
            f'{base_url}?resource_id=co2emis&fields={fields}&sort={sort}&limit={limit}&filters={filters}').json()
        data_forecast = requests.get(
            f'{base_url}?resource_id=co2emisprog&fields={fields}&sort={sort}&limit={limit}&filters={filters}').json()
        df_actual = pd.DataFrame(data['result']['records'])[::-1]
        df_actual['Minutes5DK'] = pd.to_datetime(df_actual.Minutes5DK)
        df_actual['Minutes5UTC'] = pd.to_datetime(df_actual.Minutes5UTC)
        df_actual['Type'] = 'Målt'
        df_forecast = pd.DataFrame(data_forecast['result']['records'])[::-1]
        df_forecast['Minutes5DK'] = pd.to_datetime(df_forecast.Minutes5DK)
        df_forecast['Minutes5UTC'] = pd.to_datetime(df_forecast.Minutes5UTC)
        df_forecast['Type'] = 'Prognose'
        df_forecast = df_forecast[df_forecast.Minutes5DK >= df_actual.Minutes5DK.max()]
        # Replace forecasted value for current time with actual time, mainly to make it simpler to produce a connected
        # graph below.
        df_forecast.iloc[0] = [df_actual.Minutes5UTC.max(),
                               df_actual.Minutes5DK.max(),
                               df_actual.iloc[-1]['CO2Emission'],
                               'Prognose']
        # Calculate best hour to use power
        #df_next_day = df_forecast[df_forecast.Minutes5UTC < df_actual.Minutes5UTC.max() + pd.Timedelta('1D')]
        #rolling = df_next_day.set_index('Minutes5DK').CO2Emission.rolling('1H', min_periods=12).mean()[11:]
        #lowest = rolling.idxmin()
        #self.lowest_mean = rolling.loc[lowest]
        #self.lowest_interval_start = lowest - pd.Timedelta('55m')
        #self.lowest_interval_end = lowest + pd.Timedelta('5m')
        self.df_forecast = df_forecast
        self.df = pd.concat([df_actual, df_forecast])
        self.df['Minutes5DK'] = self.df.Minutes5DK.dt.tz_localize('Europe/Copenhagen')
        self.now_utc_int = df_actual.Minutes5UTC.astype(int).max() / 1000000
        self.min_time = self.df.Minutes5DK.min()
        self.max_time = self.df.Minutes5DK.max()
        self.now = df_actual.Minutes5DK.max()
        self.current_emission = int(df_forecast.iloc[0].CO2Emission)

    quintiles = [0, 55, 95, 140, 209, 1000]  # Determined through analyses based on data since 2017

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
    df_next_day = df_forecast[df_forecast.Minutes5UTC < df_forecast.Minutes5UTC.min() + pd.Timedelta(f'{horizon}H')]
    min_periods = period * 12
    rolling = df_next_day.set_index('Minutes5DK').CO2Emission.rolling(f'{period}H', min_periods=min_periods).mean()[min_periods-1:]
    lowest = rolling.idxmin()
    lowest_mean = rolling.loc[lowest]
    lowest_interval_start = lowest - pd.Timedelta(f'{period}H') + pd.Timedelta('5m')
    lowest_interval_end = lowest + pd.Timedelta('5m')
    return lowest_mean, lowest_interval_start, lowest_interval_end

def build_model():
    data = EmissionData()
    full_chart = data.plot()
    latest_data = data.now.strftime('%Y-%m-%d %H:%M')
    current_emission = data.current_emission
    quintiles = data.quintiles
    if current_emission < quintiles[1]:
        index = 0
    elif current_emission < quintiles[2]:
        index = 1
    elif current_emission < quintiles[3]:
        index = 2
    elif current_emission < quintiles[4]:
        index = 3
    else:
        index = 4
    bg_colors = [f'rgba(0, {i}, 0, 0.9)' for i in range(128, -32, -32)]
    border_colors = [f'rgba(0, {i+32}, 0, 0.9)' for i in range(128, 0, -32)] + ['#333']
    fg_colors = ['#FFF', '#FFF', '#EEE', '#EEE', '#EEE']
    levels = ['Meget grøn', 'Grøn', 'Hverken grøn eller sort', 'Sort', 'Meget sort']
    emission_intensity = {'intensity-level-bgcolor': bg_colors[index],
                          'intensity-level-fgcolor': fg_colors[index],
                          'intensity-level-border-color': border_colors[index],
                          'intensity-level': levels[index],
                          'current-intensity': current_emission,
                          'latest-data': latest_data,
                          'plot-data': full_chart.to_dict()}
    return emission_intensity, data.df_forecast

def best_hour(df_forecast, period, horizon):
    lowest_mean, lowest_interval_start, lowest_interval_end = get_greenest(df_forecast, period, horizon)
    best_hour_start = f'{lowest_interval_start.strftime("%H:%M")}'
    best_hour_end = f'{lowest_interval_end.strftime("%H:%M")}'
    best_hour_intensity = int(round(lowest_mean))
    return {'best-hour-start': best_hour_start,
            'best-hour-end': best_hour_end,
            'best-hour-intensity': best_hour_intensity}
