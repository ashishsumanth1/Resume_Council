# Railway Deployment (Two Services)

This repo can be deployed to Railway as two services: backend API + frontend UI.

## 1) Backend service

Create a new Railway service from this repo.

- Root Directory: `/` (repo root)
- Build Command:
  - `pip install -r requirements.txt`
- Start Command:
  - `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

Environment variables (Backend):
- `OPENROUTER_API_KEY` = your OpenRouter key
- `APP_AUTH_EMAIL` = allowed email
- `APP_AUTH_PASSWORD` = allowed password
- `APP_AUTH_TOTP_SECRET` = base32 secret for Google Authenticator
- `APP_AUTH_TOKEN_SECRET` = secret for signing session tokens (optional; defaults to password)
- `CORS_ORIGINS` = frontend URL (comma-separated if multiple), e.g.
  - `https://your-frontend.railway.app`

Optional (if you use resume features):
- `RESUME_SEND_FULL_PROFILE`, `RESUME_DRAFT_MAX_TOKENS`, `RESUME_JUDGE_MAX_TOKENS`, `RESUME_POLISH_MAX_TOKENS`

Note: data is stored under `data/` and will be ephemeral unless you attach a Railway volume.

## 2) Frontend service

Create a second Railway service from the same repo.

- Root Directory: `frontend`
- Build Command:
  - `npm install && npm run build`
- Start Command:
  - `npm run preview -- --host 0.0.0.0 --port $PORT`

Environment variables (Frontend):
- `VITE_API_BASE` = backend URL, e.g.
  - `https://your-backend.railway.app`

## 3) Verify

- Open frontend URL and make sure it can load conversations.
- If you get CORS errors, confirm `CORS_ORIGINS` matches the frontend URL exactly.
