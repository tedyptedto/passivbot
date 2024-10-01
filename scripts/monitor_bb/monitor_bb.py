import ccxt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os

#python3 -m venv venv
# venv/bin/pip install ccxt matplotlib numpy pandas
# venv/bin/python3 monitor_bb.py

# Paramètres des bandes de Bollinger
lengthBBline = 20
multBBline = 2.0
lengthLineExtensionBBline = 20  # Prolongement des lignes (bougies)

# Initialisation de l'exchange (Binance ici)
exchange = ccxt.binance()


# Dictionnaire pour stocker les compteurs de croisements pour chaque symbole
cross_count = {}
cross_timeframes = {}

# Fonction pour récupérer les données OHLCV
def fetch_data(symbol, timeframe):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

# Fonction pour calculer les bandes de Bollinger
def bollinger_bands(data, length, mult):
    sma = data['close'].rolling(window=length).mean()
    std = data['close'].rolling(window=length).std()
    upper_band = sma + mult * std
    lower_band = sma - mult * std
    return upper_band, sma, lower_band

# Fonction pour prolonger les bandes de Bollinger
def extend_lines(data, upper_band, lower_band, length_extension):
    if len(data) < 4:
        return None, None  # Pas assez de barres pour calculer les pentes
    
    # Calcul de la pente pour la bande supérieure et son prolongement
    slope_upperBBline = (upper_band.iloc[-1] - upper_band.iloc[-4]) / 3
    future_index = np.arange(len(data), len(data) + length_extension)
    future_upperBBline = upper_band.iloc[-1] + slope_upperBBline * (future_index - len(data))

    # Calcul de la pente pour la bande inférieure et son prolongement
    slope_lowerBBline = (lower_band.iloc[-1] - lower_band.iloc[-4]) / 3
    future_lowerBBline = lower_band.iloc[-1] + slope_lowerBBline * (future_index - len(data))

    return future_upperBBline, future_lowerBBline

# Fonction pour tracer et enregistrer les graphiques avec prolongement des bandes
def plot_bollinger_bands(symbol, timeframe, data, upper_band, sma, lower_band, future_upper, future_lower):
    safe_symbol = symbol.replace('/', '_')
    
    plt.figure(figsize=(10, 6))
    plt.plot(data.index, data['close'], label='Close Price', color='black')
    plt.plot(data.index, upper_band, label='Upper Band', color='blue')
    plt.plot(data.index, sma, label='SMA', color='green')
    plt.plot(data.index, lower_band, label='Lower Band', color='orange')
    
    # Tracer les lignes prolongées
    future_dates = pd.date_range(data.index[-1], periods=lengthLineExtensionBBline+1, freq='D')[1:]
    plt.plot(future_dates, future_upper, '--', color='blue', label='Upper Band Extension')
    plt.plot(future_dates, future_lower, '--', color='orange', label='Lower Band Extension')

    plt.fill_between(data.index, upper_band, lower_band, color='lightgray', alpha=0.5)
    plt.title(f'{symbol} - {timeframe}')
    plt.legend()
    plt.grid()
    
    if not os.path.exists('charts'):
        os.makedirs('charts')
    plt.savefig(f'charts/{safe_symbol}_{timeframe}.png')
    plt.close()

# Fonction pour déterminer la tendance des lignes prolongées avec des couleurs
def determine_trend(symbol, timeframe, future_upper, future_lower):
    if check_cross(future_upper, future_lower):
        cross_count[symbol] = cross_count.get(symbol, 0) + 1  # Incrémente le compteur pour le symbole
        if symbol not in cross_timeframes:
            cross_timeframes[symbol] = []
        cross_timeframes[symbol].append(timeframe)  # Enregistre l'UT du croisement
        return "\033[32mCroisement\033[0m"  # Vert foncé
    elif future_upper[-1] > future_upper[0] and future_lower[-1] > future_lower[0]:
        return "\033[90mCanal ascendant\033[0m"  # Gris clair
    elif future_upper[-1] < future_upper[0] and future_lower[-1] < future_lower[0]:
        return "\033[90mCanal descendant\033[0m"  # Gris clair
    elif future_upper[-1] > future_upper[0] and future_lower[-1] < future_lower[0]:
        return "\033[90mIndécis ouvert\033[0m"  # Gris clair
    elif future_upper[-1] < future_upper[0] and future_lower[-1] > future_lower[0]:
        return "\033[90mIndécis fermé\033[0m"  # Gris clair
    return "\033[90mAucune tendance marquée\033[0m"  # Gris clair


# Fonction pour vérifier le croisement des lignes
def check_cross(future_upper, future_lower):
    # Croisement simple basé sur la dernière valeur des lignes prolongées
    return future_lower[-1] > future_upper[-1]  # Retourne True si la bande inférieure croise la supérieure

# Fonction principale pour surveiller les cryptos
def monitor_cryptos(symbols, timeframes):
    for symbol in symbols:
        for timeframe in timeframes:
            # Récupération des données
            data = fetch_data(symbol, timeframe)
            
            # Calcul des bandes de Bollinger
            upper_band, sma, lower_band = bollinger_bands(data, lengthBBline, multBBline)
            
            # Prolongement des lignes
            future_upper, future_lower = extend_lines(data, upper_band, lower_band, lengthLineExtensionBBline)
            
            if future_upper is not None and future_lower is not None:
                # Déterminer la tendance des lignes prolongées
                trend = determine_trend(symbol, timeframe, future_upper, future_lower)
                print(f'{symbol} - {timeframe}: {trend}')
            
            # Enregistrement des graphiques avec les lignes prolongées
            plot_bollinger_bands(symbol, timeframe, data, upper_band, sma, lower_band, future_upper, future_lower)

# À la fin du script, afficher les symboles avec un nombre de croisements supérieur au seuil
def display_symbols_with_crossings(threshold=2):
    print("\nSymbole(s) avec plusieurs croisements :")
    for symbol, count in cross_count.items():
        if count >= threshold:
            timeframes_str = ", ".join(cross_timeframes[symbol])
            print(f"\033[32m{symbol}\033[0m a eu {count} croisements sur les UT : \033[32m{timeframes_str}\033[0m.")
            


# Liste des cryptos à surveiller
symbols = [
            'BTC/USDT',
            'LUNA/USDT',
            'XRP/USDT',
            'DOGE/USDT',
            'CELR/USDT',
            'SOL/USDT',
            'ADA/USDT',
            'GRT/USDT',
            'AVAX/USDT',
            'XLM/USDT',
            'NEXO/USDT',
            'ETH/USDT',
            'LTC/USDT',
            'BAT/USDT',
            'ZIL/USDT',
            'BCH/USDT',
            'LUNC/USDT',
            'DOT/USDT',
            'FLOKI/USDT',
            'PEPE/USDT',
            'TRX/USDT',
            'SUSHI/USDT',
            'POLYX/USDT',
            'APT/USDT',
            'TWT/USDT',
            'FTM/USDT',
]



# Liste des unités de temps à surveiller
timeframes = ['1d', '4h', '1h', '5m']

# Lancer la surveillance
monitor_cryptos(symbols, timeframes)



# Exemple d'utilisation
# À la fin de toutes les vérifications
display_symbols_with_crossings(threshold=2)            