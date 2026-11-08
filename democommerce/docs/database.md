# Database notes

SQLite is the default local database (`backend/democommerce.db`). Set
`DEMO_DATABASE_URL` to select another SQLAlchemy URL. The default file is ignored by Git.

| Table | Purpose |
|---|---|
| `users` | Customer and administrator identities, roles and password hashes |
| `products` | Fictional store catalogue, prices in integer cents and stock |
| `sessions` | SHA-256 token digests and expiry timestamps |
| `cart_items` | Per-customer persistent cart quantities |
| `orders` | Shipping details, simulated status, amount and reference |
| `order_items` | Order-time product name and price snapshots |
| `contact_messages` | Validated fictional contact requests |
| `app_settings` | Current security profile |
| `configuration_audit` | Profile, note, administrator and change time |
| `audit_events` | Login, customer, order and administrator actions |

All tables use integer primary keys and SQLAlchemy foreign keys. Product/order amounts are
integer cents, avoiding floating-point currency calculations. Order item values are
snapshotted so later product edits do not rewrite historical receipts. Passwords are
PBKDF2-HMAC-SHA256 hashes with per-password random salts; raw session tokens are not
stored.

The initial schema is created on API startup. This is suitable for the isolated research
instance while the schema is being developed. Add and test Alembic migrations before
preserving a production or long-running research database across schema revisions. Back up
the SQLite database before any manual schema change.
