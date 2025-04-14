from flask import Flask, send_file, make_response, request
import requests
import pandas as pd
from datetime import datetime
import io
import os
import pytz
import gspread
from google.oauth2.service_account import Credentials
import json
import base64
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load the base64-encoded credentials from the environment variable
encoded_credentials = os.getenv("GOOGLE_CREDENTIALS_BASE64")
if not encoded_credentials:
    raise ValueError(
        "GOOGLE_CREDENTIALS_BASE64 environment variable is not set")

# Decode the base64-encoded JSON
decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")

# Parse the JSON into a dictionary
credentials_dict = json.loads(decoded_credentials)

# Create the credentials object
credentials = Credentials.from_service_account_info(
    credentials_dict, scopes=['https://www.googleapis.com/auth/drive'])

# Function to write data to Google Sheets


def write_to_google_sheet(sheet_name, data):
    try:
        client = gspread.authorize(credentials)

        # Open the existing Google Sheet
        main_sheet = client.open("Volume Scrapper")

        # Create a new worksheet with the given sheet_name
        new_worksheet = main_sheet.add_worksheet(
            title=sheet_name, rows="1000", cols="20")

        # Prepare data for batch write
        header = list(data[0].keys())
        rows = [list(row.values()) for row in data]

        # Write header and data in a single batch operation
        new_worksheet.update([header] + rows)

        # Return success message and status code
        return f"Data successfully written to new worksheet: {sheet_name}", 200
    except gspread.exceptions.APIError as e:
        # Handle API errors
        return f"An API error occurred while writing to Google Sheet: {e}", 403
    except Exception as e:
        # Handle other exceptions
        return f"An unexpected error occurred: {e}", 500


def send_telegram_notification(message):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("Telegram bot environment variables are not set.")
        return

    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message}
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(
                f"Failed to send Telegram notification: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Error sending Telegram notification: {e}")


app = Flask(__name__)
port = os.getenv('PORT', default=10000)


@app.route('/coin-dcx-past-24h-volume', methods=['GET'])
def coin_dcx_past_24h_volume():
    try:
        # Get market suffix from query parameter
        market_suffix = request.args.get('market', 'INR')

        # API endpoint
        url = 'https://api.coindcx.com/exchange/ticker'

        # Fetch data from API
        response = requests.get(url)
        data = response.json()

        # Ensure that data is a list
        if not isinstance(data, list):
            return make_response(f"Unexpected data format: {type(data)}", 500)

        # Initialize variables
        volume_data = []
        total_volume = 0.0

        # Filter and collect data for specified market pairs
        for item in data:
            if 'market' in item and item['market'].endswith(market_suffix) and item['market'] != 'USDTINR':
                try:
                    # Convert 'volume' and 'last_price' to floats
                    volume = float(item['volume'])
                    last_price = float(item['last_price'])
                    total_volume += volume  # Accumulate total volume

                    # Get current time in India Standard Time
                    india_timezone = pytz.timezone('Asia/Kolkata')
                    india_time = datetime.now(
                        india_timezone).strftime('%Y-%m-%d %H:%M:%S')

                    volume_data.append({
                        'Coin': item['market'],
                        'Last Price': last_price,
                        '24h Volume': volume,
                        'Timestamp': india_time,
                        'Total Count': '',  # Empty for individual coins
                        '% Contribution': ''  # Placeholder for now
                    })
                except ValueError:
                    print(
                        f"Invalid data for {item['market']}: volume or last_price is not a number.")
                    continue  # Skip this item if data is invalid

        # Calculate total count
        total_count = len(volume_data)

        # Compute % contribution for each coin
        for coin_data in volume_data:
            coin_volume = coin_data['24h Volume']
            percent_contribution = (
                coin_volume / total_volume) * 100 if total_volume > 0 else 0
            coin_data['% Contribution'] = round(percent_contribution, 2)

        # Append summary row to volume_data
        volume_data.append({
            'Coin': 'Total',
            'Last Price': '',
            '24h Volume': total_volume,
            'Timestamp': '',
            'Total Count': total_count,
            '% Contribution': '100.00'  # Total contribution is 100%
        })

        # Write data to Google Sheets
        india_timezone = pytz.timezone('Asia/Kolkata')
        india_time = datetime.now(india_timezone).strftime('%Y-%m-%d')
        sheet_name = f"CoinDCX Volume Data {india_time}"
        message, status_code = write_to_google_sheet(sheet_name, volume_data)

        send_telegram_notification(message)
        return make_response(message, status_code)

    except Exception as e:
        error_message = f"An error occurred in /coin-dcx-past-24h-volume: {e}"
        print(error_message)
        return make_response(error_message, 500)


@app.route('/coin-switch-past-24h-volume', methods=['GET'])
def coin_switch_past_24h_volume():
    try:
        # Get market suffix from query parameter
        market_suffix = request.args.get('market', 'INR')

        # API endpoint
        url = 'https://coinswitch.co/pro/api/v1/realtime-rates/ticker/24hr/all-pairs?exchange=csx'

        # Fetch data from API
        response = requests.get(url)
        data = response.json()
        data = data['data']

        # Initialize variables
        volume_data = []
        total_volume = 0.0

        # Filter and collect data for specified market pairs
        for symbol, item in data.items():
            if symbol.endswith(market_suffix) and symbol != 'USDTINR':
                try:
                    volume = float(item['quoteVolume'])
                    last_price = float(item['openPrice'])
                    total_volume += volume  # Accumulate total volume

                    # Get current time in India Standard Time
                    india_timezone = pytz.timezone('Asia/Kolkata')
                    india_time = datetime.now(
                        india_timezone).strftime('%Y-%m-%d %H:%M:%S')

                    volume_data.append({
                        'Coin': symbol,
                        'Last Price': last_price,
                        '24h Volume': volume,
                        'Timestamp': india_time,
                        'Total Count': '',  # Empty for individual coins
                        '% Contribution': ''  # Placeholder for now
                    })
                except ValueError:
                    print(
                        f"Invalid data for {symbol}: volume or last_price is not a number.")
                    continue

        # Calculate total count
        total_count = len(volume_data)

        # Compute % contribution for each coin
        for coin_data in volume_data:
            coin_volume = coin_data['24h Volume']
            percent_contribution = (
                coin_volume / total_volume) * 100 if total_volume > 0 else 0
            coin_data['% Contribution'] = round(percent_contribution, 2)

        # Append summary row to volume_data
        volume_data.append({
            'Coin': 'Total',
            'Last Price': '',
            '24h Volume': total_volume,
            'Timestamp': '',
            'Total Count': total_count,
            '% Contribution': '100.00'  # Total contribution is 100%
        })

        # Write data to Google Sheets
        india_timezone = pytz.timezone('Asia/Kolkata')
        india_time = datetime.now(india_timezone).strftime('%Y-%m-%d')
        sheet_name = f"CoinSwitch Volume Data {india_time}"
        message, status_code = write_to_google_sheet(sheet_name, volume_data)

        send_telegram_notification(message)
        return make_response(message, status_code)

    except Exception as e:
        error_message = f"An error occurred in /coin-switch-past-24h-volume: {e}"
        print(error_message)
        return make_response(error_message, 500)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=port, debug=True)
