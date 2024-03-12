import yfinance as yf
import pandas as pd
from ta.trend import IchimokuIndicator
import time
from apscheduler.schedulers.blocking import BlockingScheduler
import colorama
import json
from datetime import date

colorama.init()

def get_stock_data(ticker, start_date, end_date):
    stock_data = yf.download(ticker, start=start_date, end=end_date, progress=False)
    return stock_data

def calculate_ichimoku(stock_data):
    ichimoku = IchimokuIndicator(stock_data['High'], stock_data['Low'])
    stock_data['Ichimoku_Lagging'] = stock_data['Close'].shift(periods=-25)
    stock_data['Ichimoku_Kijun'] = ichimoku.ichimoku_base_line()
    return stock_data

def check_ichimoku_crossover(ticker, stock_data):
    # Trouver l'index de la dernière ligne contenant une valeur dans "Ichimoku_Lagging"
    last_index = stock_data['Ichimoku_Lagging'].last_valid_index()

    # Récupérer la dernière ligne avec une valeur dans "Ichimoku_Lagging"
    last_filled_row = stock_data.loc[last_index]
    print(last_filled_row)
    last_row = stock_data.iloc[-1]

    concatenated_df = pd.DataFrame([last_filled_row, last_row])

    if last_filled_row['Ichimoku_Lagging'] > last_filled_row['Ichimoku_Kijun']:
        action = "buy"
    else:
        action = "sell"
    
    # (P: actuel / K: laging / Date : Date lagging)
    return {
                "ticker" : ticker, 
                "action" : action, 
                "date" : last_index,
                "kijun_price" : last_filled_row['Ichimoku_Kijun'],
                "lagging_price" : last_filled_row['Ichimoku_Lagging']
                }

def generate_discord_message(infoTickers):
    consoleLog = ""
    discordLog = ""
    for infoTicker in infoTickers:
        shortMessage = f"**{infoTicker['ticker']}** (P: {infoTicker['lagging_price']} / K: {infoTicker['kijun_price']} / Date : {infoTicker['date']})" 
        if infoTicker['action'] == 'buy':
            consoleLog += colorama.Fore.GREEN + shortMessage + colorama.Style.RESET_ALL + "\n"
            discordLog += ":green_circle: " + shortMessage  + "\n"
        if infoTicker['action'] == 'sell':
            consoleLog += colorama.Fore.RED + shortMessage + colorama.Style.RESET_ALL + "\n"
            discordLog +=   ":red_circle: " + shortMessage  + "\n"
    print(consoleLog)
    return discordLog

def get_info_tickers():
    ticker_list = [
                    "SGO.PA",       "ALO.PA",       "GTT.PA",
                    "TEP.PA",       "ALATA.PA",     "ATEME.PA", 
                    "ATO.PA",       "FDJ.PA",       "ALCOG.PA", 
                    "BTC-USD", 
                    "DOGE-USD",     "XLM-USD",      "SUSHI-USD", 
                    "ADA-USD",      "APT21794-USD", 
                    "TWT-USD",      "FTM-USD",
                    "NEXO-USD",     "ETH-USD",
                    "XRP-USD",      "MATIC-USD", 
                    "CELR-USD",     "BCH-USD",      "AVAX-USD",
                    "LTC-USD",      "BAT-USD",
                    "ZIL-USD",      "LUNC-USD",
                    ]
    start_date = (pd.to_datetime('today') - pd.DateOffset(days=90)).strftime('%Y-%m-%d')
    end_date = pd.to_datetime('today').strftime('%Y-%m-%d')

    infoTickers = []
    for ticker in ticker_list:
        stock_data = get_stock_data(ticker, start_date, end_date)
        stock_data = calculate_ichimoku(stock_data)


        infoTickers.append(check_ichimoku_crossover(ticker, stock_data))

    return infoTickers


async def coinMonitoring(message):
    infoTickers = get_info_tickers()
    texte = generate_discord_message(infoTickers) + "\n"
    messages = texte.split('\n')  # Divise le texte en lignes

    taille_paquet = 10
    
    for i in range(0, len(messages), taille_paquet):
        paquet = messages[i:i+taille_paquet]
        await message.channel.send("\n".join(paquet))






def load_previous_info(filename):
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_info(filename, data):
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)

def process_info(previous_info, new_info):
    changed_info = []

    for info in new_info:
        ticker = info["ticker"]
        action = info["action"]

        if ticker in previous_info:
            if previous_info[ticker] != action:
                changed_info.append({"ticker": ticker, "action": action})
        else:
            changed_info.append({"ticker": ticker, "action": action})

    return changed_info

async def coinMonitoringDiff(message):

    filename = "./tmp/coinMonitoring.json"
    new_info = get_info_tickers()

    previous_info = load_previous_info(filename)
    changed_info = process_info(previous_info, new_info)

    if changed_info:
        print("Les changements suivants ont été détectés :")
        for change in changed_info:
            print(f"Ticker: {change['ticker']}, Action: {change['action']}")
        
        await message.channel.send(generate_discord_message(changed_info))

        save_info(filename, {info["ticker"]: info["action"] for info in new_info})
    else:
        print("Aucun changement détecté.")
        await message.channel.send("RAS on " + str(len(new_info)) + " coins.")