# OTMtest bot

The Django admin manages exam subjects and PDFs. The Telegram bot registers users,
delivers exams, grades answers, and looks up admission estimates in the bundled CSV.

## Setup

Use Python 3.15.2 and install the dependencies in a virtual environment.

```sh
python3.15 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

Create a local `.env` at the repository root or supply these environment variables.
The existing `tgproj/.env` location is supported.

```dotenv
secret_key=replace-with-a-generated-django-secret
bot_token=replace-with-your-telegram-bot-token
debug=False
hosts=localhost,127.0.0.1
```

Run `python manage.py migrate`, then `python manage.py createsuperuser` to
enable admin access. Run `python manage.py bot` to start polling. Run one
polling process per token. The bot accepts messages in private chats and stores
in-progress conversations in memory. Restarting the process clears those
conversations. Profiles and test counters remain in the database.

SQLite defaults to `db.sqlite3`. Use `database_path` to point to a private
location or an existing database. If an older database already has the original
tables and no recorded app migration, back it up, verify its schema matches
`tgapp/migrations/0001_initial.py`, then run
`python manage.py migrate --fake-initial` to adopt the existing tables and apply
subsequent changes. Keep production databases and backups outside the checkout.

Add subjects and PDFs in the Django admin. PDFs are stored under `uploads/`
relative to `media_root` (the repository root by default). Put answer keys at
`answers/<localized subject name>/<test number>.json`, or set `answers_dir`
to another directory. Test numbers start at 1 for each subject and language,
in PDF upload record order. Each key contains an `answers` array of 105
strings, such as `"1.A"`. The deployed PDFs and answer keys are required for
live exams.

Run `python manage.py test` to run the regression tests.
