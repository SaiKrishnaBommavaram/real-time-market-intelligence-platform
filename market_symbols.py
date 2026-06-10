from collections.abc import Iterable


SYMBOL_CATALOG = {
    "AAPL": {
        "company_name": "Apple Inc.",
        "sector": "Technology",
        "benchmark_ticker": "XLK",
        "benchmark_name": "Technology Select Sector SPDR Fund",
        "benchmark_kind": "sector_etf",
        "aliases": ["Apple", "Apple Inc", "iPhone maker"],
        "is_benchmark": False,
    },
    "MSFT": {
        "company_name": "Microsoft Corporation",
        "sector": "Technology",
        "benchmark_ticker": "XLK",
        "benchmark_name": "Technology Select Sector SPDR Fund",
        "benchmark_kind": "sector_etf",
        "aliases": ["Microsoft", "Microsoft Corp", "Azure"],
        "is_benchmark": False,
    },
    "NVDA": {
        "company_name": "NVIDIA Corporation",
        "sector": "Technology",
        "benchmark_ticker": "XLK",
        "benchmark_name": "Technology Select Sector SPDR Fund",
        "benchmark_kind": "sector_etf",
        "aliases": ["NVIDIA", "Nvidia", "NVidia", "GeForce"],
        "is_benchmark": False,
    },
    "AMD": {
        "company_name": "Advanced Micro Devices, Inc.",
        "sector": "Technology",
        "benchmark_ticker": "XLK",
        "benchmark_name": "Technology Select Sector SPDR Fund",
        "benchmark_kind": "sector_etf",
        "aliases": ["AMD", "Advanced Micro Devices", "Ryzen"],
        "is_benchmark": False,
    },
    "INTC": {
        "company_name": "Intel Corporation",
        "sector": "Technology",
        "benchmark_ticker": "XLK",
        "benchmark_name": "Technology Select Sector SPDR Fund",
        "benchmark_kind": "sector_etf",
        "aliases": ["Intel", "Intel Corp"],
        "is_benchmark": False,
    },
    "GOOGL": {
        "company_name": "Alphabet Inc.",
        "sector": "Communication Services",
        "benchmark_ticker": "XLC",
        "benchmark_name": "Communication Services Select Sector SPDR Fund",
        "benchmark_kind": "sector_etf",
        "aliases": ["Alphabet", "Google", "Alphabet Inc"],
        "is_benchmark": False,
    },
    "META": {
        "company_name": "Meta Platforms, Inc.",
        "sector": "Communication Services",
        "benchmark_ticker": "XLC",
        "benchmark_name": "Communication Services Select Sector SPDR Fund",
        "benchmark_kind": "sector_etf",
        "aliases": ["Meta", "Facebook", "Instagram"],
        "is_benchmark": False,
    },
    "NFLX": {
        "company_name": "Netflix, Inc.",
        "sector": "Communication Services",
        "benchmark_ticker": "XLC",
        "benchmark_name": "Communication Services Select Sector SPDR Fund",
        "benchmark_kind": "sector_etf",
        "aliases": ["Netflix", "Netflix Inc"],
        "is_benchmark": False,
    },
    "AMZN": {
        "company_name": "Amazon.com, Inc.",
        "sector": "Consumer Discretionary",
        "benchmark_ticker": "XLY",
        "benchmark_name": "Consumer Discretionary Select Sector SPDR Fund",
        "benchmark_kind": "sector_etf",
        "aliases": ["Amazon", "Amazon.com", "AWS"],
        "is_benchmark": False,
    },
    "TSLA": {
        "company_name": "Tesla, Inc.",
        "sector": "Consumer Discretionary",
        "benchmark_ticker": "XLY",
        "benchmark_name": "Consumer Discretionary Select Sector SPDR Fund",
        "benchmark_kind": "sector_etf",
        "aliases": ["Tesla", "Tesla Inc", "Elon Musk EV maker"],
        "is_benchmark": False,
    },
    "JPM": {
        "company_name": "JPMorgan Chase & Co.",
        "sector": "Financials",
        "benchmark_ticker": "XLF",
        "benchmark_name": "Financial Select Sector SPDR Fund",
        "benchmark_kind": "sector_etf",
        "aliases": ["JPMorgan", "JP Morgan", "JPMorgan Chase"],
        "is_benchmark": False,
    },
    "BAC": {
        "company_name": "Bank of America Corporation",
        "sector": "Financials",
        "benchmark_ticker": "XLF",
        "benchmark_name": "Financial Select Sector SPDR Fund",
        "benchmark_kind": "sector_etf",
        "aliases": ["Bank of America", "BofA", "BAC"],
        "is_benchmark": False,
    },
    "XOM": {
        "company_name": "Exxon Mobil Corporation",
        "sector": "Energy",
        "benchmark_ticker": "XLE",
        "benchmark_name": "Energy Select Sector SPDR Fund",
        "benchmark_kind": "sector_etf",
        "aliases": ["Exxon", "Exxon Mobil"],
        "is_benchmark": False,
    },
    "CVX": {
        "company_name": "Chevron Corporation",
        "sector": "Energy",
        "benchmark_ticker": "XLE",
        "benchmark_name": "Energy Select Sector SPDR Fund",
        "benchmark_kind": "sector_etf",
        "aliases": ["Chevron", "Chevron Corp"],
        "is_benchmark": False,
    },
    "SPY": {
        "company_name": "SPDR S&P 500 ETF Trust",
        "sector": "Benchmark",
        "benchmark_ticker": None,
        "benchmark_name": None,
        "benchmark_kind": "broad_market",
        "aliases": ["SPY", "S&P 500", "SPDR S&P 500 ETF Trust"],
        "is_benchmark": True,
    },
    "XLK": {
        "company_name": "Technology Select Sector SPDR Fund",
        "sector": "Technology",
        "benchmark_ticker": "SPY",
        "benchmark_name": "SPDR S&P 500 ETF Trust",
        "benchmark_kind": "broad_market",
        "aliases": ["XLK", "Technology Select Sector SPDR Fund"],
        "is_benchmark": True,
    },
    "XLC": {
        "company_name": "Communication Services Select Sector SPDR Fund",
        "sector": "Communication Services",
        "benchmark_ticker": "SPY",
        "benchmark_name": "SPDR S&P 500 ETF Trust",
        "benchmark_kind": "broad_market",
        "aliases": ["XLC", "Communication Services Select Sector SPDR Fund"],
        "is_benchmark": True,
    },
    "XLY": {
        "company_name": "Consumer Discretionary Select Sector SPDR Fund",
        "sector": "Consumer Discretionary",
        "benchmark_ticker": "SPY",
        "benchmark_name": "SPDR S&P 500 ETF Trust",
        "benchmark_kind": "broad_market",
        "aliases": ["XLY", "Consumer Discretionary Select Sector SPDR Fund"],
        "is_benchmark": True,
    },
    "XLF": {
        "company_name": "Financial Select Sector SPDR Fund",
        "sector": "Financials",
        "benchmark_ticker": "SPY",
        "benchmark_name": "SPDR S&P 500 ETF Trust",
        "benchmark_kind": "broad_market",
        "aliases": ["XLF", "Financial Select Sector SPDR Fund"],
        "is_benchmark": True,
    },
    "XLE": {
        "company_name": "Energy Select Sector SPDR Fund",
        "sector": "Energy",
        "benchmark_ticker": "SPY",
        "benchmark_name": "SPDR S&P 500 ETF Trust",
        "benchmark_kind": "broad_market",
        "aliases": ["XLE", "Energy Select Sector SPDR Fund"],
        "is_benchmark": True,
    },
}


