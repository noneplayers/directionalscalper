import logging

import ccxt

log = logging.getLogger(__name__)


class Exchange:
    def __init__(self, exchange_name, config):
        self.exchange_name = exchange_name
        self.config = config
        self.status = "unintiialised"
        self.exchange = None
        self.initialise()

    def initialise(self):
        if self.exchange_name == "bybit":
            self.exchange = ccxt.bybit(
                {
                    "enableRateLimit": True,
                    "apiKey": self.config.exchange.api_key,
                    "secret": self.config.exchange.api_secret,
                }
            )
            self.status = "initialised"

    def get_balance(self, quote: str) -> dict:
        values = {
            "available_balance": 0.0,
            "pnl": 0.0,
            "upnl": 0.0,
            "wallet_balance": 0.0,
            "equity": 0.0,
        }
        try:
            data = self.exchange.fetch_balance()
            if "info" in data:
                if "result" in data["info"]:
                    if quote in data["info"]["result"]:
                        values["available_balance"] = float(
                            data["info"]["result"][quote]["available_balance"]
                        )
                        values["pnl"] = float(
                            data["info"]["result"][quote]["realised_pnl"]
                        )
                        values["upnl"] = float(
                            data["info"]["result"][quote]["unrealised_pnl"]
                        )
                        values["wallet_balance"] = round(
                            float(data["info"]["result"][quote]["wallet_balance"]), 2
                        )
                        values["equity"] = round(
                            float(data["info"]["result"][quote]["equity"]), 2
                        )
        except Exception as e:
            print(f"An unknown error occured in get_balance(): {e}")
            log.warning(f"{e}")
        return values

    def get_orderbook(self, symbol) -> dict:
        values = {"bids": 0, "asks": 0}
        try:
            data = self.exchange.fetch_order_book(symbol)
            if "bids" in data and "asks" in data:
                if len(data["bids"]) > 0 and len(data["asks"]) > 0:
                    if len(data["bids"][0]) > 0 and len(data["asks"][0]) > 0:
                        values["bids"] = int(data["bids"][0][0])
                        values["asks"] = int(data["asks"][0][0])
        except Exception as e:
            print(f"An unknown error occured in get_orderbook(): {e}")
            log.warning(f"{e}")
        return values

    def get_positions(self, symbol):
        values = {
            "long": {
                "qty": 0,
                "price": 0,
                "realised": 0,
                "cum_realised": 0,
                "upnl": 0,
                "upnl_pct": 0,
                "liq_price": 0,
                "entry_price": 0,
            },
            "short": {
                "qty": 0,
                "price": 0,
                "realised": 0,
                "cum_realised": 0,
                "upnl": 0,
                "upnl_pct": 0,
                "liq_price": 0,
                "entry_price": 0,
            },
        }
        try:
            data = self.exchange.fetch_positions([symbol])
            if len(data) == 2:
                sides = ["long", "short"]
                for side in [0, 1]:
                    values[sides[side]]["qty"] = float(data[side]["contracts"])
                    values[sides[side]]["price"] = float(data[side]["entryPrice"])
                    values[sides[side]]["realised"] = round(
                        float(data[side]["info"]["realised_pnl"]), 4
                    )
                    values[sides[side]]["cum_realised"] = round(
                        float(data[side]["info"]["cum_realised_pnl"]), 4
                    )
                    values[sides[side]]["upnl"] = round(
                        float(data[side]["info"]["unrealised_pnl"]), 4
                    )
                    values[sides[side]]["upnl_pct"] = round(
                        float(data[side]["precentage"]), 4
                    )
                    values[sides[side]]["liq_price"] = float(
                        data[side]["liquidationPrice"]
                    )
                    values[sides[side]]["entry_price"] = float(data[side]["entryPrice"])
        except Exception as e:
            print(f"An unknown error occured in get_orderbook(): {e}")
            log.warning(f"{e}")
        return values
