from data_handling import *
from plotting import export_html, export_time_series_html
import os

def execute(asset, time_series=True):
    # Ensure the output directory exists
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    instruments_data = get_option_instruments(asset)
    df = format_instruments(instruments_data)
    instrument_dic = get_instrument_dic(df)
    greeks_df = collect_greeks_iv(instrument_dic, max_workers=8)
    update_time = greeks_df.iloc[0]["timestamp"]

    # Exports
    # Theta by strike
    theta_by_strike_html = export_html(
        df=greeks_df,
        output_file=os.path.join(output_dir, f"{asset}_theta_by_strike.html"),
        group_by_col="strike",
        x_col="expiration_sg_dt",
        y_col="theta",
        page_title="Theta across expiries by strike",
        summary_text=f"One chart per strike, Theta against Expiry. Last updated {update_time}."
    )
    print(theta_by_strike_html)

    # Theta by expiry
    theta_by_expiry_html = export_html(
        df=greeks_df,
        output_file=os.path.join(output_dir, f"{asset}_theta_by_expiry.html"),
        group_by_col="expiration_sg_dt",
        x_col="strike",
        y_col="theta",
        page_title="Theta across strikes by expiry",
        summary_text=f"One chart per expiry, Theta against Strike. Last updated {update_time}."
    )
    print(theta_by_expiry_html)

    if time_series:
        asset_historical_data_dic = historical_data_dic[asset]
        previous_historical_df = save_data(asset, greeks_df, asset_historical_data_dic)
        historical_df = fetch_historical_data(asset_historical_data_dic)

        # Theta by strike time series
        time_series_theta_by_strike_html = export_time_series_html(
            df=historical_df,
            output_file=os.path.join(output_dir, f"{asset}_time_series_theta_by_strike.html"),
            group_by_col="strike",
            x_col="timestamp",
            y_col="theta",
            page_title="Time Series - Theta across expiries by strike",
            summary_text=f"One chart per strike, Theta against Expiry. Last updated {update_time}."
        )
        print(time_series_theta_by_strike_html)

    print("Execution complete")

if __name__ == "__main__":
    execute("BTC")
    execute("ETH")