ALIAS_TO_TICKER = {}
for canonical_ticker, profile in SYMBOL_CATALOG.items():
    ALIAS_TO_TICKER[canonical_ticker] = canonical_ticker
    for alias in profile.get("aliases", []):
        ALIAS_TO_TICKER[alias.strip().upper()] = canonical_ticker


def normalize_ticker(symbol: str) -> str:
    normalized = str(symbol or "").strip().upper()
    if not normalized:
        return normalized
    return ALIAS_TO_TICKER.get(normalized, normalized)


def get_symbol_profile(symbol: str) -> dict:
    canonical_ticker = normalize_ticker(symbol)
    profile = SYMBOL_CATALOG.get(canonical_ticker, {})
    return {
        "ticker": canonical_ticker,
        "company_name": profile.get("company_name", canonical_ticker),
        "sector": profile.get("sector", "Other"),
        "benchmark_ticker": profile.get("benchmark_ticker", "SPY" if canonical_ticker != "SPY" else None),
        "benchmark_name": profile.get(
            "benchmark_name",
            "SPDR S&P 500 ETF Trust" if canonical_ticker != "SPY" else None,
        ),
        "benchmark_kind": profile.get("benchmark_kind", "broad_market"),
        "aliases": profile.get("aliases", []),
        "is_benchmark": bool(profile.get("is_benchmark", False)),
    }


def build_news_query_terms(symbol: str) -> list[str]:
    profile = get_symbol_profile(symbol)
    terms = [profile["ticker"], profile["company_name"], *profile["aliases"]]
    deduped_terms = []
    seen = set()

    for term in terms:
        cleaned = str(term or "").strip()
        if not cleaned:
            continue
        normalized = cleaned.upper()
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped_terms.append(cleaned)

    return deduped_terms[:4]


def find_canonical_entities(text: str, symbol: str) -> list[str]:
    lowered_text = (text or "").lower()
    if not lowered_text:
        return []

    profile = get_symbol_profile(symbol)
    matches = []
    for candidate in [profile["ticker"], profile["company_name"], *profile["aliases"]]:
        candidate_text = str(candidate or "").strip()
        if not candidate_text:
            continue
        if candidate_text.lower() in lowered_text:
            matches.append(candidate_text)

    return matches


def resolve_tracked_tickers(configured_tickers: Iterable[str]) -> list[str]:
    ordered_tickers = []
    seen = set()

    def _append(symbol: str):
        normalized = normalize_ticker(symbol)
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        ordered_tickers.append(normalized)

    for ticker in configured_tickers:
        _append(ticker)

    for ticker in list(ordered_tickers):
        profile = get_symbol_profile(ticker)
        benchmark_ticker = profile.get("benchmark_ticker")
        if benchmark_ticker:
            _append(benchmark_ticker)

    _append("SPY")
    return ordered_tickers
