import numpy as np
import pandas as pd
import pandas_datareader.data as pdr

from matplotlib import pyplot as plt
# import addcopyfighandler

from numpy import datetime64

import tweepy
from parse import compile
import hjson
import discord


async def flow(message, subdefined_message=""):

    await message.channel.send('Please wait...')


    def get_data(token_name='BTC'):
        pattern = "{} {token_amount:n} #{token} ({usd_amount:n} USD) transferred from {source} to {destination}\n\n{link}"

        # read config
        json_file = 'config/tweeter.json'
        json_base = hjson.load(open(json_file, encoding="utf-8"))

        bearer_token = json_base['bearer_token']
        client = tweepy.Client(bearer_token)

        user_handle = 'whale_alert'
        user_id = client.get_user(username=user_handle).data.id

        paginator = tweepy.Paginator(
            client.get_users_tweets,  # The method you want to use
            user_id,  # Some argument for this method
            exclude=['retweets', 'replies'],  # Some argument for this method
            start_time="2021-03-31T11:59:59Z",  # Some argument for this method
            max_results=100,  # How many tweets asked per request,
            tweet_fields=['created_at']
        )

        data = {'token': list(),
                'token_amount': list(),
                'usd_amount': list(),
                'source': list(),
                'destination': list(),
                'time': list(),
                'tweet_link': list(),
                'link': list()}
        try:
            p = compile(pattern)
            for tweet in paginator.flatten():
                tweet_text = tweet.data['text']
                if token_name in tweet_text:
                    r = p.parse(tweet_text)
                    if r is None:
                        continue
                    data['token'].append(r['token'])
                    data['token_amount'].append(r['token_amount'])
                    data['usd_amount'].append(r['usd_amount'])
                    data['source'].append(r['source'])
                    data['destination'].append(r['destination'])
                    data['time'].append(tweet.data['created_at'])
                    data['link'].append(r['link'])
                    data['tweet_link'].append(f'https://twitter.com/{user_handle}/status/{tweet.data["id"]}')

        except ValueError as exc:
            print('Rate limit!')
        return data


    token_name = 'BTC'
    df = pd.DataFrame(get_data(token_name=token_name))
    df = df.astype({'token_amount': np.int64, 'usd_amount': np.int64, 'time': datetime64})
    df_to_exchange = df[(df['source'] == 'unknown wallet') & (df['destination'] != 'unknown wallet')]
    # df = df[df['destination'] != 'unknown wallet']
    ax = df_to_exchange.plot(x="time", y=["usd_amount"], color='red')

    df_from_exchange = pd.DataFrame(get_data(token_name='USDT'))
    df_from_exchange = df_from_exchange.astype({'token_amount': np.int64, 'usd_amount': np.int64, 'time': datetime64})

    df_from_exchange = df_from_exchange[df_from_exchange['destination'] != 'Tether Treasury']
    # df_from_exchange = df[(df['source'] == 'unknown wallet') & (df['destination'] != 'unknown wallet')]
    df_from_exchange.plot(x="time", y=["usd_amount"], ax=ax, color='green')
    start = df['time'].iloc[-1]
    end = df['time'].iloc[0]
    df_price = pdr.DataReader(token_name + '-USD', 'yahoo', start, end)
    df_price.plot(y=["Adj Close"], ax=ax, secondary_y=True, color='blue', ylabel=f'{token_name} price')
    ax.legend(['usd amount from unknown wallet to exchange',
               'usd amount from exchange to unknown wallet',
               f'{token_name} price'])
    ax.set_ylabel('Equivalent in usd amount bought')
    ax.right_ax.set_ylabel(f'{token_name} price')
    plt.show()
    plt.savefig('tmp/flow.png')

    print(df_to_exchange.sort_values(by=['token_amount'])[:5].to_string())
    print(df_from_exchange[:5].to_string())

    await message.channel.send('Inflow/Outflow : ', file=discord.File('tmp/flow.png'))
