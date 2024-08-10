import discord
from actions.hello import hello
from actions.pumpdump import pumpdump
# from actions.long_short import long_short
# from actions.chart import chart
from actions.wallet import wallet, resetTedyEquity, sendAmountTedy
from actions.wallet import wallet, resetTedyEquity, sendAmountTedy
from actions.coinMonitoring import coinMonitoring, coinMonitoringDiff
from actions.positions import positions
# from actions.flow import flow
from functions.functions import get_channel_id, get_bot_commands_enabled_channels, send_slack_message

import os
import logging
import traceback

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import ccxt.async_support as ccxt

from actions.poolConnector import ccxt_connectors
import hjson
import json
import requests

from functions.functions import get_pro_channel_enabled, send_slack_message


async def allHL(message):

    if not (message.channel.id in get_pro_channel_enabled()):
        return


    global ccxt_connectors

    api_keys_file = "../../api-keys.json"

    keys = ""
    if os.path.exists(api_keys_file) :
        keys = hjson.load(open(api_keys_file, encoding="utf-8"))
    else:
        return {'error' : 'Problem loading keys'}
    
    totalWallet = 0.0


    messageToSend = ""
    api_keys_users = ['hyperliquid_vault_tedy57123', 'hyperliquid_vault_tedybe550', 'hyperliquid_pro57123']
    for api_keys_user in api_keys_users:
        user_name = api_keys_user
        result = {'total' : {'USDC' : 0.0}}

        followersEquity = 0.0
        nbFollowers = 0

        if (keys[api_keys_user]['is_vault']):
            url = 'https://api-ui.hyperliquid.xyz/info'

            headers = {
                'content-type': 'application/json',
                'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'
            }

            data = {
                "type": "vaultDetails",
                "vaultAddress": keys[api_keys_user]['wallet_address']
            }

            response = requests.post(url, headers=headers, json=data)

            # Afficher le contenu de la réponse
            response_json = response.json()
            leaderEquity = 0.0
            i = 0
            for followers in response_json['followers']:
                if i == 0:
                    leaderEquity = float(followers['vaultEquity'])
                else:
                    followersEquity += float(followers['vaultEquity'])
                    nbFollowers = nbFollowers + 1
                i = i + 1

            usdc_value = leaderEquity

        else:
            if user_name in ccxt_connectors :
                ccxtOnline = ccxt_connectors[user_name]
            else:
                ccxtOnline = ccxt_connectors[user_name] = ccxt.hyperliquid({"walletAddress": keys[api_keys_user]['wallet_address'],"privateKey": keys[api_keys_user]['private_key']})

            result = await ccxtOnline.fetch_balance()
        
            usdc_value = round(result['total']['USDC'], 2)

        totalWallet += usdc_value

        user_name = user_name.replace('hyperliquid_', '')

        # Discord mobile = 29 caractères
        messageToSend += f"{user_name:<17} {usdc_value:>11,.2f}$\n"
        if nbFollowers > 0:
            messageToSend += f"{nbFollowers:>15}👥  {followersEquity:>11,.2f}💰\n"
        messageToSend += "\n"


    
    # await message.channel.send(f"Total : {totalWallet} $")

    messageToSend = "```" + messageToSend + "```"
    await message.channel.send(messageToSend)

    # send_slack_message(messageToSend)