import requests
import json


channel_list = {
                "pro" : 958078641483427880,
                "passivbot" : 926406999107846245, 
                "test" : 955193076668829696, 
                "onlyupx3" : 910612726081024010, 
                "tedybot" : 956956942633414817, 
                "monitoring" : 1216851439863992441, 
}

def get_channel_id(channel_code):
    return channel_list[channel_code]

def get_bot_commands_enabled_channels():
    return [
                get_channel_id('pro'),
                get_channel_id('test'),
                get_channel_id('tedybot')
    ]

def get_pro_channel_enabled():
    return [get_channel_id('pro'), get_channel_id('test')]

def send_slack_message(text, blocks = None, file = None):
    slack_token = open("config/token_slack.txt", 'r').read().strip()
    slack_channel = '#wallet_prive'
    slack_icon_emoji = ':see_no_evil:'
    slack_user_name = 'WalletBot'
    requests.post('https://slack.com/api/chat.postMessage', {
        'token': slack_token,
        'channel': slack_channel,
        'text': text,
        'icon_emoji': slack_icon_emoji,
        'username': slack_user_name,
        'blocks': json.dumps(blocks) if blocks else None
    })

def sendAmountBistouf(message_content):
    # URL du webhook Discord
    webhook_url = "" #open("./config/webhook_tedy.txt", 'r').read()
    with open("./config/webhook_tedy.txt", 'r') as file:
        webhook_url = file.read().strip()

    # print("#" + webhook_url + "#")

    # Créer le payload pour le message
    payload = {
        "content": message_content
    }

    # Envoyer le message au webhook Discord
    response = requests.post(webhook_url, data=json.dumps(payload), headers={"Content-Type": "application/json"})

    # Vérifier si la requête a réussi
    if response.status_code == 204:
        print("Message envoyé avec succès")
    else:
        print(f"Erreur lors de l'envoi du message : {response.status_code} - {response.text}")


def print_trade_info(positions) -> None:

    discord_message = ""
    total_position = 0
    total_gain = 0
    for  position in positions:
        if float(position["contracts"]) > 0:  # skip les positions vide
            
            sens = position["side"]
            if position["side"] == "short":
                sens = "🔴"
            else:
                sens = "🟢"
            discord_message +=   (f"{sens}") \
                    + (f"{int(position['notional'])}$ ").rjust(7) \
                    + (f"{position['symbol'].split('/')[0]}").ljust(10) \
                    + (f"{position['entryPrice']}").rjust(10) \
                    + "\n" \
                    + (f"{position['unrealizedPnl']:.2f}$").rjust(17) \
                    + (f"{position['liquidationPrice']}").rjust(12) \
                    + (f"\n") 


            total_position += float(position['notional'])
            total_gain += float(position['unrealizedPnl'])

    discord_message += "\nPositions : " + (f"{total_position:.2f}$").rjust(17)  
    discord_message += "\nGain      : " + (f"{total_gain:.2f}$").rjust(17)  


    
    return discord_message