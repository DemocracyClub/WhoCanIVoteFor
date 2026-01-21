## Installation requirements on ubuntu

WCIVF requires Python 3.12.

To install the required system packages:

## Ubuntu

```shell

sudo apt-get install python3-dev libpq-dev libjpeg-dev redis-server libtidy-dev

```

## OSX with Homebrew

```shell
brew install redis postgresql jpeg cmake
```

OSX users also need to manually install `tidy` following 
[these steps](https://github.com/htacg/tidy-html5)

## Python packages

Python packages and environments are managed using
`uv`.

To install:

```shell
uv sync
```

This will create a virtual environment and install packages into it.

You can activate this environment by running

```shell
source .venv/bin/activate
```

Or by `uv run` will automatically use the correct environment.

# Running tests

Check that your env has correctly installed and project is working by running
the tests:

```shell
uv run pytest
```

## Code formatting

Additionally, this project uses [ruff](https://beta.ruff.rs/docs/)
and [djhtml](https://github.com/rtts/djhtml) for code formatting and linting:

* `ruff check .` (lint with ruff)
* `ruff format .` (auto-format with ruff)
* `git ls-files '*.html' | xargs djhtml` (auto-format templates with djhtml)

ruff has in-built functionality to fix common linting errors. Use the `--fix`
option to do this.

Ruff is automatically called as part of pytest in this project.

A pre-commit hook is defined in the project to run it automatically before each
commit. See the [pre-commit docs](https://pre-commit.com/#quick-start) for more
information, or simply run the below command to setup:

```shell
pre-commit install
```

## Database setup

Create a Postgres database as detailed [below](#setting-up-postgresql), then:

```shell
python manage.py migrate
python manage.py import_parties
python manage.py import_ballots
python manage.py import_people
```

If you want election results, you'll also need to import them:

```shell
python manage.py import_ballots --current
```

If you don't want to install Redis for some reason (like e.g. laziness) you can
override
the cache backend with a file at `./wcivf/settings/local.py` with the following:

```python

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}
```

## Setting up PostgreSQL

WhoCanIVoteFor uses PostgreSQL. To set this up locally, first install the
packages:

```shell
sudo apt-get install postgresql
```

Start the PostgreSQL server with:

    /etc/init.d/postgresql start

Then create, for example, a `wcivf` user:

```shell
sudo -u postgres createuser -P wcivf
```

Set the password to, for example, `wcivf`. Then create the database, owned by
the `wcivf` user:

```shell
sudo -u postgres createdb -O wcivf wcivf
```

Then, create a file `wcivf/settings/local.py` with the following contents,
assuming you used the same username, password and database name as above:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'wcivf',
        'USER': 'wcivf',
        'PASSWORD': 'wcivf',
        'HOST': 'localhost',
        'PORT': '',
    }
}
```

See the local.example.py file for other suggested settings to use for local
development.


# Test Feedback Form changes to Slack Webhooks

You will need access to incoming webhooks page in the DC Slack account.

Once you have access, create a new webhook and select `slackbot` as the channel.
Add that URL to your `local.py`:

```python
SLACK_FEEDBACK_WEBHOOK_URL = "URL"
```

Then, have your local install post to your channel in Slack.

Complete the feedback form on localhost, then run the management
command `manage.py batch_feedback_to_slack --hours-ago=1`

Feedback should appear in your Slack channel.

# Update Welsh Translations

To add new strings into the translation files, run:

```shell
make makemessages
```

Once translated, run:

```shell
make compilemessages`
```

If you're just filling in blanks for Welsh translations that already exist, you
can skip the `makemessages` step and just run `make compilemessages`.
