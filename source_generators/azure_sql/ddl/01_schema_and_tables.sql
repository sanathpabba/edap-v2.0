-- EDAP 2.0 Azure SQL source system. Idempotent: safe to re-run (drops and recreates synthetic data).
-- Legacy-style column names on purpose (canonical names are produced in Silver via YAML mappings).
IF SCHEMA_ID('reference') IS NULL EXEC('CREATE SCHEMA reference');
GO
IF SCHEMA_ID('source') IS NULL EXEC('CREATE SCHEMA source');
GO
IF OBJECT_ID('source.trade_event_outbox') IS NOT NULL DROP TABLE source.trade_event_outbox;
GO
IF OBJECT_ID('source.trades') IS NOT NULL DROP TABLE source.trades;
GO
IF OBJECT_ID('source.load_log') IS NOT NULL DROP TABLE source.load_log;
GO
IF OBJECT_ID('reference.accounts') IS NOT NULL DROP TABLE reference.accounts;
GO
IF OBJECT_ID('reference.counterparties') IS NOT NULL DROP TABLE reference.counterparties;
GO
IF OBJECT_ID('reference.portfolios') IS NOT NULL DROP TABLE reference.portfolios;
GO
IF OBJECT_ID('reference.instruments') IS NOT NULL DROP TABLE reference.instruments;
GO
CREATE TABLE reference.instruments (
  sec_code      VARCHAR(10)   NOT NULL PRIMARY KEY,
  sec_name      VARCHAR(100)  NOT NULL,
  sec_type      VARCHAR(12)   NOT NULL CHECK (sec_type IN ('EQUITY','BOND','FX','COMMODITY','DERIVATIVE')),
  ccy           CHAR(3)       NOT NULL,
  exchange      VARCHAR(10)   NOT NULL,
  ticker        VARCHAR(6)    NOT NULL UNIQUE,
  isin          VARCHAR(12)   NOT NULL UNIQUE,
  sector        VARCHAR(30)   NULL,
  country       CHAR(2)       NOT NULL,
  contract_size DECIMAL(18,6) NOT NULL,
  is_active     BIT           NOT NULL,
  created_ts    DATETIME2(3)  NOT NULL,
  last_updated_ts DATETIME2(3) NOT NULL
);
GO
CREATE TABLE reference.portfolios (
  book_cd       VARCHAR(8)    NOT NULL PRIMARY KEY,
  book_name     VARCHAR(100)  NOT NULL,
  business_unit VARCHAR(20)   NOT NULL,
  base_ccy      CHAR(3)       NOT NULL,
  region        VARCHAR(10)   NOT NULL,
  is_active     BIT           NOT NULL,
  created_ts    DATETIME2(3)  NOT NULL,
  last_updated_ts DATETIME2(3) NOT NULL
);
GO
CREATE TABLE reference.counterparties (
  cpty_code     VARCHAR(8)    NOT NULL PRIMARY KEY,
  cpty_name     VARCHAR(100)  NOT NULL,
  cpty_type     VARCHAR(20)   NOT NULL,
  country       CHAR(2)       NOT NULL,
  risk_category VARCHAR(8)    NOT NULL CHECK (risk_category IN ('LOW','MEDIUM','HIGH')),
  credit_rating VARCHAR(4)    NOT NULL,
  lei           CHAR(20)      NOT NULL,
  is_active     BIT           NOT NULL,
  created_ts    DATETIME2(3)  NOT NULL,
  last_updated_ts DATETIME2(3) NOT NULL
);
GO
CREATE TABLE reference.accounts (
  acct_ref      VARCHAR(8)    NOT NULL PRIMARY KEY,
  acct_name     VARCHAR(100)  NOT NULL,
  acct_type     VARCHAR(12)   NOT NULL,
  ccy           CHAR(3)       NOT NULL,
  book_cd       VARCHAR(8)    NOT NULL REFERENCES reference.portfolios(book_cd),
  custodian     VARCHAR(30)   NULL,
  is_active     BIT           NOT NULL,
  created_ts    DATETIME2(3)  NOT NULL,
  last_updated_ts DATETIME2(3) NOT NULL
);
GO
CREATE TABLE source.trades (
  trade_no      VARCHAR(12)   NOT NULL PRIMARY KEY,
  trade_dt      DATE          NOT NULL,
  trade_ts      DATETIME2(3)  NOT NULL,
  settle_dt     DATE          NOT NULL,
  sec_code      VARCHAR(10)   NOT NULL REFERENCES reference.instruments(sec_code),
  book_cd       VARCHAR(8)    NOT NULL REFERENCES reference.portfolios(book_cd),
  cpty_code     VARCHAR(8)    NOT NULL REFERENCES reference.counterparties(cpty_code),
  acct_ref      VARCHAR(8)    NOT NULL REFERENCES reference.accounts(acct_ref),
  side          VARCHAR(4)    NOT NULL CHECK (side IN ('BUY','SELL')),
  qty           DECIMAL(18,4) NOT NULL CHECK (qty > 0),
  price         DECIMAL(18,6) NOT NULL CHECK (price > 0),
  trade_ccy     CHAR(3)       NOT NULL,
  gross_amt     DECIMAL(22,2) NOT NULL,
  commission    DECIMAL(18,2) NOT NULL,
  fees          DECIMAL(18,2) NOT NULL,
  net_amt       DECIMAL(22,2) NOT NULL,
  trade_status  VARCHAR(10)   NOT NULL CHECK (trade_status IN ('NEW','EXECUTED','SETTLED','CANCELLED','FAILED')),
  version       INT           NOT NULL,
  trader        VARCHAR(40)   NOT NULL,
  strategy      VARCHAR(30)   NOT NULL,
  created_ts    DATETIME2(3)  NOT NULL,
  last_updated_ts DATETIME2(3) NOT NULL
);
GO
CREATE INDEX ix_trades_updated ON source.trades(last_updated_ts);
CREATE INDEX ix_trades_sec ON source.trades(sec_code);
CREATE INDEX ix_trades_book ON source.trades(book_cd);
CREATE INDEX ix_instr_updated ON reference.instruments(last_updated_ts);
CREATE INDEX ix_cpty_updated ON reference.counterparties(last_updated_ts);
GO
-- Outbox: every business event on a trade; the streaming producer publishes unpublished rows to Event Hubs.
CREATE TABLE source.trade_event_outbox (
  event_id      VARCHAR(12)   NOT NULL PRIMARY KEY,
  trade_no      VARCHAR(12)   NOT NULL REFERENCES source.trades(trade_no),
  event_type    VARCHAR(20)   NOT NULL CHECK (event_type IN ('TRADE_EXECUTED','TRADE_AMENDED','TRADE_CANCELLED','TRADE_SETTLED','TRADE_FAILED')),
  event_ts      DATETIME2(3)  NOT NULL,
  sec_code      VARCHAR(10)   NOT NULL,
  book_cd       VARCHAR(8)    NOT NULL,
  cpty_code     VARCHAR(8)    NOT NULL,
  side          VARCHAR(4)    NOT NULL,
  qty           DECIMAL(18,4) NOT NULL,
  price         DECIMAL(18,6) NOT NULL,
  ccy           CHAR(3)       NOT NULL,
  scenario      VARCHAR(4)    NOT NULL,
  created_ts    DATETIME2(3)  NOT NULL,
  published_ts  DATETIME2(3)  NULL
);
GO
CREATE INDEX ix_outbox_pub ON source.trade_event_outbox(published_ts);
GO
CREATE TABLE source.load_log (
  scenario      VARCHAR(4)    NOT NULL PRIMARY KEY,
  as_of_date    DATE          NOT NULL,
  run_start_ts  DATETIME2(3)  NOT NULL,
  run_end_ts    DATETIME2(3)  NOT NULL,
  trades_inserted INT NOT NULL,
  trades_updated  INT NOT NULL,
  ref_inserted    INT NOT NULL,
  ref_updated     INT NOT NULL,
  outbox_rows     INT NOT NULL
);
GO
