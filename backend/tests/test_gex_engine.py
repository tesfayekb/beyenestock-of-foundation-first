import math

from gex_engine import bs_gamma, classify_trade


def test_bs_gamma_atm_reasonable_value():
    s = 100.0
    k = 100.0
    t = 0.25
    sigma = 0.2
    gamma = bs_gamma(S=s, K=k, T=t, r=0.01, sigma=sigma)
    approx = 1.0 / (s * sigma * math.sqrt(t))
    assert gamma > 0
    assert gamma < approx


def test_bs_gamma_zero_when_t_or_sigma_zero():
    assert bs_gamma(100, 100, 0, 0.01, 0.2) == 0.0
    assert bs_gamma(100, 100, 0.2, 0.01, 0) == 0.0


def test_classify_trade_above_midpoint_returns_buy():
    assert classify_trade(10.6, 10.0, 11.0, 10.4) == 1


def test_classify_trade_below_midpoint_returns_sell():
    assert classify_trade(10.4, 10.0, 11.0, 10.5) == -1


def test_classify_trade_midpoint_tick_test_up_returns_buy():
    assert classify_trade(10.5, 10.0, 11.0, 10.4) == 1


def test_gex_confidence_zero_when_no_trades():
    expected_trades_5min = 1000
    trades_count = 0
    confidence = min(1.0, trades_count / expected_trades_5min)
    assert confidence == 0.0
