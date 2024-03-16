import yfinance as yf
import pandas as pd
from ta.trend import IchimokuIndicator
import time
from apscheduler.schedulers.blocking import BlockingScheduler
import colorama
import json
from datetime import date

colorama.init()

def get_daily_stock_data(ticker, start_date, end_date):
    stock_data = yf.download(ticker, start=start_date, end=end_date, progress=False)
    return stock_data

def get_weekly_stock_data(ticker, start_date, end_date):
    stock_data = yf.download(ticker, start=start_date, end=end_date, interval='1wk', progress=False)
    return stock_data

def calculate_ichimoku(stock_data):
    ichimoku = IchimokuIndicator(stock_data['High'], stock_data['Low'])
    stock_data['Ichimoku_Lagging'] = stock_data['Close'].shift(periods=-25)
    stock_data['Ichimoku_Kijun'] = ichimoku.ichimoku_base_line()
    return stock_data

def getLastFilledRow(stock_data, period, ticker):
    # Trouver l'index de la dernière ligne contenant une valeur dans "Ichimoku_Lagging"
    last_index = stock_data['Ichimoku_Lagging'].last_valid_index()

    # Récupérer la dernière ligne avec une valeur dans "Ichimoku_Lagging"
    toreturn = {"last_index" : last_index, "last_filled_row": stock_data.loc[last_index]}

    print(f"{period} => last_filled_row - {ticker} :")
    print(toreturn['last_filled_row'])

    return toreturn

def check_ichimoku_crossover(ticker, period, stock_data):

    # Récupérer la dernière ligne avec une valeur dans "Ichimoku_Lagging"
    last = getLastFilledRow(stock_data, period, ticker)
    last_filled_row = last['last_filled_row']

    if last_filled_row['Ichimoku_Lagging'] > last_filled_row['Ichimoku_Kijun']:
        action = "buy"
    else:
        action = "sell"
    
    # (P: actuel / K: laging / Date : Date lagging)
    return {
                "ticker" : ticker, 
                "action" : action, 
                "date" : str(last['last_index']).split(" ")[0],
                "kijun_price" : last_filled_row['Ichimoku_Kijun'],
                "lagging_price" : last_filled_row['Ichimoku_Lagging']
                }

def format_decimal(nombre, nb_decimales=2):
    if nombre > 10:
       return "{:.{}f}".format(nombre, 0)

    # Si le nombre est supérieur à zéro, affiche le chiffre à 4 décimales
    if nombre > 1:
       return "{:.{}f}".format(nombre, nb_decimales)
    # Sinon, si le nombre est inférieur à zéro, affiche 4 chiffres après le premier 0
    else:
        str_nombre = str(nombre)
        index_decimal = str_nombre.find('.')  # Trouver l'index de la décimale
        if index_decimal != -1:  # Si le nombre est décimal
            chiffres_apres_decimal = str_nombre[index_decimal + 1:]  # Extraire les chiffres après la décimale
            for i, chiffre in enumerate(chiffres_apres_decimal):
                if chiffre != '0':
                    index_dernier_zero = i + 1  # Trouver l'index du dernier 0 après la décimale
                    break
            return "{:.{}f}".format(nombre, index_dernier_zero + nb_decimales -1 )
        else:  # Si le nombre est entier
            return str(nombre)

