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
        df_next_day = df_forecast[df_forecast.Minutes5UTC < df_actual.Minutes5UTC.max() + pd.Timedelta('1D')]
        rolling = df_next_day.set_index('Minutes5DK').CO2Emission.rolling('1H', min_periods=12).mean()[11:]
        lowest = rolling.idxmin()
        self.lowest_mean = rolling.loc[lowest]
        self.lowest_interval_start = lowest - pd.Timedelta('55m')
        self.lowest_interval_end = lowest + pd.Timedelta('5m')
        self.df = pd.concat([df_actual, df_forecast])
        self.now_utc_int = df_actual.Minutes5UTC.astype(int).max() / 1000000
        self.min_time = self.df.Minutes5DK.min()
        self.max_time = self.df.Minutes5DK.max()
        self.now = df_actual.Minutes5DK.max()
        self.current_emission = int(df_forecast.iloc[0].CO2Emission)

    quintiles = [0, 55, 95, 140, 209, 1000]  # Determined through analyses based on data since 2017

    def plot(self):
        df_combined = self.df
        m = self.now_utc_int

        start = m - 3600 * 1000 * 6
        end = m + 3600 * 1000 * 6
        height = 250
        today = pd.DataFrame({'x': [self.now, self.now], 'y': [0, self.quintiles[-1]]})
        rects = [pd.DataFrame(
            {'x': [self.min_time], 'y': [self.quintiles[i]], 'x2': [self.max_time], 'y2': [self.quintiles[i+1]]})
            for i in range(5)]

        interval = alt.selection_interval(encodings=['x'],
                                          init={'x': [int(start), int(end)]})

        base = alt.Chart(df_combined).mark_line().encode(
            alt.X('yearmonthdatehoursminutes(Minutes5DK):T', title=''),
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
            .encode(x=alt.X('yearmonthdatehoursminutes(Minutes5DK):T',
                            axis=alt.Axis(format='%H:%S'),
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
    colors = ['rgba(0, 255, 0, 0.4)', 'rgba(128, 255, 128, 0.4)', 'rgba(255, 255, 0, 0.4)',
              'rgba(255, 128, 128, 0.4)', 'rgba(255, 0, 0, 0.4)']
    levels = ['Meget lav', 'Lav', 'Moderat', 'Høj', 'Meget høj']
    best_hour_start = f'{data.lowest_interval_start.strftime("%H:%M")}'
    best_hour_end = f'{data.lowest_interval_end.strftime("%H:%M")}'
    best_hour_intensity = int(round(data.lowest_mean))
    emission_intensity = {'intensity-level-color': colors[index],
                          'intensity-level': levels[index],
                          'current-intensity': current_emission,
                          'best-hour-start': best_hour_start,
                          'best-hour-end': best_hour_end,
                          'best-hour-intensity': best_hour_intensity,
                          'latest-data': latest_data,
                          'plot-data': full_chart.to_dict()}
    return emission_intensity
