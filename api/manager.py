from __future__ import annotations
from threading import Thread, Lock

import time
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

import requests  # type: ignore

from directionalscalper.core.utils import send_public_request


log = logging.getLogger(__name__)

from time import sleep

class InvalidAPI(Exception):
    def __init__(self, message="Invalid Manager setup"):
        self.message = message
        super().__init__(self.message)

class Manager:
    def __init__(
        self,
        exchange,
        exchange_name: str = 'bybit',  # Defaulting to 'binance'
        data_source_exchange: str = 'binance',
        api: str = "remote",
        cache_life_seconds: int = 20,
        path: Path | None = None,
        url: str = "",
    ):
        self.exchange = exchange
        self.exchange_name = exchange_name  # New attribute to store the exchange name
        self.data_source_exchange = data_source_exchange
        log.info("Starting API Manager")
        self.api = api
        self.cache_life_seconds = cache_life_seconds
        self.path = path
        self.url = url
        self.last_checked = 0.0
        self.data = {}

        # Attributes for caching
        self.rotator_symbols_cache = None
        self.rotator_symbols_cache_expiry = datetime.now() - timedelta(seconds=1)  # Initialize to an old timestamp to force first fetch

        # Attributes for caching API data
        self.api_data_cache = None
        self.api_data_cache_expiry = datetime.now() - timedelta(seconds=1)

        self.asset_value_cache = {}
        self.asset_value_cache_expiry = {}

        if self.api == "remote":
            log.info("API manager mode: remote")
            if len(self.url) < 6:
                # Adjusting the default URL based on the exchange_name
                self.url = f"http://api.tradesimple.xyz/data/quantdatav2_{self.exchange_name}.json"
            log.info(f"Remote API URL: {self.url}")
            self.data = self.get_remote_data()

        elif self.api == "local":
            # You might also want to consider adjusting the local path based on the exchange_name in the future.
            if len(str(self.path)) < 6:
                self.path = Path("data", f"quantdatav2_{self.exchange_name}.json")
            log.info(f"Local API directory: {self.path}")
            self.data = self.get_local_data()

        else:
            log.error("API must be 'local' or 'remote'")
            raise InvalidAPI(message="API must be 'local' or 'remote'")

        self.update_last_checked()

    def update_last_checked(self):
        self.last_checked = datetime.now().timestamp()

    def fetch_data_from_url(self, url):
        try:
            header, raw_json = send_public_request(url=url)
            return raw_json
        except requests.exceptions.RequestException as e:
            log.error(f"Request failed: {e}")
            return {}
        except json.decoder.JSONDecodeError as e:
            log.error(f"Failed to parse JSON: {e}")
            return {}
        except Exception as e:
            log.error(f"Unexpected error occurred: {e}")
            return {}

    def get_data(self):
        if self.api == "remote":
            return self.get_remote_data()
        if self.api == "local":
            return self.get_local_data()

    def get_local_data(self):
        if not self.check_timestamp():
            return self.data
        if not self.path.is_file():
            raise InvalidAPI(message=f"{self.path} is not a file")
        f = open(self.path)
        try:
            self.data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"ERROR: Invalid JSON: {exc.msg}, line {exc.lineno}, column {exc.colno}"
            )
        self.update_last_checked()
        return self.data

    def is_cache_expired(self):
        """Checks if the cache has expired based on cache_life_seconds."""
        return datetime.now() > self.rotator_symbols_cache_expiry

    def get_auto_rotate_symbols(self, min_qty_threshold: float = None, whitelist: list = None, blacklist: list = None, max_usd_value: float = None, max_retries: int = 100):
        if self.rotator_symbols_cache and not self.is_cache_expired():
            return self.rotator_symbols_cache

        symbols = []
        url = f"http://api.tradesimple.xyz/data/rotatorsymbols_{self.data_source_exchange}.json"
        
        for retry in range(max_retries):
            delay = 2**retry  # exponential backoff
            delay = min(58, delay)  # cap the delay to 30 seconds

            try:
                log.debug(f"Sending request to {url} (Attempt: {retry + 1})")
                header, raw_json = send_public_request(url=url)
                
                if isinstance(raw_json, list):
                    log.debug(f"Received {len(raw_json)} assets from API")
                    
                    for asset in raw_json:
                        symbol = asset.get("Asset", "")
                        min_qty = asset.get("Min qty", 0)
                        usd_price = asset.get("Price", float('inf')) 
                        
                        log.debug(f"Processing symbol {symbol} with min_qty {min_qty} and USD price {usd_price}")

                        # Only consider the whitelist if it's not empty or None
                        if whitelist and symbol not in whitelist and len(whitelist) > 0:
                            log.debug(f"Skipping {symbol} as it's not in whitelist")
                            continue

                        # Consider the blacklist regardless of whether it's empty or not
                        if blacklist and symbol in blacklist:
                            log.debug(f"Skipping {symbol} as it's in blacklist")
                            continue

                        # Check against the max_usd_value, if provided
                        if max_usd_value is not None and usd_price > max_usd_value:
                            log.debug(f"Skipping {symbol} as its USD price {usd_price} is greater than the max allowed {max_usd_value}")
                            continue

                        if min_qty_threshold is None or min_qty <= min_qty_threshold:
                            symbols.append(symbol)

                    log.debug(f"Returning {len(symbols)} symbols")
                    
                    # If successfully fetched, update the cache and its expiry time
                    if symbols:
                        self.rotator_symbols_cache = symbols
                        self.rotator_symbols_cache_expiry = datetime.now() + timedelta(seconds=self.cache_life_seconds)

                    return symbols

                else:
                    log.error("Unexpected data format. Expected a list of assets.")
                    # No immediate retry here. The sleep at the end will handle the delay
                    
            except requests.exceptions.RequestException as e:
                log.error(f"Request failed: {e}")
            except json.decoder.JSONDecodeError as e:
                log.error(f"Failed to parse JSON: {e}. Response: {raw_json}")
            except Exception as e:
                log.error(f"Unexpected error occurred: {e}")

            # Wait before the next retry
            if retry < max_retries - 1:
                sleep(delay)
        
        # Return empty list if all retries fail
        return []
    
    def get_symbols(self):
        url = "http://api.tradesimple.xyz/data/rotatorsymbols.json"
        try:
            header, raw_json = send_public_request(url=url)
            if isinstance(raw_json, list):
                return raw_json
            else:
                log.error("Unexpected data format. Expected a list of symbols.")
                return []
        except requests.exceptions.RequestException as e:
            log.error(f"Request failed: {e}")
            return []
        except json.decoder.JSONDecodeError as e:
            log.error(f"Failed to parse JSON: {e}")
            return []
        except Exception as e:
            log.error(f"Unexpected error occurred: {e}")
            return []

    # def get_remote_data(self):
    #     if not self.check_timestamp():
    #         return self.data
    #     header, raw_json = send_public_request(url=self.url)
    #     self.data = raw_json
    #     self.update_last_checked()
    #     return self.data

    def get_remote_data(self):
            if not self.check_timestamp():
                return self.data
            while True:  # Keep trying until a successful request is made
                try:
                    header, raw_json = send_public_request(url=self.url)
                    self.data = raw_json
                    break  # if the request was successful, break the loop
                except requests.exceptions.RequestException as e:
                    log.error(f"Request failed: {e}, retrying...")
                except json.decoder.JSONDecodeError as e:
                    log.error(f"Failed to parse JSON: {e}, retrying...")
                except Exception as e:
                    log.error(f"Unexpected error occurred: {e}, retrying...")
                finally:
                    self.update_last_checked()
            return self.data

    def check_timestamp(self):
        return datetime.now().timestamp() - self.last_checked > self.cache_life_seconds

    def get_asset_data(self, symbol: str, data):
        try:
            for asset in data:
                if asset["Asset"] == symbol:
                    return asset
        except Exception as e:
            log.warning(f"{e}")
        return None

    def get_1m_moving_averages(self, symbol, num_bars=20):
        return self.exchange.get_moving_averages(symbol, "1m", num_bars)
    
    def get_5m_moving_averages(self, symbol, num_bars=20):
        return self.exchange.get_moving_averages(symbol, "5m", num_bars)

    def get_asset_value(self, symbol: str, data, value: str):
        current_time = datetime.now()
        
        # Check if value exists in cache and hasn't expired
        if symbol in self.asset_value_cache and value in self.asset_value_cache[symbol]:
            if current_time <= self.asset_value_cache_expiry.get(symbol, {}).get(value, current_time - timedelta(seconds=1)):
                return self.asset_value_cache[symbol][value]

        # If not in cache or expired, fetch value
        try:
            asset_data = self.get_asset_data(symbol, data)
            if asset_data is not None:
                result = None
                mapping = {
                    "Price": "Price",
                    "1mVol": "1m 1x Volume (USDT)",
                    "5mVol": "5m 1x Volume (USDT)",
                    "1hVol": "1m 1h Volume (USDT)",
                    "1mSpread": "1m Spread",
                    "5mSpread": "5m Spread",
                    "15mSpread": "15m Spread",
                    "30mSpread": "30m Spread",
                    "1hSpread": "1h Spread",
                    "4hSpread": "4h Spread",
                    "Trend": "Trend",
                    "Funding": "Funding",
                    "MFI": "MFI",
                    "ERI Bull Power": "ERI Bull Power",
                    "ERI Bear Power": "ERI Bear Power",
                    "ERI Trend": "ERI Trend",
                    "HMA Trend": "HMA Trend"
                    # add other mappings here if needed
                }
                if value in mapping and mapping[value] in asset_data:
                    result = asset_data[mapping[value]]

                # Update cache and expiry time
                if result:
                    if symbol not in self.asset_value_cache:
                        self.asset_value_cache[symbol] = {}
                    if symbol not in self.asset_value_cache_expiry:
                        self.asset_value_cache_expiry[symbol] = {}
                    self.asset_value_cache[symbol][value] = result
                    self.asset_value_cache_expiry[symbol][value] = current_time + timedelta(seconds=self.cache_life_seconds)

                return result

        except Exception as e:
            log.warning(f"{e}")
        
        return None

    def is_api_data_cache_expired(self):
        return datetime.now() > self.api_data_cache_expiry

    def get_api_data(self, symbol):
        if self.api_data_cache and not self.is_api_data_cache_expired():
            return self.api_data_cache

        api_data_url = f"http://api.tradesimple.xyz/data/quantdatav2_{self.data_source_exchange}.json"
        data = self.fetch_data_from_url(api_data_url)

        api_data = {
            '1mVol': self.get_asset_value(symbol, data, "1mVol"),
            '5mVol': self.get_asset_value(symbol, data, "5mVol"),
            '1hVol': self.get_asset_value(symbol, data, "1hVol"),
            '1mSpread': self.get_asset_value(symbol, data, "1mSpread"),
            '5mSpread': self.get_asset_value(symbol, data, "5mSpread"),
            '30mSpread': self.get_asset_value(symbol, data, "30mSpread"),
            '1hSpread': self.get_asset_value(symbol, data, "1hSpread"),
            '4hSpread': self.get_asset_value(symbol, data, "4hSpread"),
            'Trend': self.get_asset_value(symbol, data, "Trend"),
            'HMA Trend': self.get_asset_value(symbol, data, "HMA Trend"),
            'MFI': self.get_asset_value(symbol, data, "MFI"),
            'ERI Trend': self.get_asset_value(symbol, data, "ERI Trend"),
            'Funding': self.get_asset_value(symbol, data, "Funding"),
            'Symbols': self.get_symbols()
        }

        # Update the cache and its expiry time
        self.api_data_cache = api_data
        self.api_data_cache_expiry = datetime.now() + timedelta(seconds=self.cache_life_seconds)

        return api_data