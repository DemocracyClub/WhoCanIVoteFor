import os
import time

import boto3

session = boto3.Session()


def create_deployment():
    """
    Create a new deployment and return deploy ID
    """
    client = session.client("codedeploy")
    other_deploys = None
    while other_deploys is not False:
        active_deployments = client.list_deployments(
            includeOnlyStatuses=["Created", "Queued", "InProgress"],
            applicationName="WCIVFCodeDeploy",
            deploymentGroupName="WCIVFDefaultDeploymentGroup",
        )["deployments"]
        other_deploys = bool(active_deployments)
        if other_deploys:
            WAIT_SECONDS = 30
            print(
                f"Another deploy ({active_deployments}) is blocking this one, waiting {WAIT_SECONDS} seconds"
            )
            time.sleep(WAIT_SECONDS)
    deployment = client.create_deployment(
        applicationName="WCIVFCodeDeploy",
        deploymentGroupName="WCIVFDefaultDeploymentGroup",
        ignoreApplicationStopFailures=True,
        revision={
            "revisionType": "GitHub",
            "gitHubLocation": {
                "repository": "DemocracyClub/WhoCanIVoteFor",
                "commitId": os.environ.get("COMMIT_SHA"),
            },
        },
    )
    return deployment["deploymentId"]


def delete_asg(asg_name):
    """
    Deletes an AutoScalingGroup and all associated instances
    """
    client = session.client("autoscaling")
    return client.delete_auto_scaling_group(
        AutoScalingGroupName=asg_name, ForceDelete=True
    )


def check_deployment(deployment_id):
    """
    Checks the status of the deploy every 5 seconds,
    returns a success or error code
    """
    client = session.client("codedeploy")
    deployment = client.get_deployment(deploymentId=deployment_id)[
        "deploymentInfo"
    ]

    if deployment["status"] == "Succeeded":
        print("SUCCESS")
        exit(0)

    if deployment["status"] in ["Failed", "Stopped"]:
        print("FAIL")
        print(deployment["errorInformation"])
        # delete the ASG that was created during the failed deployment
        delete_asg(
            asg_name=deployment["targetInstances"]["autoScalingGroups"][0]
        )
        exit(1)

    print(deployment["status"])
    time.sleep(10)
    check_deployment(deployment_id=deployment_id)


def main():
    deployment_id = create_deployment()
    check_deployment(deployment_id=deployment_id)


if __name__ == "__main__":
    main()