def generate_discord_message(infoTickers):
    consoleLog = ""
    discordLog = ""
    for infoTicker in infoTickers:
        # shortMessage = f"**{infoTicker['ticker'].ljust(20)}** {format_decimal(infoTicker['lagging_price'])} K: {format_decimal(infoTicker['kijun_price'])} {infoTicker['date']}" 
        shortDate = infoTicker['date'].split('-')[2] + "/" + infoTicker['date'].split('-')[1]
        # shortMessage = f"**{infoTicker['ticker']}** {format_decimal(infoTicker['lagging_price'])}/{format_decimal(infoTicker['kijun_price'])}/{shortDate}" 
        # shortMessage = f"{infoTicker['ticker'].ljust(13)} {format_decimal(infoTicker['lagging_price'])}/{format_decimal(infoTicker['kijun_price'])}/{shortDate}" 
        
        ticker=infoTicker['ticker'].replace(".PA","").replace("-USD","").replace("21794","").ljust(6)
        lagging=format_decimal(infoTicker['lagging_price']).rjust(7)
        kijun=format_decimal(infoTicker['kijun_price']).rjust(7)

        shortMessage = f"{ticker}|{lagging}|{kijun}|{shortDate}" 
        if infoTicker['weekly_action'] == 'buy':
            discordLog += "🟢" 
        if infoTicker['weekly_action'] == 'sell':
            discordLog += "🔴" 

        if infoTicker['action'] == 'buy':
            consoleLog += colorama.Fore.GREEN + shortMessage + colorama.Style.RESET_ALL + "\n"
            discordLog += "🟢" 
        if infoTicker['action'] == 'sell':
            consoleLog += colorama.Fore.RED + shortMessage + colorama.Style.RESET_ALL + "\n"
            discordLog += "🔴" 

        discordLog += shortMessage  + "\n"

    print(consoleLog)
    return discordLog

def get_info_tickers():
    ticker_list = [
                    "SGO.PA",       "ALO.PA",       "GTT.PA",
                    "VRLA.PA",
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
    start_date_day = (pd.to_datetime('today') - pd.DateOffset(days=90)).strftime('%Y-%m-%d')
    end_date = end_date = pd.to_datetime('today').strftime('%Y-%m-%d')

    start_date_weekly = (pd.to_datetime('today') - pd.DateOffset(days=(60)*7)).strftime('%Y-%m-%d')
    today = pd.to_datetime('today').date()
    start_of_current_week = today - pd.offsets.Week(weekday=0)
    end_of_last_week = start_of_current_week - pd.Timedelta(days=1)
    end_date_weekly = end_of_last_week.strftime('%Y-%m-%d')
 
    infoTickers = []
    for ticker in ticker_list:
        stock_daily_data = get_daily_stock_data(ticker, start_date_day, end_date)
        stock_daily_data = calculate_ichimoku(stock_daily_data)
        print(stock_daily_data.to_string())
        data_daily = check_ichimoku_crossover(ticker, 'DAILY', stock_daily_data)

        stock_weekly_data = get_weekly_stock_data(ticker, start_date_weekly, end_date_weekly)
        stock_weekly_data = calculate_ichimoku(stock_weekly_data)
        print(stock_weekly_data.to_string())

        data_weekly = check_ichimoku_crossover(ticker, 'WEEKLY', stock_weekly_data)

        data = data_daily
        data['weekly_action'] = data_weekly['action']

        infoTickers.append(data)

    return infoTickers


async def coinMonitoring(message):
    infoTickers = get_info_tickers()
    texte = generate_discord_message(infoTickers) + "\n"
    messages = texte.split('\n')  # Divise le texte en lignes

    taille_paquet = 20
    
    for i in range(0, len(messages), taille_paquet):
        paquet = messages[i:i+taille_paquet]
        await message.channel.send("```" + ("\n".join(paquet)) + "```")






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
                changed_info.append(info)
        else:
            changed_info.append(info)

    return changed_info

async def coinMonitoringDiff(message, rasMessage):

    filename = "./tmp/coinMonitoring.json"
    new_info = get_info_tickers()

    previous_info = load_previous_info(filename)
    changed_info = process_info(previous_info, new_info)

    if changed_info:
        print("Les changements suivants ont été détectés :")
        for change in changed_info:
            print(f"Ticker: {change['ticker']}, Action: {change['action']}")
        
        await message.channel.send("```" + generate_discord_message(changed_info) + "```")

        save_info(filename, {info["ticker"]: info["action"] for info in new_info})
    else:
        print("Aucun changement détecté.")
        await rasMessage.channel.send("RAS on " + str(len(new_info)) + " coins.")