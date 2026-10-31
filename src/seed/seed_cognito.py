"""
seed_cognito.py — Create Cognito adjuster accounts for ClaimSense AI
=====================================================================
Creates 5 adjuster accounts in the Cognito User Pool, matching the
assigned_adjuster field values in the claims seed data.

Users are admin-confirmed so no email verification step is needed.
Passwords are set as permanent (no forced reset) for dev convenience.

Stakeholder alignment
---------------------
  bob.reyes     → Bob Reyes, Senior Licensed Adjuster (stakeholder map)
  alice, carol,
  david, eve    → daily adjuster accounts (from claims CSV)

Usage
-----
  # After `sam deploy` — get USER_POOL_ID from stack outputs
  USER_POOL_ID=us-east-1_XXXXXXXX python src/seed/seed_cognito.py

  # Or pass ENV to look it up automatically from CloudFormation
  ENV=dev python src/seed/seed_cognito.py

Environment variables
---------------------
  USER_POOL_ID        Cognito User Pool ID (required if ENV not set)
  ENV                 Deployment stage — used to look up the pool from CF outputs
  AWS_DEFAULT_REGION  us-east-1 (default)
  TEMP_PASSWORD       Override the default seed password (optional)
"""

import os
import sys

import boto3
from botocore.exceptions import ClientError

REGION     = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
ENV        = os.environ.get("ENV", "dev")
# Default password meets the pool policy: 12+ chars, upper, lower, digit
PASSWORD   = os.environ.get("TEMP_PASSWORD", "AutoSure2024!")

# ---------------------------------------------------------------------------
# Adjuster accounts
#
# email is the Cognito username (pool uses email as username attribute).
# role is stored as a custom attribute on the pool schema (see template.yaml).
# ---------------------------------------------------------------------------

ADJUSTERS = [
    {
        "email":      "bob.reyes@autosure.com",
        "given_name": "Bob",
        "family_name": "Reyes",
        "role":       "senior_adjuster",    # stakeholder map: Bob reviews every recommendation
        "adjuster_id": "bob",               # matches assigned_adjuster in claims CSV
    },
    {
        "email":      "alice.martinez@autosure.com",
        "given_name": "Alice",
        "family_name": "Martinez",
        "role":       "adjuster",
        "adjuster_id": "alice",
    },
    {
        "email":      "carol.chen@autosure.com",
        "given_name": "Carol",
        "family_name": "Chen",
        "role":       "adjuster",
        "adjuster_id": "carol",
    },
    {
        "email":      "david.okafor@autosure.com",
        "given_name": "David",
        "family_name": "Okafor",
        "role":       "adjuster",
        "adjuster_id": "david",
    },
    {
        "email":      "eve.thompson@autosure.com",
        "given_name": "Eve",
        "family_name": "Thompson",
        "role":       "adjuster",
        "adjuster_id": "eve",
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_user_pool_id() -> str:
    pool_id = os.environ.get("USER_POOL_ID", "")
    if pool_id:
        return pool_id

    # Fall back: look it up from the CloudFormation stack outputs
    print(f"USER_POOL_ID not set — looking up from stack claimsense-{ENV} ...")
    cf = boto3.client("cloudformation", region_name=REGION)
    try:
        resp    = cf.describe_stacks(StackName=f"claimsense-{ENV}")
        outputs = resp["Stacks"][0].get("Outputs", [])
        for o in outputs:
            if o["OutputKey"] == "UserPoolId":
                return o["OutputValue"]
    except ClientError as e:
        pass

    print("ERROR: Could not determine USER_POOL_ID.")
    print("  Set USER_POOL_ID=<id> or deploy the stack first with `sam deploy`.")
    sys.exit(1)


def create_user(client, pool_id: str, adjuster: dict) -> str:
    """
    Create or update a Cognito user.
    Returns "created", "updated", or "skipped" (already exists, no change).
    """
    email = adjuster["email"]

    try:
        client.admin_create_user(
            UserPoolId=pool_id,
            Username=email,
            UserAttributes=[
                {"Name": "email",             "Value": email},
                {"Name": "email_verified",    "Value": "true"},
                {"Name": "given_name",        "Value": adjuster["given_name"]},
                {"Name": "family_name",       "Value": adjuster["family_name"]},
                {"Name": "custom:role",       "Value": adjuster["role"]},
                {"Name": "custom:adjuster_id","Value": adjuster["adjuster_id"]},
            ],
            TemporaryPassword=PASSWORD,
            MessageAction="SUPPRESS",     # don't send a welcome email
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "UsernameExistsException":
            return "skipped"
        raise

    # Set password as permanent so no forced-reset on first login (dev convenience)
    client.admin_set_user_password(
        UserPoolId=pool_id,
        Username=email,
        Password=PASSWORD,
        Permanent=True,
    )

    return "created"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    pool_id = get_user_pool_id()
    print(f"User Pool: {pool_id}  (region: {REGION})")
    print()

    client  = boto3.client("cognito-idp", region_name=REGION)
    created = skipped = errors = 0

    for adjuster in ADJUSTERS:
        email = adjuster["email"]
        try:
            status = create_user(client, pool_id, adjuster)
            icon   = "+" if status == "created" else "·"
            print(f"  {icon} {status:8}  {email:40}  role={adjuster['role']}")
            if status == "created":
                created += 1
            else:
                skipped += 1
        except ClientError as e:
            print(f"  ! ERROR    {email}  — {e.response['Error']['Message']}")
            errors += 1

    print()
    print(f"Done.  created={created}  skipped={skipped}  errors={errors}")

    if errors:
        sys.exit(1)

    print()
    print("Adjuster accounts:")
    for a in ADJUSTERS:
        print(f"  {a['email']:40}  password: {PASSWORD}")


if __name__ == "__main__":
    main()
