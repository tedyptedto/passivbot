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


# python3 -m pip install python-binance
# pip install ta
# pip install apscheduler
# pip install discord
# pip install plotly
# pip install kaleido
# https://github.com/Rapptz/discord.py
#d doc du framework : https://discordpy.readthedocs.io/en/latest/api.html#discord.Member

# problem pybit de syncronisation sur WSL :  sudo hwclock -s
#       sudo ntpdate pool.ntp.org

# sur server, forçage du resolv.conf en nameserver 10.5.0.1 (approximatif)
# script d'update du temps toutes les minuntes :
# /usr/sbin/service ntp stop
# /usr/sbin/ntpdate pool.ntp.org
# /usr/sbin/service ntp start
# /usr/sbin/hwclock --systohc


class Struct:
    def __init__(self, **entries):
        self.__dict__.update(entries)

class MyClient(discord.Client):
    async def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

        # Test part
        # await show_wallet(Test=True)
        #send_slack_message('Start Running')
        

    async def on_message(self, message):
        try:
            # we do not want the bot to reply to itself
            if message.author.id == self.user.id:
                return


            if not (message.channel.id in get_bot_commands_enabled_channels()):
                return

            a_message = message.content.split(' ')

            if a_message[0] == '!help':
                await message.channel.send('Commandes disponibles \n\
    !hello => just say hello :)\n\
    !p => positions\n\
    !w user => Show Wallet user=[tedy, jojo]\n\
    !all => Show all data for all users\n\
        ')

            if a_message[0] == '!hello':
                await hello(message)

            # if a_message[0] == '!chart':
            #     await chart(message)

            # if a_message[0] == '!flow':
            #     await flow(message)

            # if a_message[0] == '!ls':
            #     await long_short(message)

            # if a_message[0] == '!w':
            #     await wallet(message)

            if a_message[0] == '!m':
                await coinMonitoring(message)

            # if a_message[0] == '!mlocal':
            #     await coinMonitoring(message)
            if a_message[0] == '!t':
                global ccxt_connectors

                api_keys_file = "../../api-keys.json"

                keys = ""
                if os.path.exists(api_keys_file) :
                    keys = hjson.load(open(api_keys_file, encoding="utf-8"))
                else:
                    return {'error' : 'Problem loading keys'}
                
                totalWallet = 0.0

                api_keys_users = ['hyperliquid_vault_tedy57123', 'hyperliquid_vault_tedybe550', 'hyperliquid_pro57123']
                for api_keys_user in api_keys_users:



                    user_name = api_keys_user
                    result = {'total' : {'USDC' : 0.0}}

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
                        

                        result = {'total' : {'USDC' : float(response_json['followers'][0]['vaultEquity'])}}

                    else:
                        if user_name in ccxt_connectors :
                            ccxtOnline = ccxt_connectors[user_name]
                        else:
                            ccxtOnline = ccxt_connectors[user_name] = ccxt.hyperliquid({"walletAddress": keys[api_keys_user]['wallet_address'],"privateKey": keys[api_keys_user]['private_key']})

                        result = await ccxtOnline.fetch_balance()
                    
                    usdc_value = round(result['total']['USDC'], 2)

                    totalWallet += usdc_value

                    await message.channel.send(f"{user_name} : {usdc_value} $")
                
                # await message.channel.send(f"Total : {totalWallet} $")
                


            if a_message[0] == '!md_from_auto_bot_x15':
                c = client.get_channel(get_channel_id("test"))  
                data = {'content': "!md_from_auto_bot_x15", 'channel': c}
                rasMessage = Struct(**data)

                await coinMonitoringDiff(message, rasMessage)

            # if a_message[0] == '!p':
            #     await positions(message)

            if a_message[0] == '!all':

                #resetTedyEquity()

                message.content = "!t"
                await wallet(message)
                # message.content = "!w pro"
                # await wallet(message)
                # message.content = "!p pro"
                # await positions(message)

                # message.content = "!w tedy"
                # await wallet(message)
                # message.content = "!p tedy"
                # await positions(message)

                # message.content = "!w tedy1"
                # await wallet(message)
                # message.content = "!p tedy1"
                # await positions(message)

                # message.content = "!w tedy2"
                # await wallet(message)
                # message.content = "!p tedy2"
                # await positions(message)

                # message.content = "!w tedy3"
                # await wallet(message)
                # message.content = "!p tedy3"
                # await positions(message)

                # message.content = "!w sawyer"
                # await wallet(message)
                # message.content = "!p sawyer"
                # await positions(message)

                #sendAmountTedy()

            # Garé pour les infos
            # await message.channel.send('Hello {0.author.mention}'.format(message))
            # await message.channel.send('Hello {0.author.mention}'.format(message))
            # await message.channel.send('Hello {0.author}'.format(message))
        except Exception as e:
            logging.error(traceback.format_exc())
            # Logs the error appropriately.
            await message.channel.send('Mauvaise commande.') 

