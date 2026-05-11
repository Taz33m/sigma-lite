# Disabling Authentication

SigmaLite ships with an `DISABLE_AUTH` flag intended for local demos and
quick tests where the friction of registration is unnecessary.

> ⚠️ **Never enable this in any environment that is reachable from the
> internet.** When the flag is on, every request is silently routed to a
> built-in `demo_user` and there are no auth checks. The backend logs a
> warning at startup whenever the flag is active.

## How to enable it (local only)

### Backend

In `backend/.env`:

```env
DISABLE_AUTH=True
```

### Frontend

In `frontend/.env`:

```env
VITE_DISABLE_AUTH=true
```

Restart both servers after changing these.

## What changes

### Backend
- All authenticated endpoints skip the JWT check.
- The first request creates (or fetches) a `demo_user` record and treats it
  as the current user for every subsequent request.
- All datasets, sheets, and charts are owned by that demo user.

### Frontend
- On app load, the frontend still calls `/api/auth/me` and hydrates the
  backend demo user. Protected routes wait for that verified response before
  rendering.
- The `/login` and `/register` pages are still reachable but unnecessary.

## Default

`DISABLE_AUTH` defaults to **`False`**. The shipped `.env.example` files
also set it to `False` to make sure the flag is an explicit opt-in. Earlier
revisions of the project shipped with the flag on — if you're upgrading,
double-check your `.env`.

## Demo user details

| Field      | Value                |
| ---------- | -------------------- |
| Username   | `demo_user`          |
| Email      | `demo@sigmalite.com` |
| Full name  | `Demo User`          |

The demo user is created on the first request after the flag is enabled.
It is not a password-login account in normal auth mode; use the register form
or create a real local user when `DISABLE_AUTH=False`.

## Re-enabling normal auth

1. Set `DISABLE_AUTH=False` in `backend/.env` (or remove the line).
2. Set `VITE_DISABLE_AUTH=false` in `frontend/.env` (or remove the line).
3. Restart both servers and register at <http://localhost:5173/register>.
