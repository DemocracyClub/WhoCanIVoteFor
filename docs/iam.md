## IAM Entities

In the AWS console, go to IAM and follow the instructions below to create the required entities. When creating these (and any other servies) via the AWS console it is recommended that you add the following tag:
- `CreatedVia`: `Console`

This will let you identify resources created via the AWS console in future.

### Policies

#### CodeDeploy-EC2-Permissions

Create an IAM Policy named `CodeDeploy-EC2-Permissions`. This policy will alter be attached to the IAM instance profile that the EC2 instances use.

Set its Policy document as follows. Make sure the logging ARN matches the 
environment:

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "s3:Get*",
                "s3:List*"
            ],
            "Effect": "Allow",
            "Resource": "arn:aws:s3:::aws-codedeploy-eu-west-2/*"
        },
        {
            "Action": [
                "lambda:InvokeFunction"
            ],
            "Effect": "Allow",
            "Resource": "arn:aws:lambda:eu-west-2:985364114241:function:ingest-dc-postcode-searches-development"
        }
    ]
}
```

#### CodeDeployAndRelatedServices

Create an IAM policy named `CodeDeployAndRelatedServices`. This policy will later be attached to the CircleCI user to allow it to create deployments with CodeDeploy.

Set its Policy document as follows: **FIXME: limit the initial resources section by removing wildcard usage**

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "autoscaling:*",
                "codedeploy:*",
                "ec2:*",
                "elasticloadbalancing:*",
                "iam:AddRoleToInstanceProfile",
                "iam:AttachRolePolicy",
                "iam:CreateInstanceProfile",
                "iam:CreateRole",
                "iam:DeleteInstanceProfile",
                "iam:DeleteRole",
                "iam:DeleteRolePolicy",
                "iam:GetInstanceProfile",
                "iam:GetRole",
                "iam:GetRolePolicy",
                "iam:ListInstanceProfilesForRole",
                "iam:ListRolePolicies",
                "iam:ListRoles",
                "iam:PassRole",
                "iam:PutRolePolicy",
                "iam:RemoveRoleFromInstanceProfile",
                "s3:*",
                "ssm:*"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": "iam:CreateServiceLinkedRole",
            "Resource": "arn:aws:iam::*:role/aws-service-role/elasticloadbalancing.amazonaws.com/AWSServiceRoleForElasticLoadBalancing*",
            "Condition": {
                "StringLike": {
                    "iam:AWSServiceName": "elasticloadbalancing.amazonaws.com"
                }
            }
        },
        {
            "Effect": "Allow",
            "Action": [
                "iam:AttachRolePolicy",
                "iam:PutRolePolicy",
                "iam:CreateServiceLinkedRole"
            ],
            "Resource": [
                "arn:aws:iam::*:role/aws-service-role/elasticloadbalancing.amazonaws.com/AWSServiceRoleForElasticLoadBalancing*",
                "arn:aws:iam::*:role/aws-service-role/autoscaling.amazonaws.com/AWSServiceRoleForAutoScaling*"
            ]
        }
    ]
}
```

#### CodeDeployLaunchTemplatePermissions

