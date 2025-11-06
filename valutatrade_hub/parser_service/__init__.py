"""
Parser Service для сбора и обновления курсов валют
"""

from .updater import RatesUpdater
from .scheduler import RatesScheduler
from .storage import RatesStorage

__all__ = ['RatesUpdater', 'RatesScheduler', 'RatesStorage']