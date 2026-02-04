import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd
import os

# Initialize the Dash app
app = dash.Dash(__name__)

# Define the app layout
app.layout = html.Div([
    html.H1("Weather Data Dashboard", style={'textAlign': 'center'}),

    dcc.Tabs([
        dcc.Tab(label='Temperature Trends', children=[
            dcc.Graph(id='temperature-graph'),
            dcc.Interval(
                id='interval-component',
                interval=60*1000,  # Update every minute
                n_intervals=0
            )
        ]),

        dcc.Tab(label='Model Performance', children=[
            dcc.Graph(id='model-graph'),
            dcc.Interval(
                id='model-interval',
                interval=60*1000,  # Update every minute
                n_intervals=0
            )
        ])
    ])
])

@app.callback(
    Output('temperature-graph', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_temperature_graph(n):
    try:
        df = pd.read_csv('/app/clean_data/fulldata.csv')
        fig = px.line(df, x='date', y='temperature', color='city',
                     title='Temperature Trends by City',
                     labels={'temperature': 'Temperature (°C)', 'date': 'Date'})
        return fig
    except FileNotFoundError:
        return px.scatter(title="No weather data available")

@app.callback(
    Output('model-graph', 'figure'),
    [Input('model-interval', 'n_intervals')]
)
def update_model_graph(n):
    try:
        # Load model performance data - you'll need to create this in your pipeline
        df = pd.read_csv('/app/clean_data/model_performance.csv')
        fig = px.bar(df, x='model', y='score', title='Model Performance Comparison',
                    labels={'model': 'Model', 'score': 'Score'})
        return fig
    except FileNotFoundError:
        return px.bar(title="No model performance data available")

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=8050, debug=True)
