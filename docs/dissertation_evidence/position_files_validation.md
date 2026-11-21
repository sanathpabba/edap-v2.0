# Position file validation

| File | Rows | Result | Detail |
|---|---|---|---|
| d0/positions_20261116.csv | 1296 | PASS | all keys/ccy/dates valid, no duplicates |
| d1/positions_20261117.csv | 1305 | PASS | all keys/ccy/dates valid, no duplicates |
| d2_bad/positions_20261118.csv | 1312 | PASS | detected == injected: {'missing_portfolio': 10, 'duplicate_position_id': 6, 'invalid_quantity': 8, 'invalid_currency': 7, 'unknown_instrument': 5, 'invalid_date': 5} |
| d2_fixed/positions_20261118_v2.csv | 1312 | PASS | all keys/ccy/dates valid, no duplicates |
