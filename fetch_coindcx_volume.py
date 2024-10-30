import requests
import pandas as pd
from datetime import datetime


def fetch_volume_data():
    # API endpoint
    url = 'https://api.coindcx.com/exchange/ticker'

    try:
        # Fetch data from API
        response = requests.get(url)
        data = response.json()

        # Ensure that data is a list
        if not isinstance(data, list):
            print("Unexpected data format:", type(data))
            print("Data:", data)
            return

        # Initialize variables
        volume_data = []
        total_volume = 0.0
        # Filter and collect data for USDT pairs
        for item in data:
            if 'market' in item and item['market'].endswith('INR'):
                try:
                    # Convert 'volume' and 'last_price' to floats
                    volume = float(item['volume'])
                    last_price = float(item['last_price'])
                    total_volume += volume  # Accumulate total volume

                    volume_data.append({
                        'Coin': item['market'],
                        'Last Price': last_price,
                        '24h Volume (USDT)': volume,
                        'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'Total Count': ''  # Empty for individual coins
                    })
                except ValueError:
                    print(f"Invalid data for {item['market']}: volume or last_price is not a number.")
                    continue  # Skip this item if data is invalid

        # Calculate total count
        total_count = len(volume_data)

        # Append summary row to volume_data
        volume_data.append({
            'Coin': 'Total',
            'Last Price': '',
            '24h Volume (USDT)': total_volume,
            'Timestamp': '',
            'Total Count': total_count
        })

        # Create DataFrame
        df = pd.DataFrame(volume_data)

        # Save to CSV
        df.to_csv('coindcx_volume_data.csv', index=False)
        print('Data saved to coindcx_volume_data.csv')

        # Optional: Print total count and total volume
        print(f'Total number of coins: {total_count}')
        print(f'Total 24h Volume (USDT): {total_volume}')

    except Exception as e:
        print(f"An error occurred: {e}")
        # For detailed traceback, uncomment the next two lines:
        # import traceback
        # traceback.print_exc()


if __name__ == '__main__':
    fetch_volume_data()
