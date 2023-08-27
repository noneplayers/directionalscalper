import sys
import time
import traceback
import threading
from pathlib import Path

project_dir = str(Path(__file__).resolve().parent)
print("Project directory:", project_dir)
sys.path.insert(0, project_dir)

import inquirer
from rich.live import Live
import argparse
from pathlib import Path
import config
from config import load_config, Config
import ccxt
from api.manager import Manager
from directionalscalper.core.exchange import Exchange
from directionalscalper.core.strategies.strategy import Strategy
# Bybit rotator
from directionalscalper.core.strategies.bybit.multi.bybit_auto_rotator import BybitAutoRotator
from directionalscalper.core.strategies.bybit.multi.bybit_auto_rotator_mfirsi import BybitAutoRotatorMFIRSI
from directionalscalper.core.strategies.bybit.multi.bybit_auto_hedge_maker_mfirsi_rotator import BybitAutoHedgeStrategyMakerMFIRSIRotator
from directionalscalper.core.strategies.bybit.multi.bybit_auto_maker_mfirsi_rotator_aggressive import BybitRotatorAggressive
from directionalscalper.core.strategies.bybit.multi.bybit_mfirsi_trend_rotator import BybitMFIRSITrendRotator
from directionalscalper.core.strategies.bybit.multi.bybit_spoof_rotator import BybitSpoofRotator
### ILAY ###
from live_table_manager import LiveTableManager, shared_symbols_data
### ILAY ###

# def standardize_symbol(symbol):
#     return symbol.replace('/', '').split(':')[0]

def standardize_symbol(symbol):
    return symbol.replace('/', '').split(':')[0]

def choose_strategy():
    questions = [
        inquirer.List('strategy',
                      message='Which strategy would you like to run?',
                      choices=[
                          'bybit_hedge_rotator',
                          'bybit_hedge_rotator_mfirsi',
                          'bybit_auto_hedge_mfi_rotator',
                          'bybit_mfirsi_trend_rotator',
                          'bybit_rotator_aggressive',
                          'bybit_rotator_spoof',
                      ]
                     )
    ]
    answers = inquirer.prompt(questions)
    return answers['strategy']

class DirectionalMarketMaker:
    def __init__(self, config: Config, exchange_name: str):
        self.config = config
        self.exchange_name = exchange_name
        exchange_config = None

        for exch in config.exchanges:
            if exch.name == exchange_name:
                exchange_config = exch
                break

        if not exchange_config:
            raise ValueError(f"Exchange {exchange_name} not found in the configuration file.")

        api_key = exchange_config.api_key
        secret_key = exchange_config.api_secret
        passphrase = exchange_config.passphrase
        self.exchange = Exchange(self.exchange_name, api_key, secret_key, passphrase)

    # def run_strategy(self, symbol, strategy_name, config):
    def run_strategy(self, symbol, strategy_name, config, symbols_to_trade=None):
        # ... (rest of your code)
        if symbols_to_trade:
            print(f"Calling run method with symbols: {symbols_to_trade}")
        if strategy_name.lower() == 'bybit_hedge_rotator':
            strategy = BybitAutoRotator(self.exchange, self.manager, config.bot)
            strategy.run(symbol)
        elif strategy_name.lower() == 'bybit_hedge_rotator_mfirsi':
            strategy = BybitAutoRotatorMFIRSI(self.exchange, self.manager, config.bot)
            strategy.run(symbol)
        elif strategy_name.lower() == 'bybit_auto_hedge_mfi_rotator':
            strategy = BybitAutoHedgeStrategyMakerMFIRSIRotator(self.exchange, self.manager, config.bot)
            strategy.run(symbol)
        elif strategy_name.lower() == 'bybit_mfirsi_trend_rotator':
            strategy = BybitMFIRSITrendRotator(self.exchange, self.manager, config.bot)
            strategy.run(symbol)
        elif strategy_name.lower() == 'bybit_rotator_aggressive':
            strategy = BybitRotatorAggressive(self.exchange, self.manager, config.bot)
            strategy.run(symbol)
        elif strategy_name.lower() == 'bybit_rotator_spoof':
            strategy = BybitSpoofRotator(self.exchange, self.manager, config.bot)
            strategy.run(symbol)

    def get_balance(self, quote, market_type=None, sub_type=None):
        if self.exchange_name == 'bitget':
            return self.exchange.get_balance_bitget(quote)
        elif self.exchange_name == 'bybit':
            return self.exchange.get_balance_bybit(quote)
        elif self.exchange_name == 'mexc':
            return self.exchange.get_balance_mexc(quote, market_type='swap')
        elif self.exchange_name == 'huobi':
            print("Huobi starting..")
        elif self.exchange_name == 'okx':
            print(f"Unsupported for now")
        elif self.exchange_name == 'binance':
            return self.exchange.get_balance_binance(quote)
        elif self.exchange_name == 'phemex':
            print(f"Unsupported for now")

    def create_order(self, symbol, order_type, side, amount, price=None):
        return self.exchange.create_order(symbol, order_type, side, amount, price)

    def get_symbols(self):
        return self.exchange.symbols

