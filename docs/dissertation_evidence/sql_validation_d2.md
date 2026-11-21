# Azure SQL source validation - state after `d2`

Run (UTC): 2026-11-21 00:55:42 | as-of business date: 2026-11-18

**25 / 25 checks passed**

| Check | Result | Detail |
|---|---|---|
| Row counts: instruments/portfolios/accounts/counterparties | PASS | expected 100/20/30/50 |
| Row count: trades | PASS | expected 5210, found 5210 |
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
| SETTLED/FAILED only when settlement date reached | PASS | 0 violations as of 2026-11-18 |
| EXECUTED/NEW not past settlement | PASS | 0 violations |
| Realistic status mix (CANCELLED <8%, FAILED <4%, SETTLED majority) | PASS | {'CANCELLED': '4.5%', 'EXECUTED': '2.5%', 'FAILED': '2.0%', 'NEW': '0.6%', 'SETTLED': '90.4%'} |
| Unamended trade prices within 2% of that day's market price | PASS | 0 of 4901 outside |
| Max single-trade gross amount sane (<= USD 100M equivalent) | PASS | max USD 20.6M |
| Watermark column populated on all tables | PASS | 0 nulls |
| Load log contains expected scenarios | PASS | ['d0', 'd1', 'd2'] |
| Watermark picks d1 delta (last_updated_ts = run ts) | PASS | expected <= 132 (120 new + 12 updated), found 65 |
| Watermark picks d2 delta (last_updated_ts = run ts) | PASS | expected 168 (90 new + 78 updated), found 168 |
| Outbox: every trade has event history consistent with status | PASS | 0 trades without matching events |
| Outbox: no event precedes the trade's own execution event | PASS | 0 events out of order within a trade's lifecycle |
| Outbox event_id unique + format | PASS | 0 bad ids |
