# This program backtests a Lazy investment idea that buys
# a specific stock every Monday and sells at a constant percentage
# in gain. It does deduct Short term capital gain tax of 15% in final reports.
# The weekly capital is constant across all trades.
# This is an unoptimized version of python code.

from os import listdir
from os.path import isfile, join
import pandas as pd
SYMBOL = "COLPAL"
FILENAME = "./data/"+SYMBOL+".csv"

dfs = []
TAKEPROFIT = 5
CAPITAL = 5000

# Import the OHCL data
df = pd.read_csv(FILENAME)

# Delete unwanted columns
df.drop(['DontKnow', 'Volume'], axis=1, inplace=True)

# Convert date column to date type
df['Date'] = pd.to_datetime(df['Date'])

# Delete duplicates and sort
df = df.drop_duplicates(subset=['Date'])
df = df.sort_values(by='Date')

# Mark the day of week in numbers, starting Monday = 0
df['weekday'] = df['Date'].dt.dayofweek

#Optional
df = df[df['Date'].dt.year > 2015]

#Convert Columns to numeric types
df[["Open", "High", "Low", "Close"]] = df[["Open", "High", "Low", "Close"]].apply(pd.to_numeric)
df['weekstart'] = pd.Series(dtype=bool)
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
boughtTrades['BoughtOnDate'] = pd.to_datetime(df['Date'])
boughtTrades = boughtTrades.reset_index(drop=True)
boughtTrades = boughtTrades.sort_values(by='BoughtOnDate')

for idx, trade in boughtTrades.iterrows():
    targetPrice = round(trade['BoughtAtPrice'] + (trade['BoughtAtPrice'] * TAKEPROFIT / 100), 2)    

    sellTrade = None
    sellTrade = df.loc[(df['High'] >= targetPrice) & (df['Date'] > trade['BoughtOnDate'])]
    # sellTrade = df.loc[(df['Date'] > trade['BoughtOnDate'])]
    sellTrade = sellTrade.sort_values(by='Date')
    sellTrade = sellTrade.reset_index(drop=True)
    boughtTrades.at[idx,'Qty'] = round( CAPITAL / trade['BoughtAtPrice'] )

    if( len(sellTrade.index) > 0 ):
        boughtTrades.at[idx,'SoldOnDate'] = sellTrade.iloc[0]['Date']
        boughtTrades.at[idx,'SoldAtPrice'] = round(targetPrice, 2)        
    else:
        okk = 1

# boughtTrades[['BoughtOnDate','SoldOnDate']] = pd.to_datetime(boughtTrades[['BoughtOnDate','SoldOnDate']], utc=True)
# boughtTrades[['BoughtOnDate','SoldOnDate']] = boughtTrades[['BoughtOnDate','SoldOnDate']].apply(pd.to_datetime)
boughtTrades['BoughtOnDate'] = pd.to_datetime(boughtTrades['BoughtOnDate'], utc=True)
boughtTrades['SoldOnDate'] = pd.to_datetime(boughtTrades['SoldOnDate'], utc=True)
boughtTrades['InvestmentDays'] = (boughtTrades['SoldOnDate'] - boughtTrades['BoughtOnDate']).dt.days
boughtTrades[['SoldAtPrice', 'BoughtAtPrice']] = boughtTrades[['SoldAtPrice', 'BoughtAtPrice']].apply(pd.to_numeric)
boughtTrades['GrossPL'] = (boughtTrades['SoldAtPrice'] - boughtTrades['BoughtAtPrice']) * boughtTrades['Qty']

profitDF = boughtTrades[~boughtTrades['InvestmentDays'].isna()].copy()
profitDF['Utilized'] = ''
profitDF.drop(['BoughtOnDate', 'BoughtAtPrice', 'Qty', 'SoldAtPrice', 'InvestmentDays'], axis=1, inplace=True)
profitDF = profitDF.sort_values(by='SoldOnDate')
profitDF = profitDF.reset_index(drop=True)

