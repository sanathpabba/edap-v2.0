"""Deterministic reference data on the master ID standard (see docs/architecture/decisions.md).
Source-system column naming is legacy-style on purpose (sec_code, book_cd, cpty_code, acct_ref)."""
import math
import random

EQ_EXCHANGES = [("NYSE", "USD"), ("NASDAQ", "USD"), ("TSX", "CAD"), ("LSE", "GBP"), ("XETRA", "EUR"),
                ("TSE", "JPY"), ("HKEX", "HKD"), ("SGX", "SGD"), ("ASX", "AUD"), ("SIX", "CHF")]
PRICE_SCALE = {"JPY": 110.0, "HKD": 8.0}
FX_PAIRS = [("EUR", "USD", 1.10), ("GBP", "USD", 1.32), ("USD", "JPY", 159.6), ("USD", "CAD", 1.4285),
            ("USD", "CHF", 0.8393), ("AUD", "USD", 0.676), ("USD", "SGD", 1.2888), ("USD", "HKD", 7.847),
            ("EUR", "GBP", 0.8315), ("EUR", "JPY", 175.8)]
COMMODITIES = [("Gold", 2650.0, 100, "COMEX"), ("Silver", 31.0, 5000, "COMEX"), ("Crude Oil WTI", 72.0, 1000, "NYMEX"),
               ("Brent Crude", 76.0, 1000, "ICE"), ("Natural Gas", 3.1, 10000, "NYMEX"), ("Copper", 4.2, 25000, "COMEX"),
               ("Platinum", 960.0, 50, "NYMEX"), ("Wheat", 5.6, 5000, "CBOT"), ("Corn", 4.4, 5000, "CBOT"),
               ("Soybeans", 10.4, 5000, "CBOT")]
W1 = ["Northern", "Maple", "Pacific", "Atlas", "Summit", "Harbour", "Crescent", "Meridian", "Granite", "Evergreen",
      "Lakeshore", "Redwood", "Silverline", "Bluewater", "Ironbridge", "Falcon", "Orion", "Westfield", "Eastgate", "Highland"]
W2 = ["Energy", "Financial", "Logistics", "Mining", "Pharma", "Retail", "Software", "Telecom", "Utilities", "Industrials",
      "Insurance", "Semiconductor", "Foods", "Aerospace", "Realty"]
SECTORS = ["Energy", "Financials", "Materials", "Health Care", "Consumer", "Technology", "Telecom", "Utilities", "Industrials", "Real Estate"]
COUNTRY = {"USD": "US", "CAD": "CA", "GBP": "GB", "EUR": "DE", "JPY": "JP", "HKD": "HK", "SGD": "SG", "AUD": "AU", "CHF": "CH"}
BU = ["Equities", "Fixed Income", "FX", "Commodities", "Derivatives", "Multi-Asset"]
BU_TYPES = {"Equities": ["EQUITY"], "Fixed Income": ["BOND"], "FX": ["FX"], "Commodities": ["COMMODITY"],
            "Derivatives": ["DERIVATIVE", "EQUITY"], "Multi-Asset": ["EQUITY", "BOND", "FX", "COMMODITY", "DERIVATIVE"]}
CPTY_TYPES = ["BANK", "BROKER_DEALER", "HEDGE_FUND", "ASSET_MANAGER", "CLEARING_HOUSE", "CORPORATE"]
RATINGS = ["AAA", "AA", "A", "BBB", "BB"]


