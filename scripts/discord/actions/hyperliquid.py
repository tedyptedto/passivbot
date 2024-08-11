import ccxt.async_support as ccxt
from actions.poolConnector import ccxt_connectors
import hjson
import requests
import os

from functions.functions import get_pro_channel_enabled, send_slack_message, sendAmountBistouf, send_slack_message


async def allHL(message, isAuto):

    global ccxt_connectors

    #                                           ### Only for available channels
    if not (message.channel.id in get_pro_channel_enabled()):
        return

    #                                           ### Load keys
    api_keys_file = "../../api-keys.json"

    keys = ""
    if os.path.exists(api_keys_file) :
        keys = hjson.load(open(api_keys_file, encoding="utf-8"))
    else:
        return {'error' : 'Problem loading keys'}
    
    #                                           ### Define the sum send to slak or private discord
    sumAccounts = { 
                    'tedy' : {
                                'accounts' : ['hyperliquid_vault_tedy57123', 'hyperliquid_vault_tedybe550'],
                                'auto' : 'sendAmountBistouf',
                                'manual' : 'sameChannel',
                                'sum' : 0.0,
                             },
                    'pro' : {
                                'accounts' : ['hyperliquid_pro57123'],
                                'auto' : 'send_slack_message',
                                'manual' : 'doNothing',
                                'sum' : 0.0,
                             },
    }

    #                                           ### Accounts to check
    api_keys_users = ['hyperliquid_vault_tedy57123', 'hyperliquid_vault_tedybe550', 'hyperliquid_pro57123']
    for api_keys_user in api_keys_users:
        messageToSend = ""
        user_name = api_keys_user
        result = {'total' : {'USDC' : 0.0}}

        followersEquity = 0.0
        nbFollowers = 0

        #                                           ### is Hyperliquid vault
        if (keys[api_keys_user]['is_vault']):

            await message.channel.send("https://app.hyperliquid.xyz/vaults/" + keys[api_keys_user]['wallet_address'])

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

        #                                           ### is Hyperliquid normal account
        else:
            if user_name in ccxt_connectors :
                ccxtOnline = ccxt_connectors[user_name]
            else:
                ccxtOnline = ccxt_connectors[user_name] = ccxt.hyperliquid({"walletAddress": keys[api_keys_user]['wallet_address'],"privateKey": keys[api_keys_user]['private_key']})

            result = await ccxtOnline.fetch_balance()
        
            usdc_value = round(result['total']['USDC'], 2)

        user_name = user_name.replace('hyperliquid_', '')

        # Discord mobile = 29 caractères
        messageToSend += f"{user_name:<16} {usdc_value:>11,.2f}$💰\n"
        if nbFollowers > 0:
            messageToSend += f"👥{nbFollowers:<15} {followersEquity:>10,.2f}$💰\n"
        messageToSend += "\n"

        await message.channel.send("```" + messageToSend + "```")

        # manage the sum part
        # Itération sur sumAccounts pour trouver et mettre à jour la somme
        for key, value in sumAccounts.items():
            if api_keys_user in value['accounts']:
                value['sum'] += usdc_value

    #                                           ### Manage sum of account and send it do good channel
    for userName, value in sumAccounts.items():

        subMessage = f"```Sum {userName} amount : {value['sum']:,.2f}$ ```"

        action = value['auto'] if isAuto else value['manual']

        if action == 'sendAmountBistouf':
            sendAmountBistouf(subMessage)
            await message.channel.send(subMessage)
        elif  action == 'send_slack_message':
            send_slack_message(subMessage)
        elif action == 'sameChannel':
            await message.channel.send(subMessage)
        elif action == 'doNothing':
            print('doNothing')
    
    # send_slack_message(messageToSend)