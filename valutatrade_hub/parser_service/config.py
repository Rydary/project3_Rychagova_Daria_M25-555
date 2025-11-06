from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class APIConfig:
    """Конфигурация API endpoints и ключей"""
    EXCHANGERATE_API_KEY: str = "4124d29c8dd4bed32b468042"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"
    
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    
    BASE_CURRENCY: str = "USD"
    
    FIAT_CURRENCIES: List[str] = field(default_factory=lambda: ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "CNY"])
    
    CRYPTO_CURRENCIES: Dict[str, str] = field(default_factory=lambda: {
        "BTC": "bitcoin",
        "ETH": "ethereum", 
        "SOL": "solana",
        "ADA": "cardano",
        "DOT": "polkadot",
        "DOGE": "dogecoin"
    })

@dataclass
class ParserConfig:
    """Конфигурация парсера"""
    UPDATE_INTERVAL_MINUTES: int = 30 
    REQUEST_TIMEOUT: int = 10
    MAX_RETRIES: int = 3 
    CACHE_TTL_MINUTES: int = 30
    RATES_CACHE_PATH: str = "data/rates.json" 
    EXCHANGE_RATES_PATH: str = "data/exchange_rates.json" 
    TEMP_RATES_PATH: str = "data/rates_temp.json" 

api_config = APIConfig()
parser_config = ParserConfig()