# def run_bot(symbol, args, manager):
def run_bot(symbol, args, manager, rotator_symbols=None):
    config_file_path = Path('configs/' + args.config)
    print("Loading config from:", config_file_path)
    config = load_config(config_file_path)

    exchange_name = args.exchange  # These are now guaranteed to be non-None
    strategy_name = args.strategy

    print(f"Symbol: {symbol}")
    print(f"Exchange name: {exchange_name}")
    print(f"Strategy name: {strategy_name}")

    market_maker = DirectionalMarketMaker(config, exchange_name)
    market_maker.manager = manager  # Use the passed-in manager instance

    quote = "USDT"
    if exchange_name.lower() == 'huobi':
        print(f"Loading huobi strategy..")
    elif exchange_name.lower() == 'mexc':
        balance = market_maker.get_balance(quote, type='swap')
        print(f"Futures balance: {balance}")
    else:
        balance = market_maker.get_balance(quote)
        print(f"Futures balance: {balance}")

    market_maker.run_strategy(symbol, strategy_name, config, rotator_symbols)


def start_threads_for_symbols(symbols, args, manager):
    threads = [threading.Thread(target=run_bot, args=(symbol, args, manager, symbols)) for symbol in symbols]
    for thread in threads:
        thread.start()
    return threads

if __name__ == '__main__':
    # ASCII Art and Text
    sword = "====||====>"

    print("\n" + "=" * 50)
    print("DirectionalScalper".center(50))
    print("=" * 50 + "\n")

    print("Initializing", end="")
    # Loading animation
    for i in range(3):
        time.sleep(0.5)
        print(".", end="", flush=True)
    print("\n")

    # Display the ASCII art
    print("Battle-Ready Algorithm".center(50))
    print(sword.center(50) + "\n")

    # argparse code and other initializations
    parser = argparse.ArgumentParser(description='DirectionalScalper')
    parser.add_argument('--config', type=str, default='configs/config.json', help='Path to the configuration file')
    parser.add_argument('--exchange', type=str, help='The name of the exchange to use')
    parser.add_argument('--strategy', type=str, help='The name of the strategy to use')
    parser.add_argument('--symbol', type=str, help='The trading symbol to use')
    parser.add_argument('--amount', type=str, help='The size to use')
    args = parser.parse_args()

    # Ask for exchange and strategy if they're not provided
    if not args.exchange and not args.strategy:
        questions = [
            inquirer.List('exchange',
                        message="Which exchange do you want to use?",
                        choices=['bybit', 'bitget', 'mexc', 'huobi', 'okx', 'binance', 'phemex']),
            inquirer.List('strategy',
                        message="Which strategy do you want to use?",
                        choices=['bybit_hedge_rotator', 'bybit_hedge_rotator_mfirsi', 'bybit_auto_hedge_mfi_rotator',
                                'bybit_mfirsi_trend_rotator', 'bybit_rotator_aggressive', 'bybit_rotator_spoof']),
        ]
        answers = inquirer.prompt(questions)
        args.exchange = answers['exchange']
        args.strategy = answers['strategy']

    print("DirectionalScalper Initialized Successfully!".center(50))
    print("=" * 50 + "\n")
    # parser = argparse.ArgumentParser(description='DirectionalScalper')
    # parser.add_argument('--config', type=str, default='configs/config.json', help='Path to the configuration file')
    # parser.add_argument('--exchange', type=str, help='The name of the exchange to use')
    # parser.add_argument('--strategy', type=str, help='The name of the strategy to use')
    # parser.add_argument('--symbol', type=str, help='The trading symbol to use')
    # parser.add_argument('--amount', type=str, help='The size to use')
    # args = parser.parse_args()

    # # Ask for exchange and strategy if they're not provided
    # if not args.exchange and not args.strategy:
    #     questions = [
    #         inquirer.List('exchange',
    #                       message="Which exchange do you want to use?",
    #                       choices=['bybit', 'bitget', 'mexc', 'huobi', 'okx', 'binance', 'phemex']),
    #         inquirer.List('strategy',
    #                       message="Which strategy do you want to use?",
    #                       choices=['bybit_hedge_rotator', 'bybit_hedge_rotator_mfirsi', 'bybit_auto_hedge_mfi_rotator',
    #                                'bybit_mfirsi_trend_rotator', 'bybit_rotator_aggressive', 'bybit_rotator_spoof']),
    #     ]
    #     answers = inquirer.prompt(questions)
    #     args.exchange = answers['exchange']
    #     args.strategy = answers['strategy']

    config_file_path = Path('configs/' + args.config)
    config = load_config(config_file_path)

    exchange_name = args.exchange  # Now it will have a value
    market_maker = DirectionalMarketMaker(config, exchange_name)
    manager = Manager(market_maker.exchange, api=config.api.mode, path=Path("data", config.api.filename), url=f"{config.api.url}{config.api.filename}")
    
    whitelist = config.bot.whitelist
    blacklist = config.bot.blacklist
    symbols_allowed = config.bot.symbols_allowed
  
    ### ILAY ###
    table_manager = LiveTableManager()
    display_thread = threading.Thread(target=table_manager.display_table)
    display_thread.daemon = True
    display_thread.start()
    ### ILAY ###

    #Check if the specific strategy is chosen, and if so, adjust symbols_allowed
    # if args.strategy.lower() == 'bybit_rotator_aggressive':
    #     symbols_allowed = 5

    # Fetch all symbols that meet your criteria and standardize them
    all_symbols_standardized = [standardize_symbol(symbol) for symbol in manager.get_auto_rotate_symbols(min_qty_threshold=None, whitelist=whitelist, blacklist=blacklist)]

    # Get symbols with open positions and standardize them
    open_position_data = market_maker.exchange.get_all_open_positions_bybit()
    open_positions_symbols = [standardize_symbol(position['symbol']) for position in open_position_data]
    
    print(f"Open positions symbols {open_positions_symbols}")

    # Determine new symbols to trade on
    potential_new_symbols = [symbol for symbol in all_symbols_standardized if symbol not in open_positions_symbols]
    new_symbols = potential_new_symbols[:symbols_allowed]

    # Combine open positions symbols and new symbols
    symbols_to_trade = open_positions_symbols + new_symbols

    print(f"Symbols to trade: {symbols_to_trade}")

    print(f"Symbols to trade: {symbols_to_trade}")

    # Fetch the rotator symbols once before starting the threads and standardize them as well
    rotator_symbols_standardized = [standardize_symbol(symbol) for symbol in manager.get_auto_rotate_symbols(min_qty_threshold=None, whitelist=whitelist, blacklist=blacklist)]

    # Start threads for initial set of symbols
    active_threads = start_threads_for_symbols(symbols_to_trade, args, manager)

    # New section for continuous checking of rotator symbols
    while True:
        # Remove finished threads from active_threads list
        active_threads = [t for t in active_threads if t.is_alive()]

        # Refresh the list of rotator symbols
        rotator_symbols_standardized = [standardize_symbol(symbol) for symbol in manager.get_auto_rotate_symbols(min_qty_threshold=None, whitelist=whitelist, blacklist=blacklist)]

        # Find new symbols that are not yet being traded
        new_symbols = [s for s in rotator_symbols_standardized if s not in [t._args[0] for t in active_threads]]

        # Start new threads for new symbols
        new_threads = start_threads_for_symbols(new_symbols, args, manager)
        active_threads.extend(new_threads)

        # Sleep for a while before the next iteration
        time.sleep(60)