#Twitter Scraper module
import tweepy
from tweepy import OAuthHandler

#http client for sentiment analysis API
import http.client, json

#dates module
from datetime import datetime, date
from itertools import count
import time
import re

#trading terminal
import MetaTrader5 as mt5


# Store Twitter credentials from dev account
consumer_key = "consumer_key"
consumer_secret = "consumer_secret"
access_key = "access_key"
access_secret = "access_secret"

#text sentiment API key
sentiment_key = "sentiment_key"

# Pass twitter credentials to tweepy via its OAuthHandler
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_key, access_secret)
api = tweepy.API(auth)


# connect to the trade account without specifying a password and a server
mt5.initialize()

# account number in the top left corner of the MT5 terminal window
# the terminal database password is applied if connection data is set to be remembered
account_number = 555
authorized = mt5.login(account_number)

if authorized:
    print(f'connected to account #{account_number}')
else:
    print(f'failed to connect at account #{account_number}, error code: {mt5.last_error()}')

# store the equity of your account
account_info = mt5.account_info()
if account_info is None:
    raise RuntimeError('Could not load the account equity level.')
else:
    equity = float(account_info[10])

#crypto sign and keywords
CRYPTO='BTCUSD'
keywords =['Bitcoin', 'bitcoin', 'BITCOIN', 'btc', 'BTC']


#Get Technoking's latest tweet
def get_elons_tweet():
    """Get Elon's last tweet by user ID"""
    tweets = tweepy.Cursor(api.user_timeline,id="44196397", since=date.today(), tweet_mode='extended').items(1)

    #remove all invalid characters
    elons_last_tweet = [re.sub('[^A-Za-z0-9]+', ' ', tweet.full_text) for tweet in tweets]

    #re-try until it returns a value - tweepy API fails to return the tweet sometimes
    while not elons_last_tweet:
        tweets = tweepy.Cursor(api.user_timeline,id="44196397", since=date.today(), tweet_mode='extended').items(1)
        elons_last_tweet = [re.sub('[^A-Za-z0-9]+', ' ', tweet.full_text) for tweet in tweets]
    return elons_last_tweet[0]

def analyze_sentence():
    """Determine whether Elons Tweet is positive, negative or neutral"""
    tweet = get_elons_tweet()

    #fomat the request
    conn = http.client.HTTPSConnection("text-sentiment.p.rapidapi.com")
    payload = "text="+tweet
    headers = {
        'content-type': "application/x-www-form-urlencoded",
        'x-rapidapi-key': sentiment_key,
        'x-rapidapi-host': "text-sentiment.p.rapidapi.com"
        }

    #post the request
    conn.request("POST", "/analyze", payload, headers)

    #get response
    res = conn.getresponse()
    raw_tweet = res.read()

    #convert response to json
    json_tweet = json.loads(raw_tweet)
    return json_tweet['pos']

#buy bitcoin
def trade():
    """Check if Musk mentioned bitcoin with positive sentiment and open a buy position if so"""
    what_musk_said = get_elons_tweet()
    tweet_sentiment = analyze_sentence()

    # used to check if a position has already been placed
    positions = mt5.positions_get(symbol=CRYPTO)
    orders = mt5.orders_get(symbol=CRYPTO)
    symbol_info = mt5.symbol_info(CRYPTO)
    price = mt5.symbol_info_tick(CRYPTO).bid

    # perform logic check
    if any(keyword in what_musk_said for keyword in keywords) and tweet_sentiment > 0:
        print(f'the madlad said it - buying some!')

        # prepare the trade request
        if not mt5.initialize():
            raise RuntimeError(f'MT5 initialize() failed with error code {mt5.last_error()}')

        # check that there are no open positions or orders
        if len(positions) == 0 and len(orders) < 1:
            if symbol_info is None:
                print(f'{CRYPTO} not found, can not call order_check()')
                mt5.shutdown()

            # if the symbol is unavailable in MarketWatch, add it
            if not symbol_info.visible:
                print(f'{CRYPTO} is not visible, trying to switch on')
                if not mt5.symbol_select(CRYPTO, True):
                    print('symbol_select({}}) failed, exit', CRYPTO)

            #this represents 5% Equity. Minimum order is 0.01 BTC. Increase equity share if retcode = 10014
            lot = float(round(((equity / 5) / price), 2))

            # define stop loss and take profit
            sl = price - (price * 5) / 100
            tp = price + (price * 10) / 100
            request = {
                'action': mt5.TRADE_ACTION_DEAL,
                'symbol': CRYPTO,
                'volume': lot,
                'type': mt5.ORDER_TYPE_BUY,
                'price': price,
                'sl': sl,
                'tp': tp,
                'magic': 66,
                'comment': 'python-buy',
                'type_time': mt5.ORDER_TIME_GTC,
                'type_filling': mt5.ORDER_FILLING_IOC,
            }

            # send a trading request
            result = mt5.order_send(request)

            # check the execution result
            print(f'1. order_send(): by {CRYPTO} {lot} lots at {price}')

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                print(f'2. order_send failed, retcode={result.retcode}')

            #print the order result - anything else than retcode=10009 is an error in the trading request.
            print(f'2. order_send done, {result}')
            print(f'   opened position with POSITION_TICKET={result.order}')

        else:
            print(f'BUY signal detected, but {CRYPTO} has {len(positions)} active trade')

    else:
        print(f'He did not say it, he said: {what_musk_said} - OR sentiment was not positive')

#execute code every 5 seconds
if __name__ == '__main__':
    print('Press Ctrl-C / Ctrl-Q to stop.')
    for i in count():
        trade()
        print(f'Iteration {i}')
        time.sleep(5)
