# API guide

FastAPI generates the OpenAPI schema at `/openapi.json` and interactive documentation at
`/docs`. Use `http://127.0.0.1:8001/docs` locally. Customer and administrator
authentication use the `democommerce_session` HttpOnly cookie; browser requests include
credentials. Do not put session tokens in URLs or local storage.

## Public catalogue and contact

| Method | Endpoint | Behavior |
|---|---|---|
| `GET` | `/api/products?q=&category=&featured=` | List/search active products |
| `GET` | `/api/products/{slug}` | Read one active product |
| `POST` | `/api/contact` | Validate and persist a contact request |

## Authentication and customer

| Method | Endpoint | Behavior |
|---|---|---|
| `POST` | `/api/auth/register` | Create a customer and sign in |
| `POST` | `/api/auth/login` | Authenticate and set session cookie |
| `POST` | `/api/auth/logout` | Revoke current session |
| `GET/PATCH` | `/api/auth/me` | Read/update own profile |
| `GET` | `/api/cart` | Read own cart and current totals |
| `POST` | `/api/cart/items` | Add a product after stock validation |
| `PATCH/DELETE` | `/api/cart/items/{item_id}` | Change/remove an owned cart item |
| `POST` | `/api/orders` | Create a simulated order; accepts name/address only |
| `GET` | `/api/orders` | List own orders with item snapshots and status |
| `GET` | `/api/orders/{reference}` | Read one of the current user's orders |

## Administrator

Every route below requires the `admin` role:

| Method | Endpoint | Behavior |
|---|---|---|
| `GET/POST` | `/api/admin/products` | List all products/create product |
| `PUT/DELETE` | `/api/admin/products/{id}` | Edit/archive product |
| `GET` | `/api/admin/orders` | List orders and customer summary |
| `PATCH` | `/api/admin/orders/{id}/status` | Update a simulated order status |
| `GET` | `/api/admin/customers` | List customer records and order counts |
| `GET` | `/api/admin/contact-messages` | Read local contact inbox |
| `GET/POST` | `/api/admin/security-profile` | Read/apply local-only configuration profiles |
| `GET` | `/api/admin/audit` | Read the most recent administrative/business events |

Prices use integer cents; profile/order responses use RFC 3339 timestamps. Invalid fields
return FastAPI validation errors. Customer data is scoped to the authenticated identity;
administrative routes return `401` without a session and `403` to a customer account.
