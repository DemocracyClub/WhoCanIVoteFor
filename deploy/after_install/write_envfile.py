#!/var/www/wcivf/code/.venv/bin/python

import json
import string
from pathlib import Path
from typing import Dict, List

import boto3

client = boto3.client("ssm", region_name="eu-west-2")


def get_parameter_store_names() -> List:
    response = client.describe_parameters(MaxResults=50)
    return [param["Name"] for param in response["Parameters"]]


def get_parameter_store_vars() -> Dict:
    parameters = {}
    names = get_parameter_store_names()
    for name in names:
        if name[0] not in string.ascii_uppercase:
            # Env vars should be capitalised.
            continue
        response = client.get_parameter(Name=name)
        key = response["Parameter"]["Name"]
        value = response["Parameter"]["Value"]
        parameters[key] = value

    return parameters


def get_deploy_vars() -> Dict:
    with open(Path(__file__).parents[1] / "deploy-env-vars.json") as f:
        return json.loads(f.read())


def write_parameters_to_envfile() -> None:
    deploy_env_vars = get_deploy_vars()
    parameter_store_vars = get_parameter_store_vars()

    # Defer to parameter store vars over values stored in repo.
    deploy_env_vars.update(parameter_store_vars)

    with open(deploy_env_vars["ENV_FILE_PATH"], "w") as f:
        for key, value in deploy_env_vars.items():
            f.write(f"{key}='{value}'\n")


if __name__ == "__main__":
    write_parameters_to_envfile()
