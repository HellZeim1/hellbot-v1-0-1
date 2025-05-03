import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
import pandas as pd
import requests
import talib
import dash_bootstrap_components as dbc
from datetime import datetime

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
server = app.server

symbol = "SOLUSDT"
intervals = {
    "15 Dakika": "15m",
    "1 Saat": "1h",
    "4 Saat": "4h",
    "1 Gün": "1d",
    "7 Gün": "1w",
    "30 Gün": "1M"
}

# Binance'ten veri çekme fonksiyonu
def get_binance_ohlcv(symbol, interval, limit=200):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data, columns=[ 
        "timestamp", "open", "high", "low", "close", "volume", 
        "close_time", "quote_asset_volume", "number_of_trades", 
        "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"])

    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    return df

# Bitcoin Dominasyonu verisini çekme fonksiyonu
def get_bitcoin_dominance():
    url = "https://api.coingecko.com/api/v3/global"
    response = requests.get(url)
    data = response.json()
    dominance = data['data']['market_cap_percentage']['btc']
    return dominance

# Piyasa haberlerini çekme fonksiyonu (CoinGecko)
def get_market_news():
    url = "https://api.coingecko.com/api/v3/news"
    response = requests.get(url)
    news = response.json()
    headlines = [item['title'] for item in news[:5]]  # İlk 5 haberi al
    return headlines

# Grafik oluşturma fonksiyonu
def generate_chart(df, show_ema9, show_ema21, show_macd, show_rsi, show_sma):
    sma = talib.SMA(df['close'], timeperiod=14)
    rsi = talib.RSI(df['close'], timeperiod=14)
    macd, macd_signal, _ = talib.MACD(df['close'], fastperiod=12, slowperiod=26, signalperiod=9)
    ema_9 = talib.EMA(df['close'], timeperiod=9)
    ema_21 = talib.EMA(df['close'], timeperiod=21)

    candlestick = go.Candlestick(
        x=df['timestamp'], open=df['open'], high=df['high'],
        low=df['low'], close=df['close'], name="Fiyat"
    )

    indicators = []

    if show_sma:
        indicators.append(go.Scatter(x=df['timestamp'], y=sma, mode='lines', name='SMA (14)', line=dict(width=1)))
    if show_ema9:
        indicators.append(go.Scatter(x=df['timestamp'], y=ema_9, mode='lines', name='EMA (9)', line=dict(width=1, dash='dot')))
    if show_ema21:
        indicators.append(go.Scatter(x=df['timestamp'], y=ema_21, mode='lines', name='EMA (21)', line=dict(width=1, dash='dot')))
    if show_macd:
        indicators.append(go.Scatter(x=df['timestamp'], y=macd, mode='lines', name='MACD', line=dict(width=1, color='cyan')))
        indicators.append(go.Scatter(x=df['timestamp'], y=macd_signal, mode='lines', name='MACD Sinyal', line=dict(width=1, color='magenta')))
    if show_rsi:
        indicators.append(go.Scatter(x=df['timestamp'], y=rsi, mode='lines', name='RSI', line=dict(width=1, color='green')))

    fig = go.Figure(data=[candlestick, *indicators])

    fig.update_layout(
        template='plotly_dark', xaxis_title='Tarih', yaxis_title='Fiyat (USDT)', xaxis_rangeslider_visible=False
    )

    return fig

