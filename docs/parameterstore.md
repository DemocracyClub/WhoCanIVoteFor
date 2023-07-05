## Parameter Store

AWS parameter store is used to store secrets and values that we then use to expose as environment variables to be used in the code. You should be able to review these in the dev/staging environment as a reference. Below is a list of the required parameters that need to be set:

- `DC_ENVIRONMENT` e.g. `production`, `staging`, `development`
- `EMAIL_SIGNUP_API_KEY`
- `LOGGER_DB_HOST`
- `LOGGER_DB_PASSWORD`
- `RDS_DB_NAME`
- `RDS_DB_PASSWORD`
- `RDS_HOST`
- `SECRET_KEY` - should be a long and random string. [A handy way of using Django to generate one can be found in this blog post](https://humberto.io/blog/tldr-generate-django-secret-key/).
- `SENTRY_DSN`
- `SLACK_FEEDBACK_WEBHOOK_URL`
- `WDIV_API_KEY`
- `FIREHOSE_ACCOUNT_ARN`
- `AKISMET_API_KEY`
