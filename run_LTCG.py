# Monday Buying - LTCG Oriented - 
# Sell after one year at CMP if it is greater than TAKEPROFIT % else at TAKEPROFIT %

from os import listdir
from os.path import isfile, join
import pandas as pd
FILENAME = "./data/COLPAL.csv"

dfs = []
TAKEPROFIT = 10
CAPITAL = 5000

df = pd.read_csv(FILENAME)

# Delete unwanted columns
df.drop(['DontKnow', 'Volume'], axis=1, inplace=True)

# Convert date column to date type
df['Date'] = pd.to_datetime(df['Date'])

# Delete duplicates and sort
df = df.drop_duplicates(subset=['Date'])
df = df.sort_values(by='Date')

# df['weekday'] = datetime.datetime(2022, 10, 17).weekday() 
df['weekday'] = df['Date'].dt.dayofweek

#Optional
df = df[df['Date'].dt.year > 2015]

df[["Open", "High", "Low", "Close"]] = df[["Open", "High", "Low", "Close"]].apply(pd.to_numeric)
df['weekstart'] = ''
df = df.reset_index(drop=True)

for index, row in df.iterrows():
    if(row['weekday'] < df.iloc[index-1]['weekday']):
        df.at[index,'weekstart'] = True

boughtTrades = df.loc[df['weekstart'] == True]

boughtTrades['Qty'] = ''
boughtTrades['SoldOnDate'] = ''
boughtTrades['SoldAtPrice'] = ''
boughtTrades['GrossPL'] = ''
boughtTrades.rename(columns = {'Date':'BoughtOnDate', 'Open':'BoughtAtPrice'}, inplace = True)
boughtTrades.drop(['High', 'Low', 'Close', 'weekday', 'weekstart'], axis=1, inplace=True)

for idx, trade in boughtTrades.iterrows():
    targetPrice = round(trade['BoughtAtPrice'] + (trade['BoughtAtPrice'] * (TAKEPROFIT*2) / 100), 2)
    boughtTrades.at[idx,'Qty'] = round( CAPITAL / trade['BoughtAtPrice'] )
    
    # print(trade['BoughtOnDate'])
    # exit()

    sellTrade = None
    sellTrade = df.loc[(df['Date'] > trade['BoughtOnDate']+pd.DateOffset(365))]
    # sellTrade = df.loc[(df['Date'] > trade['BoughtOnDate'])]
    sellTrade = sellTrade.sort_values(by='Date')
    sellTrade = sellTrade.reset_index(drop=True)

    if( len(sellTrade.index) > 0 ):
        if(sellTrade.iloc[0]['Open'] > targetPrice):
            boughtTrades.at[idx,'SoldOnDate'] = sellTrade.iloc[0]['Date']
            boughtTrades.at[idx,'SoldAtPrice'] = round(sellTrade.iloc[0]['Open'], 2)
            continue
        else:
            sellTrade = df.loc[(df['High'] >= targetPrice) & (df['Date'] > trade['BoughtOnDate']+pd.DateOffset(365))]
            if( len(sellTrade.index) > 0 ):
                boughtTrades.at[idx,'SoldOnDate'] = sellTrade.iloc[0]['Date']
                boughtTrades.at[idx,'SoldAtPrice'] = round(targetPrice, 2)  
                continue      
            else:
                okk = 1          

    

    

# boughtTrades[['BoughtOnDate','SoldOnDate']] = pd.to_datetime(boughtTrades[['BoughtOnDate','SoldOnDate']], utc=True)
# boughtTrades[['BoughtOnDate','SoldOnDate']] = boughtTrades[['BoughtOnDate','SoldOnDate']].apply(pd.to_datetime)
boughtTrades['BoughtOnDate'] = pd.to_datetime(boughtTrades['BoughtOnDate'], utc=True)
boughtTrades['SoldOnDate'] = pd.to_datetime(boughtTrades['SoldOnDate'], utc=True)
boughtTrades['InvestmentDays'] = (boughtTrades['SoldOnDate'] - boughtTrades['BoughtOnDate']).dt.days

# boughtTrades.to_csv("./df.csv")

ledger = pd.DataFrame(columns=['TransactionDate','Price', 'Qty','Action','WalletBalance'])

for indexx, tradee in boughtTrades.iterrows():
    BuyRow = {'TransactionDate': tradee['BoughtOnDate'],'Price': tradee['BoughtAtPrice'],'Action': 'BUY', 'Qty': tradee['Qty']}
    ledger = ledger.append(BuyRow, ignore_index = True)
    SellRow = {'TransactionDate': tradee['SoldOnDate'],'Price': tradee['SoldAtPrice'],'Action': 'SELL', 'Qty': tradee['Qty']}
    ledger = ledger.append(SellRow, ignore_index = True)

ledger = ledger[~ledger['TransactionDate'].isna()].sort_values(by='TransactionDate')
print("Ledger compilation completed")

# Simulate Trades
ledger = ledger.reset_index(drop=True)
ledger[["WalletBalance"]] = ledger[["WalletBalance"]].apply(pd.to_numeric)
for ii, transaction in ledger.iterrows():
    if(ii == 0):
        ledger.at[ii,'WalletBalance'] = round(transaction['Price'] * transaction['Qty'] * (-1 if transaction['Action'] == 'BUY' else 1))
    else:
        ledger.at[ii,'WalletBalance'] = round(ledger.iloc[ii-1]['WalletBalance'] + transaction['Price'] * transaction['Qty'] * (-1 if transaction['Action'] == 'BUY' else 1))
print("Trade Simulation completed")


report = pd.DataFrame({'Years': ledger['TransactionDate'].dt.year.unique(), 'MaxCapital': '', 'RealizedGain': '', 'UnrealizedGain': ''})

for y, line in report.iterrows():
    report.at[y, 'MaxCapital'] = ledger[ledger['TransactionDate'].dt.year == line['Years']]['WalletBalance'].min() * -1

    RealizedGainDF = boughtTrades[(boughtTrades['SoldOnDate'].dt.year == line['Years']) & (~boughtTrades['InvestmentDays'].isna())]
    report.at[y, 'RealizedGain'] = round(((RealizedGainDF['SoldAtPrice'] - RealizedGainDF['BoughtAtPrice']) * RealizedGainDF['Qty']).sum())

    UnrealizedGainDF = boughtTrades[(boughtTrades['BoughtOnDate'].dt.year == line['Years']) & (boughtTrades['InvestmentDays'].isna())]
    report.at[y, 'UnrealizedGain'] = round(((UnrealizedGainDF['BoughtAtPrice'] * UnrealizedGainDF['Qty']) * 0.05).sum())

report[["RealizedGain", "MaxCapital"]] = report[["RealizedGain", "MaxCapital"]].apply(pd.to_numeric)
report['Percentage'] = round((report['RealizedGain'] * 100) / report['MaxCapital'])

report.to_csv('./'+str(TAKEPROFIT)+'_percent.csv')
print("Report Generated.")
