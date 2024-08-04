import requests

def get_top_cryptos(numberCoins):
    # Faire une requête à l'API CoinGecko pour obtenir les 50 premières cryptomonnaies par market cap
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",  # Récupérer les prix en dollars US
        "order": "market_cap_desc",  # Trier par ordre décroissant de market cap
        "per_page": numberCoins,  # Nombre de cryptos à récupérer
        "page": 1,  # Page de résultats
        "category": "cryptocurrency",  # Exclure les stablecoins
    }
    response = requests.get(url, params=params)
    data = response.json()

    # print(data)

    # Parcourir les données et extraire le nom et le market cap de chaque cryptomonnaie
    top_cryptos = []
    for crypto in data:
        name = crypto["name"]
        market_cap = crypto["market_cap"]
        symbol = crypto["symbol"]
        top_cryptos.append({"name": name, "market_cap": market_cap, "symbol": symbol})


    return top_cryptos

if __name__ == "__main__":
    top_50_cryptos = get_top_cryptos(20)
    print("Top 50 Cryptomonnaies par Market Cap :")
    for crypto in top_50_cryptos:
        print(f"{crypto['symbol']} / {crypto['name']} / ${crypto['market_cap']}")