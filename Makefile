export DJANGO_SETTINGS_MODULE?=wcivf.settings.lambda
export DC_ENVIRONMENT?=development
export AWS_DEFAULT_REGION?=eu-west-2

.PHONY: all
make all: build clean

.PHONY: build
build:
	sam build -t ./sam-template.yaml

.PHONY: clean
clean: ## Delete any unneeded static asset files and git-restore the rendered API documentation file
	rm -rf .aws-sam/build/WCIVFControllerFunction/wcivf/static/booklets/
	rm -rf .aws-sam/build/WCIVFControllerFunction/wcivf/assets/booklets/
	rm -rf .aws-sam/build/WCIVFControllerFunction/wcivf/assets/images/
	rm -rf .aws-sam/build/WCIVFControllerFunction/wcivf/static/images/
	rm -rf .aws-sam/build/WCIVFControllerFunction/wcivf/media/
	rm -rf .aws-sam/build/WCIVFControllerFunction/docs/
	rm -f .aws-sam/build/WCIVFControllerFunction/wcivf/settings/local.py
	rm -f .aws-sam/build/WCIVFControllerFunction/results_app.dot
	rm -f .aws-sam/build/WCIVFControllerFunction/results_app.png
	rm -f .aws-sam/build/WCIVFControllerFunction/transifex.yml
	rm -f .aws-sam/build/WCIVFControllerFunction/local.example

.PHONY: lambda-migrate
lambda-migrate:  ## Invoke lambda to migrate the database
	output=$$(aws lambda invoke \
		--function-name WCIVFControllerFunction \
		--payload '{ "command": "migrate", "args": ["--no-input"] }' \
		--cli-binary-format raw-in-base64-out \
		--output json \
		/dev/stdout); \
	echo "$$output"; \
	echo "$$output" | grep -q '"FunctionError"' && exit 1 || exit 0

lib/dc_utils:
	mkdir -p lib
	ln -s `python -c 'import dc_utils; print(dc_utils.__path__[0])'` lib/dc_utils

.PHONY: makemessages
makemessages: lib/dc_utils
	${VIRTUAL_ENV}/bin/python manage.py makemessages -l cy --ignore='env*'

.PHONY: compilemessages
compilemessages:
	${VIRTUAL_ENV}/bin/python manage.py compilemessages --ignore='env*'


build-WCIVFControllerFunction:
	uv venv
	uv export --no-hashes --no-dev --group deploy > "$(ARTIFACTS_DIR)/requirements.txt"
	uv pip install --upgrade -r "$(ARTIFACTS_DIR)/requirements.txt" --target "$(ARTIFACTS_DIR)"
	cp -r wcivf $(ARTIFACTS_DIR)
	cp manage.py $(ARTIFACTS_DIR)
