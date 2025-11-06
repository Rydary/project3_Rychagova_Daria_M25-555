import requests
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple

from .config import api_config, parser_config
from ..core.exceptions import ApiRequestError

logger = logging.getLogger(__name__)

class BaseAPIClient(ABC):
    """Базовый класс для API клиентов"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ValutaTradeHub/1.0',
            'Accept': 'application/json'
        })
    
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Tuple[bool, Dict, Optional[str]]:
        """Выполняет HTTP запрос с обработкой ошибок"""
        for attempt in range(parser_config.MAX_RETRIES):
            try:
                start_time = time.time()
                response = self.session.get(
                    url, 
                    params=params, 
                    timeout=parser_config.REQUEST_TIMEOUT
                )
                request_time = int((time.time() - start_time) * 1000)
                
                if response.status_code == 200:
                    return True, response.json(), f"Request took {request_time}ms"
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.warning(f"Attempt {attempt + 1} failed: {error_msg}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Attempt {attempt + 1}: Request timeout")
                error_msg = "Request timeout"
            except requests.exceptions.ConnectionError:
                logger.warning(f"Attempt {attempt + 1}: Connection error")
                error_msg = "Connection error"
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1}: Request exception: {str(e)}")
                error_msg = f"Request exception: {str(e)}"
            except Exception as e:
                logger.error(f"Attempt {attempt + 1}: Unexpected error: {str(e)}")
                error_msg = f"Unexpected error: {str(e)}"
            
            if attempt < parser_config.MAX_RETRIES - 1:
                time.sleep(2 ** attempt) 
        raise ApiRequestError(f"Failed after {parser_config.MAX_RETRIES} attempts: {error_msg}")

    @abstractmethod
    def fetch_rates(self) -> Dict[str, float]:
        """Абстрактный метод для получения курсов в формате {currency_pair: rate}"""
        pass


class ExchangeRateAPIClient(BaseAPIClient):
    """Клиент для ExchangeRate-API"""
    
    def fetch_rates(self) -> Dict[str, float]:
        """Получает курсы фиатных валют в формате {EUR_USD: 1.0786}"""
        logger.info("Fetching rates from ExchangeRate-API...")
        
        url = f"{api_config.EXCHANGERATE_API_URL}/{api_config.EXCHANGERATE_API_KEY}/latest/{api_config.BASE_CURRENCY}"
        
        try:
            success, data, meta_info = self._make_request(url)
            rates = {}
            if 'conversion_rates' in data:
                for currency, rate in data['conversion_rates'].items():
                    if currency in api_config.FIAT_CURRENCIES and currency != api_config.BASE_CURRENCY:
                        pair_key = f"{currency}_{api_config.BASE_CURRENCY}"
                        rates[pair_key] = float(rate)
            
            logger.info(f"ExchangeRate-API: Retrieved {len(rates)} fiat rates")
            return rates
            
        except ApiRequestError:
            raise
        except (KeyError, ValueError, TypeError) as e:
            error_msg = f"Invalid ExchangeRate-API response format: {str(e)}"
            logger.error(error_msg)
            raise ApiRequestError(error_msg)
    def get_fiat_rates(self, base_currency: str = "USD") -> Tuple[bool, Dict, Optional[str]]:
        """Совместимость со старым кодом"""
        try:
            rates = self.fetch_rates()
            simple_rates = {}
            for pair, rate in rates.items():
                currency = pair.split('_')[0]
                simple_rates[currency] = rate
            return True, simple_rates, None
        except ApiRequestError as e:
            return False, {}, str(e)


class CoinGeckoAPIClient(BaseAPIClient):
    """Клиент для CoinGecko API"""
    
    def fetch_rates(self) -> Dict[str, float]:
        """Получает курсы криптовалют в формате {BTC_USD: 59337.21}"""
        logger.info("Fetching rates from CoinGecko...")
        
        crypto_ids = list(api_config.CRYPTO_CURRENCIES.values())
        crypto_ids_param = ",".join(crypto_ids)
        
        params = {
            'ids': crypto_ids_param,
            'vs_currencies': 'usd'
        }
        
        try:
            success, data, meta_info = self._make_request(api_config.COINGECKO_URL, params)
            rates = {}
            for crypto_code, crypto_id in api_config.CRYPTO_CURRENCIES.items():
                if crypto_id in data and 'usd' in data[crypto_id]:
                    pair_key = f"{crypto_code}_{api_config.BASE_CURRENCY}"
                    rates[pair_key] = float(data[crypto_id]['usd'])
            
            logger.info(f"CoinGecko: Retrieved {len(rates)} crypto rates")
            return rates
            
        except ApiRequestError:
            raise
        except (KeyError, ValueError, TypeError) as e:
            error_msg = f"Invalid CoinGecko response format: {str(e)}"
            logger.error(error_msg)
            raise ApiRequestError(error_msg)

    def get_crypto_rates(self, vs_currency: str = "usd") -> Tuple[bool, Dict, Optional[str]]:
        try:
            rates = self.fetch_rates()
            simple_rates = {}
            for pair, rate in rates.items():
                currency = pair.split('_')[0]
                simple_rates[currency] = rate
            return True, simple_rates, None
        except ApiRequestError as e:
            return False, {}, str(e)