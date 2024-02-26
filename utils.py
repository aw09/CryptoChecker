from datetime import datetime, timedelta
import time

def format_currency(amount):
    return "{:,.2f}".format(amount)


def timestamp_to_date(timestamp):
    timestamp = timestamp / 1000
    date = datetime.fromtimestamp(timestamp)

    return date

def subtract_days_from_timestamp(timestamp, days):
    timestamp = timestamp / 1000
    date = datetime.fromtimestamp(timestamp)
    date = date - timedelta(days=days)
    timestamp = int(date.timestamp() * 1000)

    return timestamp

def get_timestamp_now():
    # Get the current date and time
    now = datetime.now()

    # Convert to timestamp (in seconds)
    timestamp_now = int(time.mktime(now.timetuple()))

    # Convert to milliseconds
    return timestamp_now * 1000

def get_datetime_now():
    return datetime.now()