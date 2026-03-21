import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

BASE_URL = "https://deribit.com/api/v2"

session = requests.Session()

historical_data_dic = {
    "BTC": {
    "strike_lower_bound" : 50000,
    "strike_upper_bound" : 100000,
    "file_path" : "btc_historical_greeks.parquet"
},
"ETH":{
    "strike_lower_bound" : 1500,
    "strike_upper_bound" : 4000,
    "file_path" : "eth_historical_greeks.parquet"
}
}


#####Data collection and processing functions#####

def convert_ts(ts_ms):
    ts_s = ts_ms / 1000  # convert milliseconds to seconds
    dt = datetime.utcfromtimestamp(ts_s)
    
    # Convert to Singapore Time (UTC+8)
    sg_dt = dt + timedelta(hours=8)
    return sg_dt

def safe_get(url, params=None, max_retries=5, base_sleep=0.5):
    for attempt in range(max_retries):
        response = session.get(url, params=params, timeout=20)

        if response.status_code == 429:
            sleep_time = base_sleep * (2 ** attempt)
            print(f"429 hit for {params}. Sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
            continue

        response.raise_for_status()
        return response

    raise RuntimeError(f"Too many 429 responses for {url} with params={params}")

def get_option_instruments(asset):
    url = f"{BASE_URL}/public/get_instruments"
    params = {"currency": asset, "kind": "option"}
    response = session.get(url, params=params)
    response.raise_for_status()
    return response.json()

def format_instruments(instruments_data):
    all_data = []
    results = instruments_data['result']
    for result in results:
        if result["state"] == "open" and result["is_active"] == True and result["instrument_type"] == "reversed":
            
            #modify formatting
            #tick size above
            tick_size_step_list = result["tick_size_steps"]
            for tick_size_step_dic in tick_size_step_list:
                price = tick_size_step_dic["above_price"]
                tick_size = tick_size_step_dic["tick_size"]
                result[f"tick_size_above_{price}"] = tick_size
            del result["tick_size_steps"]
            
            result["expiration_sg_dt"] = convert_ts(result["expiration_timestamp"])
            all_data.append(result)
            
    df = pd.DataFrame(all_data)
    return df

def get_instrument_dic(instrument_df):
    instrument_dic = {}

    for row in instrument_df.itertuples(index=False):
        instrument_dic[row.instrument_name] = {
            "expiration_sg_dt": row.expiration_sg_dt,
            "fees": max(row.maker_commission, row.taker_commission),
            "strike": row.strike,
        }

    return instrument_dic


def get_greeks_iv(instrument_name, instrument_dic):
    url = f"{BASE_URL}/public/ticker"
    params = {"instrument_name" : instrument_name}
    response = safe_get(url, params=params)
    response.raise_for_status()
    result = response.json()["result"]
    greeks = result.get("greeks")
    underlying_price = result.get("underlying_price")
    row = {
    "instrument_name": instrument_name,
    "option_type" : instrument_name[-1],

    "timestamp": convert_ts(result.get("timestamp")),
    "index_price": result.get("index_price"),
    "underlying_price": underlying_price,
    "strike" : instrument_dic[instrument_name]["strike"],
    "fees" : min(instrument_dic[instrument_name]["fees"] * underlying_price , 
             0.125 * result.get("best_bid_price") * underlying_price),
    "mark_price": result.get("mark_price") * underlying_price ,
    "mark_iv": result.get("mark_iv"),
    "bid_iv": result.get("bid_iv"),
    "ask_iv": result.get("ask_iv"),
    "best_bid_price": result.get("best_bid_price") * underlying_price,
    "best_ask_price": result.get("best_ask_price") * underlying_price,
    "best_bid_amount": result.get("best_bid_amount"),
    "best_ask_amount": result.get("best_ask_amount"),
    "open_interest": result.get("open_interest"),
    "expiration_sg_dt" : instrument_dic[instrument_name]["expiration_sg_dt"],


    "delta": greeks.get("delta"),
    "gamma": greeks.get("gamma"),
    "theta": greeks.get("theta") * (-1),
    "vega": greeks.get("vega"),
    "rho": greeks.get("rho"),
    
}
    if abs(greeks.get("delta")) > 0.5 or result.get("best_bid_price") < 0.0001:
        return None
    return row


def collect_greeks_iv(instrument_dic, max_workers=16):
    rows = []
    instrument_names = list(instrument_dic.keys())

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(get_greeks_iv, instrument_name, instrument_dic): instrument_name
            for instrument_name in instrument_names
        }

        for future in as_completed(futures):
            instrument_name = futures[future]
            try:
                if not future.result():
                    continue
                rows.append(future.result())
            except Exception as e:
                print(f"Failed for {instrument_name}: {e}")

    df = pd.DataFrame(rows)
    df["timestamp"] = df["timestamp"].max()

    return df


def save_data(asset, greeks_df, historical_data_dic, days_to_keep=30):
    strike_lower_bound = historical_data_dic["strike_lower_bound"]
    strike_upper_bound = historical_data_dic["strike_upper_bound"]
    file_path = historical_data_dic["file_path"]
    
    # Check if the file exists, if not create an empty file and DataFrame
    try:
        # Read the historical data
        historical_df = pd.read_parquet(file_path)
        # Get the list of active instruments
        active_instruments = [instrument["instrument_name"] for instrument in get_option_instruments(asset)["result"]]
        
        # Calculate the cutoff date for filtering timestamps
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Filter the historical data
        historical_df_filtered = historical_df[
            (historical_df["instrument_name"].isin(active_instruments)) &
            (historical_df["strike"] > strike_lower_bound) &
            (historical_df["strike"] < strike_upper_bound) &
            (historical_df["timestamp"] >= cutoff_date)  
        ]

    except FileNotFoundError:
        print(f"{file_path} not found. Creating an empty file.")
        historical_df_filtered = pd.DataFrame()  # Create an[] empty DataFrame
        Path(file_path).touch()  # Create an empty file
    

    
    # Filter the new greeks data
    greeks_df_filtered = greeks_df[
        (greeks_df["strike"] > strike_lower_bound) &
        (greeks_df["strike"] < strike_upper_bound)
    ]
    
    # Select relevant columns for saving
    greeks_df_to_save = greeks_df_filtered[[
        "instrument_name", "timestamp", "underlying_price", "strike", 
        "mark_iv", "expiration_sg_dt", "gamma", "theta"
    ]]
    
    # Combine the filtered historical data and new greeks data
    combined_df = pd.concat([historical_df_filtered, greeks_df_to_save], ignore_index=True).drop_duplicates()
    
    # Save the combined data back to the file
    combined_df.to_parquet(file_path, index=False)
    print("Updated data")
    return historical_df_filtered

def fetch_historical_data(historical_data_dic):
    file_path = historical_data_dic["file_path"]
    df = pd.read_parquet(file_path)

    return df