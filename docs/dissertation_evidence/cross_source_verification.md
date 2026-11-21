# Cross-source verification

Run (UTC): 2026-11-21 00:57:10

**8 / 8 checks passed**

| Check | Result | Detail |
|---|---|---|
| Event Hubs received exactly what the producer sent (IncomingMessages metric) | PASS | metric 10661, producer manifests 10661 |
| Stream sample: payloads parse and keys match SQL (instrument/portfolio/counterparty) | PASS | sample 1279 messages: 1279 complete, 1279 resolve to SQL trades, 0 non-JSON/incomplete (injected malformed) |
| Event history (outbox) reproduces every trade's SQL status | PASS | 5180 trades compared, 0 differ |
| Every non-NEW SQL trade has an event history | PASS | 0 trades without events |
| All outbox events published after D2 (none stuck) | PASS | 0 unpublished |
| Injected stream conditions recorded for later DQ/dedup checks | PASS | duplicates 104, out-of-order 210, malformed 18 |
| FX history file covers every instrument and portfolio currency | PASS | in use ['AUD', 'CAD', 'CHF', 'EUR', 'GBP', 'HKD', 'JPY', 'SGD', 'USD']; FX file has ['AUD', 'CAD', 'CHF', 'EUR', 'GBP', 'HKD', 'JPY', 'SGD', 'USD'] |
| FX history spans trade history (no gaps > 4 days) | PASS | 509 dated rate sets |