client = MyClient()
base_dir = os.path.realpath(os.path.dirname(os.path.abspath(__file__))+'/')+'/'

# sendAmountTedy()

async def show_wallet(Test=False):
    await client.wait_until_ready()

    resetTedyEquity()

    if not Test:
        # c = client.get_channel(get_channel_id("passivbot"))  
        # data = {'content': "!w tedy from_auto_bot_x15", 'channel': c}
        # message = Struct(**data)
        # await wallet(message)

        # c = client.get_channel(get_channel_id("passivbot"))  
        # data = {'content': "!w tedy1 from_auto_bot_x15", 'channel': c}
        # message = Struct(**data)
        # await wallet(message)

        # c = client.get_channel(get_channel_id("passivbot"))  
        # data = {'content': "!w tedy2 from_auto_bot_x15", 'channel': c}
        # message = Struct(**data)
        # await wallet(message)

        # c = client.get_channel(get_channel_id("passivbot"))  
        # data = {'content': "!w tedy3 from_auto_bot_x15", 'channel': c}
        # message = Struct(**data)
        # await wallet(message)

        # c = client.get_channel(get_channel_id("pro"))  
        # data = {'content': "!w pro from_auto_bot_x15", 'channel': c}
        # message = Struct(**data)
        # await wallet(message)

        c = client.get_channel(get_channel_id("pro"))  
        data = {'content': "!t", 'channel': c}
        message = Struct(**data)
        await wallet(message)

        # c = client.get_channel(get_channel_id("pro"))  
        # data = {'content': "!w sawyer from_auto_bot_x15", 'channel': c}
        # message = Struct(**data)
        # await wallet(message)

        c = client.get_channel(get_channel_id("monitoring"))  
        data = {'content': "!md_from_auto_bot_x15", 'channel': c}
        message = Struct(**data)
        c = client.get_channel(get_channel_id("test"))  
        data = {'content': "!md_from_auto_bot_x15", 'channel': c}
        rasMessage = Struct(**data)

        await coinMonitoringDiff(message, rasMessage)

        # c = client.get_channel(get_channel_id("onlyupx3"))  
        # data = {'content': "!w jojo from_auto_bot_x15", 'channel': c}
        # message = Struct(**data)
        # await wallet(message)

        # sendAmountTedy()
        
    else:
        # c = client.get_channel(get_channel_id("monitoring"))  
        # data = {'content': "!md_from_auto_bot_x15", 'channel': c}
        # message = Struct(**data)
        # await coinMonitoringDiff(message)
        print("test")

    


#initializing scheduler
scheduler = AsyncIOScheduler()
#sends "Your Message" at 12PM and 18PM (Local Time)
scheduler.add_job(show_wallet, CronTrigger(hour="18", minute="0", second="0")) 
#starting the scheduler
scheduler.start()


client.run(open(base_dir+"/config/token.txt", 'r').read())

