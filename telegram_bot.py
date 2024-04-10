from binance_script import get_balance as binance_balance, client
from gate_script import balance as gate_balance
from wallet_script import balance_usdt as wallet_balance
import os
import pandas as pd
from datetime import datetime
from configs import TELEGRAM_TOKEN
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from matplotlib.ticker import FuncFormatter
import matplotlib.pyplot as plt
from datetime import datetime
import textwrap
from functools import wraps

filename = 'balance_vs_btc.csv'
chartname = 'chart.png'
refresh_time = 15 * 60 # 15 minutes

def read_whitelist():
    with open('whitelist.txt', 'r') as file:
        usernames = file.read().splitlines()
    return usernames

def authorization(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_user.username not in read_whitelist() and str(update.effective_user.id) not in read_whitelist():
            await update.message.reply_text('You are not authorized to use this bot.')
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

async def updateData(*args, **kwargs):
    total_binance, usdt_idr_rate = binance_balance()
    total_gate = gate_balance
    manta_bitget = 325
    manta_price = client.ticker_price("MANTAUSDT")
    total_bitget = manta_bitget * float(manta_price['price'])
    total_usdt = total_binance + total_gate + wallet_balance + total_bitget
    total_idr = total_usdt * usdt_idr_rate
    btc_price = client.ticker_price("BTCUSDT")['price']
    total_btc = total_usdt / float(btc_price)

    # Check if the file exists
    file_exists = os.path.isfile(filename)

    df = pd.DataFrame({
        'Date': [datetime.now()],
        'BTC_Price': [btc_price],
        'Binance_USDT': [total_binance],
        'Gate_USDT': [total_gate],
        'Other_USDT': [total_bitget + wallet_balance],
        'Total_BTC': [total_btc],
        'Total_USDT': [total_usdt],
        'Total_IDR': [total_idr]
    })

    # Append the DataFrame to the CSV file
    df.to_csv(filename, mode='a', header=not file_exists, index=False)

    result = {
        'btc_price': btc_price,
        'total_binance': total_binance,
        'usdt_idr_rate': usdt_idr_rate,
        'total_gate': total_gate,
        'total_bitget': total_bitget,
        'total_usdt': total_usdt,
        'total_idr': total_idr,
        'total_btc': total_btc
    }

    return result



@authorization
async def sendInfo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = updateData()
    message = textwrap.dedent(f"""
    {datetime.now()}
          
    === BINANCE ===
    Total Asset in USDT: {format(data['total_binance'], ',.0f')}
    Total Asset in IDR: {format(data['total_binance'] * data['usdt_idr_rate'], ',.0f')}

    === GATE.IO ===
    Total Asset in USDT: {data['total_gate']}
    Total Asset in IDR: {format(data['total_gate'] * data['usdt_idr_rate'], ',.0f')}

    === Bitget ===
    Total Asset in USDT: {format(data['total_bitget'], ',.0f')}
    Total Asset in IDR: {format(data['total_bitget'] * data['usdt_idr_rate'], ',.0f')}

    === TOTAL ===
    BTC Price: {data['btc_price']}
    Total Asset in USDT: {format(data['total_usdt'], ',.0f')}
    Total Asset in IDR: {format(data['total_idr'], ',.0f')}
    Total Asset in BTC: {format(data['total_btc'], ',.8f')}
    """)
    
    await update.message.reply_text(message)



def millions(x, pos):
    'The two args are the value and tick position'
    return '%1.1fM' % (x * 1e-6)


@authorization
async def sendChart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    df = pd.read_csv(filename)
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    formatter = FuncFormatter(millions)

    # Create a figure and a set of subplots
    fig, axs = plt.subplots(3, 1, figsize=(10, 10))

    # Plot the BTC price data on the first subplot
    axs[0].plot(df.index, df['BTC_Price'], color='g', label='BTC Price')
    axs[0].set_ylabel('BTC Price')
    axs[0].set_title('BTC Price and Total BTC Over Time')
    axs[0].legend(loc='upper left')

    # Create a second y-axis for the first subplot that shares the same x-axis
    ax4 = axs[0].twinx()

    # Plot the Total BTC data on the second y-axis of the first subplot
    ax4.plot(df.index, df['Total_BTC'], color='b', label='Total BTC')
    ax4.set_ylabel('Total BTC')
    ax4.legend(loc='upper right')

    # Plot the Binance USDT data on the second subplot
    axs[1].plot(df.index, df['Binance_USDT'], color='r', label='Binance USDT')
    axs[1].set_ylabel('Binance USDT')
    axs[1].set_title('Binance and Gate io USDT Value Over Time')
    axs[1].legend(loc='upper left')


    # Create a second y-axis for the second subplot that shares the same x-axis
    ax2 = axs[1].twinx()


    # Plot the Gate io USDT data on the second y-axis of the second subplot
    ax2.plot(df.index, df['Gate_USDT'], color='b', label='Gate USDT')
    ax2.set_ylabel('Gate USDT')
    ax2.legend(loc='upper right')

    # Plot the USDT data on the second subplot
    axs[2].plot(df.index, df['Total_USDT'], color='r', label='USDT')
    axs[2].set_ylabel('Value in USDT')
    axs[2].set_title('USDT and IDR Value Over Time')
    axs[2].legend(loc='upper left')

    # Create a second y-axis for the second subplot that shares the same x-axis
    ax3 = axs[2].twinx()

    # Plot the IDR data on the second y-axis of the second subplot
    ax3.plot(df.index, df['Total_IDR'], color='b', label='IDR')
    ax3.set_ylabel('Value in IDR')
    ax3.legend(loc='upper right')

    # Apply the formatter to the y-axis of the second plot
    ax3.yaxis.set_major_formatter(formatter)

    # Adjust the layout
    plt.tight_layout()

    # Show the plot
    plt.savefig(chartname)
    with open(chartname, 'rb') as photo:
        last_modified = datetime.fromtimestamp(os.path.getmtime(filename))
        await update.message.reply_photo(photo=photo, caption=f"{last_modified}")


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("info", sendInfo))
    app.add_handler(CommandHandler("chart", sendChart))

    app.job_queue.run_repeating(updateData, interval=refresh_time, first=0)
    app.run_polling()

if __name__ == '__main__':
    main()