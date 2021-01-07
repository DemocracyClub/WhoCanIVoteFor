## Installation requirements on ubuntu

WCIVF requires Python 3.

To install:

    sudo apt-get install python3-dev libpq-dev libjpeg-dev redis-server
    pip install -r requirements/local.txt


## Installation requirements on macOS

Use homebrew to install the following dependencies:

    brew install postgresql libjpeg-dev postgis

Pyenv is recommended to install python versions. You can find installation instructions for pyenv [here](https://github.com/pyenv/pyenv#installation) - installation via homebrew is recommended. You can then install python 3 with:

    pyenv install 3.6.12

If using pyenv, after installation use the command `pyenv local 3.6.12` to set this version for the project locally. This will create a `.python-version` file with the specified python version.

You can then create a [virtual environment](https://docs.python.org/3/tutorial/venv.html) with the command:

    python -m venv env

This will create a virtual environment in the directory `env`. You can then activate the virtual environment with:

    source env/bin/activate

Check that the virtual environment is using the correct python version:

    python --version

The output should match the python version set in the .python-version file. If it does not, something has gone wrong - delete the `env` directory and retry the steps to set the python version and create the virtual environment.

You can now install the project dependencies in to your activated virtualenv:

    pip install -r requirements/local.txt


## Database setup

Create a Postgres database as detailed [below](#setting-up-postgresql-and-postgis), then:

    python manage.py migrate
    python manage.py import_parties
    python manage.py import_ballots
    python manage.py import_people

If you don't want to install Redis for some reason (like e.g. laziness) you can override
the cache backend with a file at `./wcivf/settings/local.py` with the following:

    CACHES = {
        'default': {
           'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }


## Setting up PostgreSQL and PostGIS

By default WhoCanIVoteFor uses PostgreSQL with the PostGIS extension. To set this up locally, first install the packages:

    sudo apt-get install postgresql postgis

Then create, for example, a `wcivf` user:

    sudo -u postgres createuser -P wcivf

Set the password to, for example, `wcivf`. Then create the database, owned by the `wcivf` user:

    sudo -u postgres createdb -O wcivf wcivf

Finally, add the PostGIS extension to the database:

    sudo -u postgres psql -d wcivf -c "CREATE EXTENSION postgis;"

Then, create a file `wcivf/settings/local.py` with the following contents, assuming you used the same username, password and database name as above:

    DATABASES = {
        'default': {
            'ENGINE': 'django.contrib.gis.db.backends.postgis',
            'NAME': 'wcivf',
            'USER': 'wcivf',
            'PASSWORD': 'wcivf',
            'HOST': 'localhost',
            'PORT': '',
        }
    }


## Creating inline CSS

To regenerate the static files:

    manage.py collectstatic

The CSS for this project is inlined in the base template for performance reasons.

This is created using [`critical`](https://github.com/addyosmani/critical), and can be re-created by running

```
curl localhost:8000 | critical --base wcivf -m > wcivf/templates/_compressed_css.html
```
