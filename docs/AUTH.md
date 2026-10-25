# Authentication design (Week 5)

## What is implemented
- **Register** `POST /api/v1/auth/register`: email (stored in lower case) and a password of 8 to 72 characters. The password is hashed with **bcrypt** (cost 12, a new random salt every time) and only the hash is stored.
- **Login** `POST /api/v1/auth/login`: checks the hash and returns a signed **JWT** (`sub` = user id, `iat`, `exp`) valid for 60 minutes, signed with HS256 and a secret of at least 32 characters.
- **Current user** `GET /api/v1/me` and **logout** `POST /api/v1/auth/logout` need the header `Authorization: Bearer <token>`.
- **Roles:** `user` or `admin`. The role is read from the database on every request (`require_admin`), not from the token, so a role change takes effect immediately. An existing user is promoted with `python -m tools.make_admin EMAIL`.
- **Multi-tenant:** every user is a separate account; later report routes check ownership in code, and other people's reports answer 404.

## Decisions and reasons
| Decision | Reason |
|---|---|
| bcrypt for passwords | Slow on purpose, salted, widely reviewed; named in the Week 5 requirement |
| Passwords limited to 72 bytes | bcrypt only uses the first 72 bytes; longer input is rejected instead of silently cut |
| Same message for wrong password and unknown email, plus a dummy hash check | The response and its timing do not reveal which emails are registered |
| JWT kept short-lived (60 minutes) | A stolen token stops working soon |
| Token stored in **sessionStorage** in the browser | Simple, cleared when the tab closes. Trade-off: JavaScript can read it, so a cross-site scripting bug would expose it. Mitigations: no user HTML is rendered, a strict content security policy is added at deployment (Week 10 and 11). An HttpOnly cookie is the alternative if the university or advisor prefers it |
| Logout is stateless | The client deletes the token; the token also expires by itself. A token blocklist is not needed for the MVP |
| One error format `{"error": {"code", "message"}}` | The web client shows safe messages; no stack traces or SQL reach the user |
| CORS limited to the configured web client address | Other websites cannot call the API from a browser |

## Known limits (honest list)
- No limit on login attempts yet: rate limiting (30 requests per minute) is planned for Week 10.
- No password reset and no email verification in this version.
- A logged-out token stays valid until it expires (at most 60 minutes) if someone copied it.
- Only the users table exists; the other tables of the ERD are added by later migrations.

## Database connection
`GET /health/db` runs `SELECT 1` and answers 200 when the database is reachable and 503 otherwise. Migrations are applied with `alembic upgrade head`.
