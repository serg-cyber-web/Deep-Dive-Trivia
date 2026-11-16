# Deep Dive — Online-Ready Version

## Upload to GitHub
1. Create a new GitHub repository, for example `deep-dive-trivia`.
2. Upload **the contents of this folder** to the repository root (`app.py` should be visible on the repo front page).
3. Commit your changes. Keep `.env` and any personal or private data out of the repository.

## Deploy to Render
1. At render.com select **New → Web Service** and connect the GitHub repository.
2. Runtime: Python 3; build command: `pip install -r requirements.txt`.
3. Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`.
4. Choose a service plan, deploy, and open the generated `.onrender.com` website.

**IMPORTANT: The free Render plan does not keep SQLite changes after the service spins down or redeploys.** The starter question bank is recreated from `seed_data.json`, but submissions, active games, and observed rarity counts reset. That makes this version good for a demo, not a persistent community rarity game. For persistence, use a paid service with a persistent disk and set `DATABASE_PATH` to an absolute path on the mounted disk, e.g. `/var/data/game.db` (mount a disk at `/var/data`), or migrate the database logic to hosted PostgreSQL.

Before opening this up broadly, add rate limiting, cleanup of old games, moderation/admin review, privacy safeguards, and basic abuse protection. Never promise that scoring is identical to Krillion.

## Run locally
`python3 -m pip install -r requirements.txt`
`python3 -m uvicorn app:app --reload`

Open http://127.0.0.1:8000. The app stores data in `game.db` locally.
