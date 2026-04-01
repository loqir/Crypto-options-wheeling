# Crypto Options Wheeling

This project pulls live crypto option data from Deribit and generates HTML dashboards to compare theta collection opportunities for a wheel-style strategy.

It is mainly meant to help answer two questions:

1. For a given strike, how do the theta across different expiries compare?
  
   1.1 How has this been changing over a recent time period?
   
3. For a given expiry, how do the theta across different strikes compare?


The project currently supports BTC and ETH and also saves a rolling history to view historical changes.

## What it does

The workflow is:

1. fetch option instruments from Deribit
2. collect greeks and pricing data in parallel
3. filter for OTM contracts
4. generate HTML dashboards
5. save historical snapshots to parquet files
6. build an index page linking all outputs


## Main files

- run.py: main script that runs the full workflow
- data_handling.py: Deribit API calls, filtering, and historical data storage
- plotting.py: Plotly chart creation and HTML export
- output/: generated HTML reports
- btc_historical_greeks.parquet / eth_historical_greeks.parquet: stored history
- .github/workflows/run-script.yml: scheduled GitHub Actions workflow

## Outputs

For each asset, the script generates:

- theta by strike
- theta by expiry
- time-series theta by strike
- an index page in output/index.html

The charts also include useful hover data such as IV, bid/ask, underlying price, gamma, and theta-to-gamma ratio.

## Run locally

Install dependencies:

```powershell
python -m venv wheeling
.\wheeling\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run the project:

```powershell
python run.py
```

Then open:

- output/index.html

## Notebook

Use run_execute.ipynb if you want to run the workflow interactively instead of from the terminal.

## Automation

The GitHub Actions workflow runs every 6 hours or on manual trigger. It:

1. installs dependencies
2. runs the script
3. updates generated HTML and parquet files
4. deploys the output to GitHub Pages

## Key assumptions

- data source is Deribit only
- supported assets are BTC and ETH
- contracts with `abs(delta) > 0.5` are filtered out
- historical strike ranges are manually set
- timestamps are converted to Singapore time

## Summary

At a high level, this repository is a Deribit-backed options screener for comparing where theta is most attractive across strikes, expiries, and recent history.
