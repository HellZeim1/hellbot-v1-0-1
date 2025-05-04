import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
import pandas as pd
import requests
import pandas_ta as ta  # talib yerine pandas_ta kullanıyoruz
import dash_bootstrap_components as dbc
from datetime import datetime

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
server = app.server

html.Img(src='/assets/hellbot_logo.png', style={'width': '100px'})

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
    if response.status_code == 200:
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
    else:
        print(f"API yanıtı başarısız, durum kodu: {response.status_code}")
        return pd.DataFrame()  # Boş bir DataFrame döndürülür

# Bitcoin Dominasyonu verisini çekme fonksiyonu
def get_bitcoin_dominance():
    url = 'https://api.coingecko.com/api/v3/global'
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if 'data' in data and 'market_cap_percentage' in data['data']:
            dominance = data['data']['market_cap_percentage'].get('btc', None)
            return dominance
        else:
            print("API yanıtı beklenen formatta değil:", data)
            return None
    else:
        print(f"API isteği başarısız oldu, durum kodu: {response.status_code}")
        return None

# Anlık fiyatı çeken fonksiyon
def get_live_price():
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return float(data['price'])
    else:
        print(f"Anlık fiyat verisi alınamadı. Durum kodu: {response.status_code}")
        return None

# Grafik oluşturma fonksiyonu
def generate_chart(df, show_ema9, show_ema21, show_macd, show_rsi, show_sma):
    # pandas_ta kullanarak göstergeler
    sma = ta.sma(df['close'], timeperiod=14)
    rsi = ta.rsi(df['close'], timeperiod=14)
    macd, macd_signal, _ = ta.macd(df['close'], fast=12, slow=26, signal=9)
    ema_9 = ta.ema(df['close'], timeperiod=9)
    ema_21 = ta.ema(df['close'], timeperiod=21)

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
def generate_ai_analysis(df, dominance):
    if df.empty:
        return "Veri alınamadı veya API yanıtı boş."
    
    price = df['close'].iloc[-1] if not df.empty else 0
    low_24h = df['low'].min() if not df.empty else 0
    high_24h = df['high'].max() if not df.empty else 0
    support_level = low_24h
    resistance_level = high_24h

    dominance_comment = risk_management(dominance) if dominance else "Dominasyon verisi alınamadı."

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
    """
    return analysis

# Risk Yönetimi Fonksiyonu
def risk_management(dominance):
    if dominance > 60:
        return "Bitcoin Dominasyonu yüksek. Altcoinlerde risk olabilir, pozisyonu dikkatlice kontrol edin."
    else:
        return "Bitcoin Dominasyonu düşük, altcoinler daha rahat hareket edebilir."

# Dash Layout
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

    # Grafik ve göstergeler
    dcc.Graph(id='price-graph', config={'scrollZoom': True}),
    html.Div(id='technical-comment', className='text-center mt-3', style={'color': '#00f0ff', 'fontWeight': 'bold'}),

    # Yapay Zeka Analizi Paneli
    html.Div([
        html.H3("Yapay Zeka Analizi"),
        html.Pre(id='ai-analysis', style={
            'color': '#ffffff',
            'backgroundColor': '#1e1e1e',
            'padding': '10px',
            'borderRadius': '5px',
            'border': '1px solid #444',
            'whiteSpace': 'pre-wrap',
            'fontSize': '12px',
        }),
    ], className='mt-4'),
])

@app.callback(
    [Output('price-graph', 'figure'),
     Output('ai-analysis', 'children'),
     Output('live-price', 'children')],
    [Input('interval-dropdown', 'value')]
)
def update_dashboard(interval):
    # Binance verisini al
    df = get_binance_ohlcv(symbol, interval)
    
    # Bitcoin dominasyonunu al
    dominance = get_bitcoin_dominance()
    
    # Anlık fiyatı al
    live_price = get_live_price()
    
    # Teknik analiz grafik ve yorumları
    show_ema9 = True
    show_ema21 = True
    show_macd = True
    show_rsi = True
    show_sma = True
    chart = generate_chart(df, show_ema9, show_ema21, show_macd, show_rsi, show_sma)
    
    # Yapay zeka analizi oluştur
    ai_analysis = generate_ai_analysis(df, dominance)
    
    return chart, ai_analysis, f"Anlık Fiyat: {live_price:.2f} USDT" if live_price else "Fiyat alınamadı."

if __name__ == '__main__':
    app.run(debug=True)
