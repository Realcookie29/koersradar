from koersradar.config import load_costs, load_instruments


def test_repo_config_loads():
    instruments = load_instruments()
    symbols = {i.symbol for i in instruments}
    assert "BTC/USDT" in symbols and "ASML.AS" in symbols
    assert all(i.experimental for i in instruments if i.market == "aex")
    costs = load_costs()
    assert {i.source for i in instruments} <= set(costs)
