#threading and time are needed for our bot, so install those with pip as well if you haven't
import MetaTrader5 as mt5, time, threading
#time module is needed to select the range of our dataset
from datetime import datetime, date, time as datetime_time, timedelta
#connect to the trade account without specifying a password and a server
mt5.initialize()

#account number in the top left corner of the MT5 terminal window
account=##YOUR_ACCOUNT_NUMBER_HERE##
#the terminal database password is applied if connection data is set to be remembered
authorized=mt5.login(account)
if authorized:
    print("connected to account #{}".format(account))
else:
    print("failed to connect at account #{}, error code: {}".format(account, mt5.last_error()))

#store the equity of your account
account_info=mt5.account_info()
if account_info!=None:
    equity=float(account_info[10])

#dates will be used to define the range of our dataset in the get_data function
def get_dates():
    global utc_to, utc_from, from_date, to_date
    days_before = timedelta(days=1)
    todays_date = date.today()
    start_of_day = datetime_time(00,00,00)
    end_of_day = datetime_time(23,59,59)
    utc_to = datetime.now()
    utc_from = datetime.combine(todays_date, start_of_day) - days_before

#pull one day of 10 minute candles along with the buy and sell prices for bitcoin
def get_data():
    global candles, current_buy_price, current_sell_price
    #utc_from and utc_to in order to define the time period while mt5.TIMEFRAME_M10 defines the timeframes.
    candles = mt5.copy_rates_range("BTCUSD", mt5.TIMEFRAME_M10, utc_from, utc_to)
    current_buy_price = mt5.symbol_info_tick("BTCUSD")[2]
    current_sell_price = mt5.symbol_info_tick("BTCUSD")[1]
     #bid and ask price can also be defined as:
    price_buy=mt5.symbol_info_tick("BTCUSD").bid
    price_sell=mt5.symbol_info_tick("BTCUSD").ask

#build the logic and send the trade request to the MT5 terminal
def trade():
    global candles
    crypto = "BTCUSD"
    #calculate the % difference between the current price and the close price of the previous candle
    difference = (candles["close"][-1] - candles["close"][-2])/candles["close"][-2]*100
    symbol = crypto
    #used to check if a position has already been placed
    positions = mt5.positions_get(symbol=symbol)
    orders=mt5.orders_get(symbol=symbol)
    symbol_info = mt5.symbol_info(symbol)
    point = mt5.symbol_info(symbol).point

    #perform logic check
    if difference >3:
        print("dif 1:", crypto, difference)
        #Pause for 8 seconds to ensure the increase is sustained
        time.sleep(8)
        #calculate the difference once again
        candles = mt5.copy_rates_range(crypto, mt5.TIMEFRAME_M10, utc_from, utc_to)
        difference = (candles["close"][-1] - candles["close"][-2])/candles["close"][-2]*100
        if difference >3:
            print("dif 2:", crypto, difference)
            price=mt5.symbol_info_tick(symbol).bid
            print(crypto, "is up", "%" + str(difference), "in the last 5 minutes opening BUY position...")

            #prepare the trade request
            if not mt5.initialize():
                print("initialize() failed, error code =",mt5.last_error())
            #check that there are no open positions or orders
            if len(positions) == 0 and len(orders) < 1:
                if symbol_info is None:
                    print(symbol, "not found, can not call order_check()")
                    mt5.shutdown()
                    # if the symbol is unavailable in MarketWatch, add it
                if not symbol_info.visible:
                    print(symbol, "is not visible, trying to switch on")
                    if not mt5.symbol_select(symbol,True):
                        print("symbol_select({}}) failed, exit",symbol)
                lot = float(round(((equity/20)/current_buy_price),2))
                #define stop loss and take profit
                sl = price - (price*5)/100
                tp = price + (price*8)/100
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": lot,
                    "type": mt5.ORDER_TYPE_BUY,
                    "price": price,
                    "sl": sl,
                    "tp": tp,
                    "magic": 66,
                    "comment": "python-buy",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                # send a trading request
                result = mt5.order_send(request)
                # check the execution result
                print("1. order_send(): by {} {} lots at {}".format(symbol,lot,price));
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    print("2. order_send failed, retcode={}".format(result.retcode))
                    # request the result as a dictionary and display it element by element
                    result_dict=result._asdict()
                    for field in result_dict.keys():
                        print("   {}={}".format(field,result_dict[field]))
                        # if this is a trading request structure, display it element by element as well
                        if field=="request":
                            traderequest_dict=result_dict[field]._asdict()
                            for tradereq_filed in traderequest_dict:
                                print("       traderequest: {}={}".format(tradereq_filed,traderequest_dict[tradereq_filed]))
                print("2. order_send done, ", result)
                print("   opened position with POSITION_TICKET={}".format(result.order))
            else:
                print("BUY signal detected, but", symbol,'has' ,len(positions), 'active trade')
        else:
            (crypto, "price has fallen to", difference, " in the last 5 seconds")
    else:
        if len(orders) or len(positions) > 0:
            print("Buying signal detected but there is already an active trade")
        else:
            print("difference is only:", "%" + str(difference), "trying again...")
            
#add threading so the bot will always listen for chanchges in price. You can adjust the speed in the time.sleep.
def go_trade():
    i = 1
    while i != 0:
        get_dates()
        get_data()
        trade()
        i= i+1
        print (i)
        time.sleep(5)
thread = threading.Thread(target=go_trade)
thread.start()
thread.join()
