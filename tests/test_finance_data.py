from types import SimpleNamespace

from shared.finance_data import fetch_ticker_metadata


def test_fetch_ticker_metadata_does_not_use_previous_close_as_current_price(monkeypatch) -> None:
    class FakeTicker:
        fast_info = {"regular_market_previous_close": 99.0}

        def __init__(self, symbol: str) -> None:
            self.symbol = symbol

        def get_info(self) -> dict[str, object]:
            return {"shortName": "Example Inc", "previousClose": 100.0}

    monkeypatch.setattr("shared.finance_data.yf", SimpleNamespace(Ticker=FakeTicker))

    metadata = fetch_ticker_metadata(" exm ")

    assert metadata["ticker"] == "EXM"
    assert metadata["company_name"] == "Example Inc"
    assert metadata["current_price"] is None