def _lei(r):
    return "".join(r.choice("0123456789ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(20))


def build(cfg):
    r = random.Random(cfg["seed"])
    ccys = cfg["currencies"]
    mix = cfg["instrument_mix"]
    n = cfg["volumes"]["instruments"]
    counts = {k: round(n * v / sum(mix.values())) for k, v in mix.items()}
    counts["EQUITY"] += n - sum(counts.values())
    instruments, i, used_t = [], 0, set()

    def ticker():
        while True:
            t = "".join(r.choice("ABCDEFGHJKLMNPRSTUVWXYZ") for _ in range(r.choice([3, 4])))
            if t not in used_t:
                used_t.add(t)
                return t

    def add(typ, name, ccy, exch, base, csize, extra=None):
        nonlocal i
        i += 1
        t = ticker()
        d = dict(sec_code="INST%05d" % i, sec_name=name, sec_type=typ, ccy=ccy, exchange=exch, ticker=t,
                 isin=COUNTRY[ccy] + "".join(r.choice("0123456789") for _ in range(9)) + str(r.randint(0, 9)),
                 sector=None, country=COUNTRY[ccy], contract_size=csize, base_price=round(base, 4), is_active=1)
        d.update(extra or {})
        instruments.append(d)

    eq_list = []
    for _ in range(counts["EQUITY"]):
        exch, ccy = r.choice(EQ_EXCHANGES)
        base = math.exp(r.uniform(math.log(12), math.log(350))) * PRICE_SCALE.get(ccy, 1.0)
        add("EQUITY", "%s %s Corp" % (r.choice(W1), r.choice(W2)), ccy, exch, base, 1, {"sector": r.choice(SECTORS)})
        eq_list.append(instruments[-1])
    for _ in range(counts["BOND"]):
        ccy = r.choice(ccys)
        cpn = round(r.uniform(1.5, 6.5), 2)
        yr = r.choice([2028, 2030, 2032, 2035, 2040])
        add("BOND", "%s %s %s%% %d" % (r.choice(W1), r.choice(["Govt", "Corp", "Provincial", "Treasury"]), cpn, yr),
            ccy, "OTC", r.uniform(94, 106), 0.01, {"sector": "Fixed Income"})
    pairs = FX_PAIRS[: counts["FX"]]
    for b, q, rate in pairs:
        add("FX", "%s/%s" % (b, q), q, "OTC", rate, 1, {"sector": "FX"})
    for name, px, size, exch in COMMODITIES[: counts["COMMODITY"]]:
        add("COMMODITY", name + " Future", "USD", exch, px, size, {"sector": "Commodities"})
    for _ in range(counts["DERIVATIVE"]):
        u = r.choice(eq_list)
        strike = round(u["base_price"] * r.choice([0.9, 1.0, 1.1]), 0)
        cp = r.choice(["C", "P"])
        add("DERIVATIVE", "%s Dec26 %d %s" % (u["ticker"], strike, cp), u["ccy"], "OTC",
            max(0.05, u["base_price"] * r.uniform(0.01, 0.08)), 100, {"sector": u["sector"]})
    portfolios = []
    for p in range(1, cfg["volumes"]["portfolios"] + 1):
        bu = BU[(p - 1) % len(BU)]
        base = r.choice(["USD", "CAD", "CAD", "EUR", "GBP", "JPY", "CHF", "AUD", "SGD", "HKD"])
        portfolios.append(dict(book_cd="PORT%04d" % p, book_name="%s %s Book %d" % (r.choice(W1), bu, p), business_unit=bu,
                               base_ccy=base, region={"USD": "AMERICAS", "CAD": "AMERICAS", "EUR": "EMEA", "GBP": "EMEA",
                                                      "CHF": "EMEA"}.get(base, "APAC"), is_active=1))
    accounts = []
    for a in range(1, cfg["volumes"]["accounts"] + 1):
        pf = portfolios[(a - 1) % len(portfolios)] if a <= len(portfolios) else r.choice(portfolios)
        accounts.append(dict(acct_ref="ACC%05d" % a, acct_name="%s %s Account" % (pf["book_name"].split(" Book")[0], r.choice(["Custody", "Cash", "Margin", "Settlement"])),
                             acct_type=r.choice(["CUSTODY", "CASH", "MARGIN", "SETTLEMENT"]),
                             ccy=pf["base_ccy"] if r.random() < 0.7 else r.choice(ccys), book_cd=pf["book_cd"],
                             custodian=r.choice(["Northern Trust", "State Street", "BNY", "RBC I&TS"]), is_active=1))
    cptys = []
    for c in range(1, cfg["volumes"]["counterparties"] + 1):
        ccy = r.choice(ccys)
        rt = r.choices(RATINGS, weights=[5, 20, 35, 30, 10])[0]
        cptys.append(dict(cpty_code="CPTY%04d" % c, cpty_name="%s %s %s" % (r.choice(W1), r.choice(["Securities", "Capital", "Markets", "Partners", "Bank"]), r.choice(["LLC", "Ltd", "Inc", "plc", "AG"])),
                          cpty_type=r.choice(CPTY_TYPES), country=COUNTRY[ccy],
                          risk_category={"AAA": "LOW", "AA": "LOW", "A": "MEDIUM", "BBB": "MEDIUM", "BB": "HIGH"}[rt],
                          credit_rating=rt, lei=_lei(r), is_active=1))
    return dict(instruments=instruments, portfolios=portfolios, accounts=accounts, counterparties=cptys)