# Logic for profit re-investment - Starts
for k, trd in boughtTrades.iterrows():
    tempDF = profitDF[(profitDF['SoldOnDate'] < trd['BoughtOnDate']) & (profitDF['Utilized'] == '')]
    if(len(tempDF.index) > 0):
        NEW_CAPITAL = CAPITAL + round(tempDF['GrossPL'].sum())
        NEW_QTY = round(NEW_CAPITAL / trd['BoughtAtPrice'])
        if(NEW_QTY == trd['Qty']):
            continue
        else:
            boughtTrades.at[k, 'Qty'] = round(NEW_CAPITAL / trd['BoughtAtPrice'])
            profitDF.at[tempDF.index, 'Utilized'] = 'X'
# Logic for profit re-investment - Ends

ledger = pd.DataFrame(columns=['TransactionDate','Price', 'Qty','Action','WalletBalance'])

for indexx, tradee in boughtTrades.iterrows():
    BuyRow = {'TransactionDate': tradee['BoughtOnDate'],'Price': tradee['BoughtAtPrice'],'Action': 'BUY', 'Qty': tradee['Qty']}
    ledger = ledger.append(BuyRow, ignore_index = True)
    SellRow = {'TransactionDate': tradee['SoldOnDate'],'Price': tradee['SoldAtPrice'],'Action': 'SELL', 'Qty': tradee['Qty']}
    ledger = ledger.append(SellRow, ignore_index = True)

ledger = ledger[~ledger['TransactionDate'].isna()].sort_values(by='TransactionDate')
print("(1/3) - Ledger compilation completed")

# Simulate Trades
ledger = ledger.reset_index(drop=True)
ledger[["WalletBalance"]] = ledger[["WalletBalance"]].apply(pd.to_numeric)
for ii, transaction in ledger.iterrows():
    ledger.at[ii,'WalletBalance'] = round((0 if ii == 0 else ledger.iloc[ii-1]['WalletBalance']) + transaction['Price'] * transaction['Qty'] * (-1 if transaction['Action'] == 'BUY' else 1))

print("(2/3) - Trade Simulation completed)")

# Build a report
report = pd.DataFrame({'Years': ledger['TransactionDate'].dt.year.unique(), 'MaxCapital': '', 'RealizedGain': '', 'UnrealizedGain': ''})
for y, line in report.iterrows():
    report.at[y, 'MaxCapital'] = ledger[(ledger['TransactionDate'].dt.year == line['Years']) * (ledger['Action'] == 'BUY')]['WalletBalance'].min() * -1

    RealizedGainDF = boughtTrades[(boughtTrades['SoldOnDate'].dt.year == line['Years']) & (~boughtTrades['InvestmentDays'].isna())]
    report.at[y, 'RealizedGain'] = round(((RealizedGainDF['SoldAtPrice'] - RealizedGainDF['BoughtAtPrice']) * RealizedGainDF['Qty']).sum())

    UnrealizedGainDF = boughtTrades[(boughtTrades['BoughtOnDate'].dt.year == line['Years']) & (boughtTrades['InvestmentDays'].isna())]
    report.at[y, 'UnrealizedGain'] = round(((UnrealizedGainDF['BoughtAtPrice'] * UnrealizedGainDF['Qty']) * 0.05).sum())

report[["RealizedGain", "MaxCapital"]] = report[["RealizedGain", "MaxCapital"]].apply(pd.to_numeric)
report['PAT'] = (report['RealizedGain']) - ((report['RealizedGain'] + report['UnrealizedGain'])*15/100)
report['PAT'] = report['PAT'].apply(pd.to_numeric)
report['PAT (%)'] = round((report['PAT'] * 100) / report['MaxCapital'])

# report = report.append({'MaxCapital': report['MaxCapital'].max(), 'RealizedGain': report['RealizedGain'].sum(), 'UnrealizedGain': report['UnrealizedGain'].sum(), 'PAT': report['PAT'].sum()}, ignore_index=True)
# report = report.append({}, ignore_index=True)

report.to_csv('./STCG_'+str(TAKEPROFIT)+'_percent_'+SYMBOL+'.csv')
print(report)
print("(3/3) - Report Generated.")

print("Max Capital Consumed = "+str(report['MaxCapital'].max()))
print("TOTAL PAT = "+str(report['PAT'].sum()))
