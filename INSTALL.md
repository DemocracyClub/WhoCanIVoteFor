## Installation requirements on ubuntu

WCIVF requires Python 3.12

To install:

    sudo apt-get install python3-dev libpq-dev libjpeg-dev redis-server libtidy-dev
    pip install -r requirements/local.txt


## Installation requirements on macOS

Use homebrew to install the following dependencies:

    brew install postgresql jpeg

If you want to use redis, this can also be installed with homebrew:
    
    brew install redis

Pyenv is recommended to install python versions. You can find installation instructions for pyenv [here](https://github.com/pyenv/pyenv#installation) - installation via homebrew is recommended.

The python version that we are using for this project is specified in the `.python-version` file in the root of the directory.You can install this version with:

    pyenv install 3.12

The presence of a `.python-version` file means that pyenv will activate this version whenever in this directory. This means that whenever running a `python` command, the version specified in `.python-version` is used. You can check this with the below command:

    python --version

The output should match the version in `.python-version`. If the version is not installed, pyenv will output an error stating the version is not installed.

If there is no `.python-version` file you can use the following command to create one and activate that version for this project:

    pyenv local 3.12

When you are happy that you are using the correct python version, you are ready to create a [virtual environment](https://docs.python.org/3/tutorial/venv.html) with the command:

    python -m venv env

This will create a virtual environment in the directory `env`. You can then activate the virtual environment with:

    source env/bin/activate

Check that the virtual environment is using the correct python version:

    python --version

The output should match the python version set in the `.python-version`. If it does not, something has gone wrong - delete the `env` directory and retry the steps to set the python version and create the virtual environment.

You can now install the project dependencies in to your activated virtualenv:

    pip install -r requirements/local.txt

You'll also need to make sure that you're set up with tidy. 
First install cmake:
```
# Mac
brew install cmake

# Linux
sudo apt-get install cmake
```
Once cmake is in place, follow the build steps in the tidy repository [here](https://github.com/htacg/tidy-html5).

Check that your env has correctly installed and project is working by running the tests:

    pytest

## Code formatting

Additionally, this project uses [ruff](https://beta.ruff.rs/docs/) for code formatting and linting. You can run it with:

    ruff format .
    ruff check .

ruff has in-built functionality to fix common linting errors. Use the `--fix` option to do this.

Ruff is automatically called as part of pytest in this project.

A pre-commit hook is defined in the project to run it automatically before each commit. See the [pre-commit docs](https://pre-commit.com/#quick-start) for more information, or simply run the below command to setup:

    pre-commit install


## Database setup

Create a Postgres database as detailed [below](#setting-up-postgresql), then:

    python manage.py migrate
    python manage.py import_parties
    python manage.py import_ballots
    python manage.py import_people

If you want election results, you'll also need to import them:

    python manage.py import_ballots --current

If you don't want to install Redis for some reason (like e.g. laziness) you can override
the cache backend with a file at `./wcivf/settings/local.py` with the following:

    CACHES = {
        'default': {
           'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }


## Setting up PostgreSQL

WhoCanIVoteFor uses PostgreSQL. To set this up locally, first install the packages:

    sudo apt-get install postgresql

Then create, for example, a `wcivf` user:

    sudo -u postgres createuser -P wcivf

Set the password to, for example, `wcivf`. Then create the database, owned by the `wcivf` user:

    sudo -u postgres createdb -O wcivf wcivf

Then, create a file `wcivf/settings/local.py` with the following contents, assuming you used the same username, password and database name as above:

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'wcivf',
            'USER': 'wcivf',
            'PASSWORD': 'wcivf',
            'HOST': 'localhost',
            'PORT': '',
        }
    }

See the local.example.py file for other suggested settings to use for local development.

## Creating inline CSS

To regenerate the static files:

    manage.py collectstatic

The CSS for this project is inlined in the base template for performance reasons.

This is created using [`critical`](https://github.com/addyosmani/critical), and can be re-created by running

```
curl localhost:8000 | critical --base wcivf -m > wcivf/templates/_compressed_css.html
```

# Test Feedback Form changes to Slack Webhooks
You will need access to incoming webhooks page in the DC Slack account.

Once you have access, create a new webhook and select `slackbot` as the channel. 
Add that URL to your `local.py`: 

`SLACK_FEEDBACK_WEBHOOK_URL = "URL"`

Then, have your local install post to your channel in Slack.

Complete the feedback form on localhost, then run the management command `manage.py batch_feedback_to_slack --hours-ago=1`

Feedback should appear in your Slack channel.

# Update Welsh Translations

To add new strings into the translation files, run:

`make makemessages`

Once translated, run:

`make compilemessages`

If you're just filling in blanks for Welsh translations that already exist, you can skip the `makemessages` step and just run `make compilemessages`.
