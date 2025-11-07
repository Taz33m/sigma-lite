# Disabling Authentication

For easier development and testing, SigmaLite supports disabling authentication entirely.

## How to Disable Authentication

### Backend

Edit `backend/.env` and add:

```env
DISABLE_AUTH=True
```

### Frontend

Edit `frontend/.env` and add:

```env
VITE_DISABLE_AUTH=true
```

## What Happens When Auth is Disabled?

### Backend Behavior

- All API endpoints bypass authentication checks
- A demo user (`demo_user`) is automatically created and used for all requests
- No JWT tokens are required
- All data is associated with the demo user

### Frontend Behavior

- Login and Register pages are still accessible but not required
- You can navigate directly to the dashboard at `http://localhost:5173/`
- No authentication state is checked for protected routes
- You can start uploading and working with data immediately

## Use Cases

✅ **Quick Testing** - Test features without creating accounts  
✅ **Demos** - Show the platform without authentication friction  
✅ **Development** - Focus on feature development without auth overhead  
✅ **CI/CD** - Run automated tests without authentication setup  

## Security Warning

⚠️ **Never use `DISABLE_AUTH=True` in production!**

This feature is intended for:
- Local development
- Testing environments
- Demos and presentations

## Re-enabling Authentication

To re-enable authentication:

1. **Backend**: Set `DISABLE_AUTH=False` in `backend/.env` (or remove the line)
2. **Frontend**: Set `VITE_DISABLE_AUTH=false` in `frontend/.env` (or remove the line)
3. Restart both servers

## Default Configuration

By default, authentication is **enabled** in production and **disabled** in the example configuration for easier onboarding.

To use authentication from the start:
- Remove or set `DISABLE_AUTH=False` in `backend/.env`
- Remove or set `VITE_DISABLE_AUTH=false` in `frontend/.env`
- Register a new account at `http://localhost:5173/register`

## Demo User Details

When authentication is disabled, all operations use:
- **Username**: `demo_user`
- **Email**: `demo@sigmalite.com`
- **Full Name**: Demo User

This user is automatically created on first API request.
