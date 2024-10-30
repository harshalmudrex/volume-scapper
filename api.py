from flask import Flask, send_file, make_response, request
import requests
import pandas as pd
from datetime import datetime
import io
import os
import pytz


app = Flask(__name__)
port = os.getenv('PORT', default=10000)


@app.route('/download-csv', methods=['GET'])
def download_csv():
    # Get market suffix from query parameter
    market_suffix = request.args.get('market', 'INR')

    # API endpoint
    url = 'https://api.coindcx.com/exchange/ticker'

    try:
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
                    india_time = datetime.now(india_timezone).strftime('%Y-%m-%d %H:%M:%S')

                    volume_data.append({
                        'Coin': item['market'],
                        'Last Price': last_price,
                        '24h Volume': volume,
                        'Timestamp': india_time,
                        'Total Count': '',  # Empty for individual coins
                        '% Contribution': ''  # Placeholder for now

                    })
                except ValueError:
                    print(f"Invalid data for {item['market']}: volume or last_price is not a number.")
                    continue  # Skip this item if data is invalid

        # Calculate total count
        total_count = len(volume_data)

        # Compute % contribution for each coin
        for coin_data in volume_data:
            coin_volume = coin_data['24h Volume']
            percent_contribution = (coin_volume / total_volume) * 100 if total_volume > 0 else 0
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

        # Create DataFrame
        df = pd.DataFrame(volume_data)

        # Convert DataFrame to CSV in memory
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        # Create response
        response = make_response(csv_buffer.getvalue())
        filename = f'coindcx_volume_data_{market_suffix}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        response.headers['Content-Type'] = 'text/csv'

        return response

    except Exception as e:
        # For detailed traceback, uncomment the next two lines:
        # import traceback
        # traceback.print_exc()
        return make_response(f"An error occurred: {e}", 500)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=port, debug=True)
