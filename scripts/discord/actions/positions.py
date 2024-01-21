# import requests
import time
# from pybit import usdt_perpetual
from pybit import HTTP  # supports inverse perp & futures, usdt perp, spot.
from functions.functions import get_pro_channel_enabled, send_slack_message
import os
import json
import hjson
import ccxt.async_support as ccxt

from actions.poolConnector import ccxt_connectors


def print_trade_info(info: dict, d_message) -> None:
    sens = info["side"]
    if info["side"] == "long":
        sens = "🟢"
    elif info["side"] == "short":
        sens = "🔴"
    # message = f"=================\n" \
    # Mobile affiche 25 caractères sur une ligne
    message =   (f"{sens}") \
              + (f"{int(info['notional'])}$ ").rjust(7) \
              + (f"{info['symbol'].split('/')[0]}").ljust(10) \
              + (f"{info['entryPrice']}").rjust(10) \
              + "\n" \
              + (f"{info['unrealizedPnl']:.2f}$").rjust(17) \
              + (f"{info['liquidationPrice']}").rjust(12) \
              + (f"\n") 
            #   f"-\n" 
            #   f"⚠ Levier : X{info['leverage']}\n" 
            #   f"👁️ Paires : {info['symbol']}\n" \
            #   f"▶ Prix d'entrée : {info['entry_price']}\n" \
            #   \
            #   f"🎯 TP 1 : {info['take_profit']}$\n" \
            #   f"🛑 SL : {info['stop_loss']}$" \
            #   f"\n================="
    # await d_message.channel.send(message)
    return message


async def trader_alert(d_message):


    a_message = d_message.content.split(' ')
    if len(a_message) < 2:
        await d_message.channel.send("Mauvais usage. Ex : !p tedy")
        return

    api_keys_user = "bybit_tedy"
    user_name = a_message[1]
    if a_message[1] == "tedy": 
        api_keys_user = "bybit_tedy"
    elif a_message[1] == "tedy1":
        api_keys_user = "bybit_tedySUB1"
    elif a_message[1] == "tedy2":
        api_keys_user = "bybit_tedySUB2"
    elif a_message[1] == "tedy3":
        api_keys_user = "bybit_tedySUB3"
    elif a_message[1] == "sawyer":
        api_keys_user = "bybit_sawyer"
    elif a_message[1] == "jojo":
        api_keys_user = "bybit_jojo"
    elif (a_message[1] == "pro") and (d_message.channel.id in get_pro_channel_enabled()):
        api_keys_user = "bybit_pro" 
    else:
        await d_message.channel.send("Mauvais user.")
        return 


    api_keys_file = "../../api-keys.json"

    keys = ""
    if os.path.exists(api_keys_file) :
        keys = hjson.load(open(api_keys_file, encoding="utf-8"))
    else:
        return {'error' : 'Problem loading keys'}

    # time.sleep(5)
    global ccxt_connectors
    if user_name in ccxt_connectors :
        ccxtOnline = ccxt_connectors[user_name]
    else:
        ccxtOnline = ccxt_connectors[user_name] = ccxt.bybit({"apiKey": keys[api_keys_user]['key'],"secret": keys[api_keys_user]['secret']})


    #while True:
    #print('ask position')
    x = await ccxtOnline.fetch_positions()  # recupere toutes les positions
    #print('end position')
    # print('ask close')
    # await ccxtOnline.close() 
    # print(json.dumps(x, indent=2))
    # print('end position')
    
    discord_message = ""
    total_position = 0
    total_gain = 0
    for i in x:
        # i = i["info"]
       
        if float(i["contracts"]) > 0:  # skip les positions vide
            discord_message += print_trade_info(i, d_message)
            total_position += float(i['notional'])
            total_gain += float(i['unrealizedPnl'])

    discord_message += "\nPositions : " + (f"{total_position:.2f}$").rjust(17)  
    discord_message += "\nGain      : " + (f"{total_gain:.2f}$").rjust(17)  


    await d_message.channel.send("```" + discord_message + "```")

async def positions(d_message):
    await trader_alert(d_message)


