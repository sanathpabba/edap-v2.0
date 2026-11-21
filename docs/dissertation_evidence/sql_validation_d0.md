# Azure SQL source validation - state after `d0`

Run (UTC): 2026-11-21 00:32:53 | as-of business date: 2026-11-16

**22 / 22 checks passed**

| Check | Result | Detail |
|---|---|---|
| Row counts: instruments/portfolios/accounts/counterparties | PASS | expected 100/20/30/50 |
| Row count: trades | PASS | expected 5000, found 5000 |
| Master ID format: sec_code | PASS | 0 violations |
| Master ID format: book_cd | PASS | 0 violations |
| Master ID format: cpty_code | PASS | 0 violations |
| Master ID format: acct_ref | PASS | 0 violations |
| Master ID format: trade_no | PASS | 0 violations |
| Trade account belongs to trade portfolio (1.0 defect: 582) | PASS | 0 mismatches expected |
| Trade currency equals instrument currency | PASS | 0 mismatches expected |
| No nulls in key/core trade columns | PASS | 0 expected |
| Settlement date >= trade date; T+1/T+2 only | PASS | 0 violations |
| Gross = qty x price x contract size | PASS | 0 violations (tolerance 0.02) |
| Net = gross +/- commission + fees by side | PASS | 0 violations |
| SETTLED/FAILED only when settlement date reached | PASS | 0 violations as of 2026-11-16 |
| EXECUTED/NEW not past settlement | PASS | 0 violations |
| Realistic status mix (CANCELLED <8%, FAILED <4%, SETTLED majority) | PASS | {'CANCELLED': '4.6%', 'EXECUTED': '0.3%', 'FAILED': '2.1%', 'NEW': '0.0%', 'SETTLED': '93.0%'} |
| Unamended trade prices within 2% of that day's market price | PASS | 0 of 4716 outside |
| Max single-trade gross amount sane (<= USD 100M equivalent) | PASS | max USD 20.6M |
| Watermark column populated on all tables | PASS | 0 nulls |
| Load log contains expected scenarios | PASS | ['d0'] |
| Outbox: every trade has event history consistent with status | PASS | 0 trades without matching events |
| Outbox event_id unique + format | PASS | 0 bad ids |
