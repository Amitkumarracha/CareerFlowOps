"""Render account-specific IAM documents locally; never calls AWS."""

import argparse
import json
import re
from pathlib import Path


def render(account: str, region: str, bucket: str, output: Path) -> None:
    if not re.fullmatch(r"\d{12}", account):
        raise ValueError("Use a 12-digit AWS account ID")
    if not re.fullmatch(r"[a-z]{2}-[a-z]+-\d", region):
        raise ValueError("Use a standard AWS region, such as ap-south-1")
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket):
        raise ValueError("Use a valid S3 bucket name")
    root = Path(__file__).parent
    output.mkdir(parents=True, exist_ok=True)
    for source, target in [
        ("oidc-trust-policy.json", "github-trust.json"),
        ("ecr-publish-policy.json", "github-ecr.json"),
    ]:
        content = (
            (root / source)
            .read_text()
            .replace("ACCOUNT_ID", account)
            .replace("OWNER/REPOSITORY", "Arjun-Reddy-I/CareerFlowOps")
            .replace("ap-south-1", region)
        )
        (output / target).write_text(content)
    documents = {
        "ec2-trust.json": {
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "ec2.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ]
        },
        "ec2-pull.json": {
            "Statement": [
                {"Effect": "Allow", "Action": "ecr:GetAuthorizationToken", "Resource": "*"},
                {
                    "Effect": "Allow",
                    "Action": [
                        "ecr:BatchGetImage",
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:BatchCheckLayerAvailability",
                    ],
                    "Resource": [
                        f"arn:aws:ecr:{region}:{account}:repository/careerflowops-{name}"
                        for name in ["api", "web"]
                    ],
                },
                {
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": f"arn:aws:s3:::{bucket}",
                    "Condition": {
                        "StringLike": {"s3:prefix": ["careerflowops", "careerflowops/*"]}
                    },
                },
                {
                    "Effect": "Allow",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket}/careerflowops/*",
                },
            ]
        },
        "trainer-storage.json": {
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": f"arn:aws:s3:::{bucket}",
                    "Condition": {
                        "StringLike": {"s3:prefix": ["careerflowops", "careerflowops/*"]}
                    },
                },
                {
                    "Effect": "Allow",
                    "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
                    "Resource": f"arn:aws:s3:::{bucket}/careerflowops/*",
                },
            ]
        },
        "github-deploy.json": {
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "ssm:SendCommand",
                    "Resource": f"arn:aws:ssm:{region}::document/AWS-RunShellScript",
                },
                {
                    "Effect": "Allow",
                    "Action": "ssm:SendCommand",
                    "Resource": f"arn:aws:ec2:{region}:{account}:instance/*",
                    "Condition": {"StringEquals": {"ssm:resourceTag/Name": "CareerFlowOps"}},
                },
                {
                    "Effect": "Allow",
                    "Action": "ssm:GetCommandInvocation",
                    "Resource": "*",
                    "Condition": {"StringEquals": {"aws:RequestedRegion": region}},
                },
            ]
        },
    }
    for name, document in documents.items():
        document["Version"] = "2012-10-17"
        (output / name).write_text(json.dumps(document, indent=2) + "\n")
    print(f"Rendered IAM documents in {output}. No AWS calls were made.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account", required=True)
    parser.add_argument("--region", default="ap-south-1")
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--output", type=Path, default=Path(".aws-policies"))
    args = parser.parse_args()
    render(args.account, args.region, args.bucket, args.output)


if __name__ == "__main__":
    main()
