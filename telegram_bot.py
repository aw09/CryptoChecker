from binance_script import get_balance as binance_balance, client
from gate_script import get_balance as gate_balance
#from wallet_script import balance_usdt as wallet_balance
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
import operator as op

filename = 'balance_vs_btc.csv'
chartname = 'chart.png'
refresh_time = 3 * 60 # 15 minutes
wallet_balance = 0

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
    total_gate = gate_balance()
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
        'usdt_idr_rate': usdt_idr_rate,
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
    data = await updateData()
    message = textwrap.dedent(f"""
    {datetime.now()}
    USD to IDR Rate: {format(data['usdt_idr_rate'], ',.0f')}
          
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
    await updateData()
    
    start_date = context.args[0] if len(context.args) > 0 else None
    end_date = context.args[1] if len(context.args) > 1 else None

    df = pd.read_csv(filename)
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    formatter = FuncFormatter(millions)

    if start_date:
        df = df[df.index >= start_date]
    if end_date:
        df = df[df.index <= end_date]

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
    
    os.remove(chartname)
    plt.close()

async def check_alerts(context: ContextTypes.DEFAULT_TYPE):
    # Load the alerts from the CSV file
    df = pd.read_csv('alerts.csv')

    # Map the operator strings to actual operator functions
    operators = {'<': op.lt, '>': op.gt, '<=': op.le, '>=': op.ge, '==': op.eq}

    # Check each alert
    for index, row in df.iterrows():
        # Get the current price of the coin
        if 'Total' in row['coin']:
            balance_df = pd.read_csv(filename)
            current_price = float(balance_df.tail(1)[row['coin']].item())
        else:
            current_price = float(client.ticker_price(f"{row['coin']}USDT")['price'])

        # If the current price matches the alert condition, send an alert message and delete the alert
        if operators[row['operator']](current_price, row['price']):
            await context.bot.send_message(row['chat_id'], f'Price alert: {row["coin"]} is now {row["operator"]} {row["price"]}')
            df = df.drop(index)

    # Write the DataFrame back to the CSV file
    df.to_csv('alerts.csv', index=False, header=True)

async def list_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Load the alerts from the CSV file
    df = pd.read_csv('alerts.csv')

    # Filter the alerts for the current chat
    df = df[df['chat_id'] == update.message.chat_id]
    df = df.drop(columns='chat_id')

    # Format the DataFrame as a list of strings
    alerts = []
    for index, row in df.iterrows():
        alerts.append(f"{row['coin']} {row['operator']} {row['price']}")

    # Concatenate all alerts into a single string
    alerts_message = '\n'.join(alerts)

    # Send a message with the list of alerts
    await update.message.reply_text(alerts_message)

async def delete_alert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Check if the correct number of arguments were provided
    if len(context.args) != 1:
        await update.message.reply_text('Invalid number of arguments. Usage: /delete_alert <coin>')
        return

    # Get the chat_id from the update object and the coin name from the message
    chat_id = update.message.chat_id
    coin = context.args[0]

    # Load the alerts from the CSV file
    df = pd.read_csv('alerts.csv')

    # Delete the alert
    df = df[(df.chat_id != chat_id) | (df.coin != coin)]

    # Write the DataFrame back to the CSV file
    df.to_csv('alerts.csv', index=False, header=True)

    # Send a confirmation message
    await update.message.reply_text(f'Alert for {coin} deleted')


async def create_alert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Check if the correct number of arguments were provided
    if len(context.args) != 3:
        await update.message.reply_text('Invalid number of arguments. Usage: /create_alert <coin> <operator> <price>')
        return

    # Get the coin name, the operator, and the alert price from the message
    coin = context.args[0]
    operator = context.args[1]

    # Check if the operator is valid
    if operator not in ['<', '>', '<=', '>=', '==']:
        await update.message.reply_text('Invalid operator. Please use one of the following operators: <, >, <=, >=, ==')
        return

    # Check if the price is a valid number
    try:
        price = float(context.args[2])
    except ValueError:
        await update.message.reply_text('Invalid price. Please enter a valid number.')
        return

    # Create a DataFrame with the alert data
    df = pd.DataFrame([[update.message.chat_id, coin, operator, price]], columns=['chat_id', 'coin', 'operator', 'price'])

    # Check if the file exists
    if not os.path.isfile('alerts.csv'):
        df.to_csv('alerts.csv', mode='w', header=True, index=False)
    else:
        df.to_csv('alerts.csv', mode='a', header=False, index=False)

    # Send a confirmation message
    await update.message.reply_text(f'Alert created for {coin} {operator} {price}')

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("info", sendInfo))
    app.add_handler(CommandHandler("chart", sendChart))
    app.add_handler(CommandHandler("create_alert", create_alert))
    app.add_handler(CommandHandler("delete_alert", delete_alert))
    app.add_handler(CommandHandler("list_alerts", list_alerts))

    app.job_queue.run_repeating(updateData, interval=refresh_time, first=0)
    app.job_queue.run_repeating(check_alerts, interval=refresh_time, first=0)
    app.run_polling()

if __name__ == '__main__':
    main()