Create a Policy with the name `CodeDeployLaunchTemplatePermissions`. This policy adds additional permissions required when using Code Deploy with Launch Template ([more information can be found here](https://docs.aws.amazon.com/codedeploy/latest/userguide/troubleshooting-auto-scaling.html#troubleshooting-auto-scaling-general)). It will be attached to a service role that will be created later (details below).

Set the policy document to:

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:RunInstances",
                "ec2:CreateTags",
                "iam:PassRole"
            ],
            "Resource": "*"
        }
    ]
}
```

#### WCIVFDeployer

Create a Policy with the name `WCIVFDeployer`. The policy will be attached to the CircleCI IAM user, to allow it to deploy the Lambda function and events.

Set its Policy document to:
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "apigateway:DELETE",
                "apigateway:GET",
                "apigateway:PATCH",
                "apigateway:POST",
                "apigateway:PUT",
                "cloudformation:CreateChangeSet",
                "cloudformation:DescribeChangeSet",
                "cloudformation:DescribeStackEvents",
                "cloudformation:DescribeStacks",
                "cloudformation:ExecuteChangeSet",
                "cloudformation:GetTemplateSummary",
                "events:*",
                "lambda:AddPermission",
                "lambda:CreateAlias",
                "lambda:CreateEventSourceMapping",
                "lambda:CreateFunction",
                "lambda:DeleteAlias",
                "lambda:DeleteEventSourceMapping",
                "lambda:DeleteFunction",
                "lambda:GetEventSourceMapping",
                "lambda:GetFunction",
                "lambda:GetFunctionConfiguration",
                "lambda:GetLayerVersion",
                "lambda:InvokeFunction",
                "lambda:ListEventSourceMappings",
                "lambda:ListTags",
                "lambda:ListVersionsByFunction",
                "lambda:PublishLayerVersion",
                "lambda:PublishVersion",
                "lambda:RemovePermission",
                "lambda:TagResource",
                "lambda:UntagResource",
                "lambda:UpdateAlias",
                "lambda:UpdateFunctionCode",
                "lambda:UpdateFunctionConfiguration",
                "lambda:UpdateEventSourceMapping",
                "logs:CreateLogGroup",
                "logs:PutRetentionPolicy",
                "s3:AbortMultipartUpload",
                "s3:GetObject",
                "s3:ListBucketMultipartUploads",
                "s3:ListMultipartUploadParts",
                "s3:PutObject",
                "s3:PutObjectAcl",
                "s3:PutObjectTagging",
                "sqs:AddPermission",
                "sqs:CreateQueue",
                "sqs:DeleteQueue",
                "sqs:GetQueueAttributes",
                "sqs:GetQueueUrl",
                "sqs:ListQueueTags",
                "sqs:RemovePermission",
                "sqs:SetQueueAttributes",
                "sqs:TagQueue",
                "sqs:UntagQueue"
            ],
            "Resource": [
                "arn:aws:apigateway:eu-west-2:*::/restapis",
                "arn:aws:apigateway:eu-west-2:*::/restapis/*",
                "arn:aws:cloudformation:eu-west-2:*:changeSet/samcli-deploy*/*",
                "arn:aws:cloudformation:eu-west-2:*:stack/WCIVFApp*/*",
                "arn:aws:cloudformation:eu-west-2:aws:transform/Serverless-2016-10-31",
                "arn:aws:events:eu-west-2:*:rule/*",
                "arn:aws:lambda:eu-west-2:*:function:WCIVFControllerFunction*",
                "arn:aws:lambda:eu-west-2:*:layer:DependenciesLayer",
                "arn:aws:lambda:eu-west-2:*:layer:DependenciesLayer:*",
                "arn:aws:logs:eu-west-2:*:log-group:/aws/lambda/WCIVFApp*",
                "arn:aws:sqs:eu-west-2:*:wcivf-jobs.fifo",
                "arn:aws:sqs:eu-west-2:*:wcivf-jobs-dlq.fifo",
                "arn:aws:s3:::wcivf-deployment-artifacts-*",
                "arn:aws:s3:::wcivf-deployment-artifacts-*/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": "iam:PassRole",
            "Resource": [
                "arn:aws:iam::*:role/WCIVFLambdaExecutionRole"
            ],
            "Condition": {
                "StringEquals": {
                    "iam:PassedToService": "lambda.amazonaws.com"
                }
            }
        }
    ]
}
```

Note the S3 value resource includes part of the bucket name `wcivf-deployment-artifacts-*`. Instructions on the creation of this S3 bucket are elsewhere in this documentation, but if you name the bucket something else, you will need to update this line in the `WCIVFDeployer` policy document accordingly.


### Roles

In the AWS console, go to IAM and create the following Roles:

#### CodeDeploy-EC2-Instance-Profile

Create a Role with the name `CodeDeploy-EC2-Instance-Profile`. During creation:

- Select the use-case creation shortcut for EC2
- Attach the `CodeDeploy-EC2-Permissions` policy created earlier
- Attach the AWS managed policy `AmazonSSMReadOnlyAccess`
- Attach the AWS managed policy `CloudWatchAgentServerPolicy`

After creation, ensure the trust relationship looks like this:
```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

####  CodeDeployServiceRole

Create a Role with the name `CodeDeployServiceRole`. During creation:

- Select the use-case creation shortcut for CodeDeploy
- Attach the `CodeDeployLaunchTemplatePermissions` policy created earlier
- Attach the AWS managed policy `AWSCodeDeployRole`.

For more information about this role, [see the AWS documentation](https://docs.aws.amazon.com/codedeploy/latest/userguide/getting-started-create-service-role.html).

After creation, ensure the trust relationship looks like this:
```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "codedeploy.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

#### WCIVFLambdaExecutionRole

Create a Role with the name `WCIVFLambdaExecutionRole`. During creation:

- Select the use-case creation shortcut for Lambda
- Attach the AWS-managed policy: `AWSLambdaBasicExecutionRole`

After creation, ensure the trust relationship looks like this:

```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### User Groups

In the AWS console, go to IAM and create the following User Group:

#### WCIVFDeployerGroup

During creation, attach the following policies created earlier:

- `WCIVFDeployer`
- `CodeDeployAndRelatedServices`

### Users

In the AWS console, go to IAM and create the following User:

#### CircleCI

During creation:

- Select "Programmatic access" only.
- Add them to the `WCIVFDeployerGroup` created earlier

After creation, copy the generated access key ID and secret access key, and paste them inside an appropriately-named CircleCI "Context", with each value stored under its relevant standard [AWS environment variable name](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html).

**Make very, *very* sure that you capture the key ID and secret precisely! Ensure that, when you paste it into the CircleCI UI, you don't accidentally insert any leading or trailing whitespace, and that you've copied the entire string each time - even if the string contains word-break characters that stop your browser from selecting the whole string!**
