"""Shared synthetic fixtures. Fully hand-built with round numbers so every
expected value in the tests is computable by hand. No network, no yfinance."""

import copy
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest


def make_bundle(**over):
    """A clean, stable, wide-moat-free synthetic company:
    price 100, shares 100, fx 1, FCF flat 10/yr for 5 yrs."""
    b = {
        'symbol': 'TEST', 'name': 'Test Co', 'sector': 'Industrials',
        'industry': 'Specialty Industrial Machinery', 'price': 100.0,
        'price_ccy': 'USD', 'fin_ccy': 'USD', 'fx': 1.0, 'shares': 100.0,
        'eps_ps': 6.0, 'bvps_ps': 50.0, 'pb': 2.0, 'div_yield': 0.02,
        'mkt_cap': 10_000.0,
        'ebit': 12.0, 'interest': 1.5, 'revenue': 90.0, 'ebitda': 16.0,
        'tax': 2.0,
        'total_assets': 300.0, 'total_equity': 150.0, 'total_debt': 60.0,
        'cash': 10.0, 'current_assets': 80.0, 'current_liab': 50.0,
        'retained_earnings': 60.0, 'long_term_debt': 55.0,
        'fcf_hist': [10.0, 10.0, 10.0, 10.0, 10.0],
        'ni_hist': [8.0, 8.0, 8.0, 8.0],
        'ocf_hist': [12.0, 12.0, 12.0, 12.0],
        'capex_hist': [4.0, 4.0, 4.0, 4.0],
        'da_hist': [4.0, 4.0, 4.0, 4.0],
        'lease_principal_hist': [],
        'shares_hist': [100.0, 100.5, 101.0, 101.5],
        'total_assets_hist': [300.0, 295.0, 290.0, 285.0],
        'long_term_debt_hist': [55.0, 60.0, 65.0, 70.0],
        'current_assets_hist': [80.0, 78.0, 76.0, 74.0],
        'current_liab_hist': [50.0, 52.0, 54.0, 56.0],
        'revenue_hist': [90.0, 88.0, 86.0, 84.0],
        'cogs_hist': [50.0, 50.0, 49.0, 48.0],
        'fetched_at': '2026-09-01T00:00:00+00:00', 'source': 'snapshot',
        'approximate': False,
    }
    b.update(over)
    return b


def make_inputs(**over):
    i = {'moat': 'narrow', 'cyclical': False, 'thesis': 'Test thesis. [Signed 1 Sep 2026]'}
    i.update(over)
    return i


@pytest.fixture
def bundle():
    return make_bundle()


@pytest.fixture
def inputs():
    return make_inputs()
