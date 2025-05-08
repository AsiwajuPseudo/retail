#utilities
from datetime import datetime, timedelta
from collections import defaultdict
from bs4 import BeautifulSoup
import pandas as pd
import requests
import random
import math
import json
import re

class Utils:
	@staticmethod
	def group_orderbook_levels(levels, step):
	    grouped = defaultdict(float)  # {price_level: total_volume}
	    
	    for price_str, volume_str in levels:
	        price = float(price_str)
	        volume = float(volume_str)
	        
	        # Find the bin for the price
	        bin_price = math.floor(price / step) * step
	        grouped[bin_price] += volume

	    # Return sorted list
	    return sorted([[bin_price, volume] for bin_price, volume in grouped.items()])

	@staticmethod
	def get_candlesticks(raw_data, interval_minutes=15):
		df = pd.DataFrame(raw_data, columns=['timestamp', 'price'])
		df['timestamp'] = pd.to_datetime(df['timestamp'])
		df.set_index('timestamp', inplace=True)
		df_clean = df.dropna()
		if df_clean.empty:
			return []
		ohlc = df_clean['price'].resample(f'{interval_minutes}min').ohlc()
		ohlc.dropna(inplace=True)
		ohlc.reset_index(inplace=True)
		ohlc_data = []
		for _, row in ohlc.iterrows():
			ohlc_data.append({'time': int(row['timestamp'].timestamp()),'open': row['open'],'high': row['high'],'low': row['low'],'close': row['close'],'volume':0})
		return ohlc_data

	@staticmethod
	def simulate_order_book(data):
		bids = data.get('bids', [])
		asks = data.get('asks', [])
		if not bids or not asks:
			return data
		base_bid_price, base_bid_volume = bids[0]
		base_ask_price, base_ask_volume = asks[0]
		simulated_bids = [[base_bid_price, base_bid_volume]]
		simulated_asks = [[base_ask_price, base_ask_volume]]

		for i in range(1, 5):
			price = round(base_bid_price - i * random.uniform(0.1, 0.5), 2)
			volume = round(base_bid_volume * random.uniform(0.7, 1.2), 2)
			simulated_bids.append([price, volume])
		for i in range(1, 5):
			price = round(base_ask_price + i * random.uniform(0.1, 0.5), 2)
			volume = round(base_ask_volume * random.uniform(0.7, 1.2), 2)
			simulated_asks.append([price, volume])

		simulated_bids = sorted(simulated_bids, key=lambda x: x[0])
		simulated_asks = sorted(simulated_asks, key=lambda x: x[0])

		return {'bids': simulated_bids, 'asks': simulated_asks}
