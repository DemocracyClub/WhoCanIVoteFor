import json

import django
import sentry_sdk
from django.core.management import call_command


def handler(event, context):
    """
    Parameters
    ----------
    event: dict, required
        Either an SQS event (when invoked via the SQS event source mapping) or
        a direct invocation payload. SQS events wrap the command payload in
        Records[0].body as a JSON string.

        SQS event doc: https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
    dict with statusCode and body
    """
    if "Records" in event:
        event = json.loads(event["Records"][0]["body"])

    cmd = event["command"]
    args = event.get("args", [])

    sentry_sdk.set_context("event", event)

    django.setup()

    print(f"Calling {cmd} with args {args}")
    call_command(cmd, *args)

    arg_str = " ".join(args)
    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": f"{cmd} {arg_str} completed",
            }
        ),
    }
