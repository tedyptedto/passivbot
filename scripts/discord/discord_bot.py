import discord
import os
import logging
import traceback
from actions.hyperliquid import allHL
from actions.coinMonitoring import coinMonitoring, coinMonitoringDiff
from functions.functions import get_channel_id, get_bot_commands_enabled_channels
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger


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

#                                           ### Message incoming listener
class MyClient(discord.Client):

    #                                           ### Ready, print some debug info
    async def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

    #                                           ### Message incoming
    async def on_message(self, message):
        try:
            #                                           ### Don't reply to itself
            if message.author.id == self.user.id:
                return

            #                                           ### Only allowed channels
            if not (message.channel.id in get_bot_commands_enabled_channels()):
                return

            #                                           ### Split message
            a_message = message.content.split(' ')

            #                                           ### Ask coin monitoring with ichimoku
            if a_message[0] == '!m':
                await coinMonitoring(message)

            #                                           ### Ask HyperLiquid accounts
            if a_message[0] == '!all':
                await allHL(message, isAuto=False)
                
            #                                           ### Command to test a function
            if a_message[0] == '!t':
                await allHL(message, isAuto=False)
                

        except Exception as e:
            logging.error(traceback.format_exc())
            # Logs the error appropriately.
            await message.channel.send('Mauvaise commande.') 

client = MyClient()
base_dir = os.path.realpath(os.path.dirname(os.path.abspath(__file__))+'/')+'/'


#                                           ### AUTO function, run 1 time by day
async def show_wallet(Test=False):
    await client.wait_until_ready()

    #                                           ### Ask HyperLiquid accounts
    c = client.get_channel(get_channel_id("pro"))  
    data = {'content': "!all", 'channel': c}
    message = Struct(**data)
    await allHL(message, isAuto=True)

    #                                           ###  Ask coin monitoring with ichimoku (2 channel 1 for see it is working)
    c = client.get_channel(get_channel_id("monitoring"))  
    data = {'content': "!md_from_auto_bot_x15", 'channel': c}
    message = Struct(**data)
    c = client.get_channel(get_channel_id("test"))  
    data = {'content': "!md_from_auto_bot_x15", 'channel': c}
    rasMessage = Struct(**data)

    await coinMonitoringDiff(message, rasMessage)

  


#initializing scheduler
scheduler = AsyncIOScheduler()
#sends "Your Message" at 12PM and 18PM (Local Time)
scheduler.add_job(show_wallet, CronTrigger(hour="18", minute="0", second="0")) 
#starting the scheduler
scheduler.start()


client.run(open(base_dir+"/config/token.txt", 'r').read())