# Yapay zeka analiz fonksiyonu
def generate_ai_analysis(df, dominance, news):
    price = df['close'].iloc[-1]
    low_24h = df['low'].min()
    high_24h = df['high'].max()
    support_level = low_24h
    resistance_level = high_24h

    dominance_comment = risk_management(dominance)

    news_comment = "Piyasa Haberleri:\n" + "\n".join(news)

    analysis = f"""
    Grafik, {len(df)} veri noktasıyla SOL/USDT paritesini gösteriyor.
    Şu anda fiyat {price:.2f} USDT, son 24 saatteki en düşük seviye ise {low_24h:.2f} USDT.
    Teknik olarak kısa vadeli analiz:

    1. Destek ve Direnç Seviyeleri:
    Destek: {support_level:.2f}
    Direnç: {resistance_level:.2f}

    2. Trend:
    Kısa vadeli düşüşten sonra {support_level:.2f}'dan yukarı tepki gelmiş.

    3. Mum Formasyonları:
    Dipten gelen birkaç yeşil mum var ama henüz net bir yükseliş trendi başlamış değil.

    4. Yön Tahmini:
    Fiyat {resistance_level:.2f} seviyesini aşamazsa ve tekrar satış gelirse, short için fırsat doğabilir.
    {support_level:.2f} seviyesi kırılırsa düşüş hızlanabilir.
    Ancak {resistance_level:.2f} üzerine çıkarsa kısa vadeli long düşünülebilir.

    Strateji Önerisi:
    Şu an nötr bölge. Net yön için ya:
    {resistance_level:.2f} üzerine çıkması (long)
    {support_level:.2f} altına inmesi (short) beklenmeli.
    
    {dominance_comment}
    
    {news_comment}
    """
    return analysis

# Risk Yönetimi Fonksiyonu
def risk_management(dominance):
    if dominance > 60:
        return "Bitcoin Dominasyonu yüksek. Altcoinlerde risk olabilir, pozisyonu dikkatlice kontrol edin."
    else:
        return "Bitcoin Dominasyonu düşük, altcoinler daha rahat hareket edebilir."

app.layout = dbc.Container([
    html.H1("SOL/USDT Teknik Analiz Paneli", className="text-center my-4 text-primary"),
    dbc.Row([
        dbc.Col([ 
            html.Label("Zaman Aralığı Seçin:"),
            dcc.Dropdown(
                id='interval-dropdown',
                options=[{'label': k, 'value': v} for k, v in intervals.items()],
                value='1h', clearable=False
            )
        ], width=3),
        dbc.Col(html.Div(id='live-price', className='h4 text-end', style={'color': '#00ff88'}), width=9)
    ], className='mb-4'),

    # Grafik ve göstergelerin kontrolü için checkbox'lar
    html.Div([
        dcc.Checklist(
            id='indicator-checklist',
            options=[
                {'label': 'SMA (14)', 'value': 'SMA'},
                {'label': 'EMA (9)', 'value': 'EMA9'},
                {'label': 'EMA (21)', 'value': 'EMA21'},
                {'label': 'MACD', 'value': 'MACD'},
                {'label': 'RSI', 'value': 'RSI'}
            ],
            value=['SMA', 'EMA9', 'EMA21', 'MACD', 'RSI'],  # Varsayılan olarak hepsi açık
            inline=True,
            style={'margin': '10px'}
        )
    ], className='mb-4'),

    dcc.Graph(id='price-graph', config={'scrollZoom': True}),
    html.Div(id='technical-comment', className='text-center mt-3', style={'color': '#00f0ff', 'fontWeight': 'bold'}),
    html.Pre(id='ai-analysis', style={
        'color': '#ffffff',
        'backgroundColor': '#1e1e1e',
        'padding': '10px',
        'borderRadius': '5px',
        'border': '1px solid #444',
        'whiteSpace': 'pre-wrap',
        'fontSize': '12px',
    })
])

@app.callback(
    [Output('price-graph', 'figure'),
     Output('technical-comment', 'children'),
     Output('ai-analysis', 'children')],
    [Input('interval-dropdown', 'value'),
     Input('indicator-checklist', 'value')]
)
def update_graph(interval, selected_indicators):
    df = get_binance_ohlcv(symbol, interval)
    dominance = get_bitcoin_dominance()
    news = get_market_news()

    show_ema9 = 'EMA9' in selected_indicators
    show_ema21 = 'EMA21' in selected_indicators
    show_macd = 'MACD' in selected_indicators
    show_rsi = 'RSI' in selected_indicators
    show_sma = 'SMA' in selected_indicators

    fig = generate_chart(df, show_ema9, show_ema21, show_macd, show_rsi, show_sma)

    ai_analysis = generate_ai_analysis(df, dominance, news)

    return fig, "", ai_analysis

if __name__ == '__main__':
    app.run(debug=True)
