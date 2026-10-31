"""
ingest.py — Upload policy manual to S3 and trigger Bedrock ingestion
=====================================================================
Run this once after `sam deploy` to populate the Knowledge Base.
Re-run whenever the policy manual is updated.

What it does:
  1. Uploads AutoSure_Policy_Manual_CLS-001-012.pdf to S3
  2. Starts a Bedrock ingestion job (chunks + embeds the PDF)
  3. Polls until the job completes or fails
  4. Prints a summary

Usage
-----
  # After sam deploy -- get these values from the deploy outputs
  export KNOWLEDGE_BASE_ID=<kb-id>
  export DOCS_BUCKET=claimsense-docs-<account-id>
  export STAGE=dev
  export AWS_DEFAULT_REGION=us-east-1

  python src/retrieval/ingest.py

  # Or via Makefile:
  make ingest ENV=dev

Environment variables
---------------------
  KNOWLEDGE_BASE_ID   from sam deploy outputs (KnowledgeBaseId)
  DOCS_BUCKET         from sam deploy outputs (PolicyDocsBucketName)
  STAGE               dev | staging | prod  (default: dev)
  AWS_DEFAULT_REGION  us-east-1
"""

import os
import sys
import time
from pathlib import Path

import boto3

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID", "")
DOCS_BUCKET       = os.environ.get("DOCS_BUCKET", "")
STAGE             = os.environ.get("STAGE", "dev")
REGION            = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

POLICY_MANUAL_PATH = (
    Path(__file__).parent.parent.parent
    / "ClaimsData"
    / "synthetic_documents"
    / "AutoSure_Policy_Manual_CLS-001-012.pdf"
)

# S3 key follows the prefix the Knowledge Base data source watches
S3_KEY = f"{STAGE}/policy-manual/AutoSure_Policy_Manual_CLS-001-012.pdf"

# How long to wait between status polls (seconds)
POLL_INTERVAL = 10


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate():
    errors = []
    if not KNOWLEDGE_BASE_ID:
        errors.append("KNOWLEDGE_BASE_ID is not set. Get it from `sam deploy` outputs.")
    if not DOCS_BUCKET:
        errors.append("DOCS_BUCKET is not set. Get it from `sam deploy` outputs.")
    if not POLICY_MANUAL_PATH.exists():
        errors.append(
            f"Policy manual not found at {POLICY_MANUAL_PATH}. "
            "Ensure ClaimsData/synthetic_documents/ is present."
        )
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Step 1 — Upload PDF to S3
# ---------------------------------------------------------------------------

def upload_policy_manual():
    print(f"Uploading policy manual to s3://{DOCS_BUCKET}/{S3_KEY} ...")
    s3 = boto3.client("s3", region_name=REGION)

    s3.upload_file(
        Filename=str(POLICY_MANUAL_PATH),
        Bucket=DOCS_BUCKET,
        Key=S3_KEY,
        ExtraArgs={"ContentType": "application/pdf"},
    )
    print(f"  Upload complete.")
    return f"s3://{DOCS_BUCKET}/{S3_KEY}"


# ---------------------------------------------------------------------------
# Step 2 — Get the data source ID
#
# The Knowledge Base has one data source (the S3 prefix). We need its ID
# to start the ingestion job. We fetch it rather than hard-coding it.
# ---------------------------------------------------------------------------

def get_data_source_id() -> str:
    bedrock = boto3.client("bedrock-agent", region_name=REGION)
    response = bedrock.list_data_sources(knowledgeBaseId=KNOWLEDGE_BASE_ID)
    sources = response.get("dataSourceSummaries", [])

    if not sources:
        print("ERROR: No data sources found for this Knowledge Base.")
        sys.exit(1)

    # We only have one data source — the S3 bucket prefix
    return sources[0]["dataSourceId"]


# ---------------------------------------------------------------------------
# Step 3 — Start ingestion job
#
# Bedrock reads the S3 prefix, chunks the PDFs, embeds each chunk with
# Titan Embeddings, and stores the vectors in the managed vector store.
# ---------------------------------------------------------------------------

def start_ingestion(data_source_id: str) -> str:
    print(f"Starting Bedrock ingestion job ...")
    bedrock = boto3.client("bedrock-agent", region_name=REGION)

    response = bedrock.start_ingestion_job(
        knowledgeBaseId=KNOWLEDGE_BASE_ID,
        dataSourceId=data_source_id,
    )
    job_id = response["ingestionJob"]["ingestionJobId"]
    print(f"  Ingestion job started: {job_id}")
    return job_id


# ---------------------------------------------------------------------------
# Step 4 — Poll until complete
#
# Ingestion typically takes 30–120 seconds for a small PDF.
# Status values: STARTING → IN_PROGRESS → COMPLETE | FAILED
# ---------------------------------------------------------------------------

def wait_for_ingestion(data_source_id: str, job_id: str):
    bedrock = boto3.client("bedrock-agent", region_name=REGION)
    print(f"Waiting for ingestion to complete (polling every {POLL_INTERVAL}s) ...")

    while True:
        response = bedrock.get_ingestion_job(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            dataSourceId=data_source_id,
            ingestionJobId=job_id,
        )
        job    = response["ingestionJob"]
        status = job["status"]
        stats  = job.get("statistics", {})

        print(
            f"  Status: {status} | "
            f"scanned: {stats.get('numberOfDocumentsScanned', 0)} | "
            f"indexed: {stats.get('numberOfNewDocumentsIndexed', 0)} | "
            f"failed: {stats.get('numberOfDocumentsFailed', 0)}"
        )

        if status == "COMPLETE":
            print("\nIngestion complete.")
            print(f"  Documents indexed: {stats.get('numberOfNewDocumentsIndexed', 0)}")
            print(f"  Documents failed:  {stats.get('numberOfDocumentsFailed', 0)}")
            return

        if status == "FAILED":
            failures = job.get("failureReasons", [])
            print(f"\nIngestion FAILED.")
            for reason in failures:
                print(f"  {reason}")
            sys.exit(1)

        time.sleep(POLL_INTERVAL)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== ClaimSense — Bedrock Knowledge Base Ingestion ===\n")
    print(f"Knowledge Base: {KNOWLEDGE_BASE_ID}")
    print(f"S3 Bucket:      {DOCS_BUCKET}")
    print(f"Stage:          {STAGE}")
    print(f"Region:         {REGION}\n")

    validate()

    s3_uri         = upload_policy_manual()
    data_source_id = get_data_source_id()
    job_id         = start_ingestion(data_source_id)
    wait_for_ingestion(data_source_id, job_id)

    print(f"\nDone. The Coverage Check agent can now retrieve policy clauses.")
    print(f"Test it:")
    print(f"  curl -X POST http://localhost:3000/search \\")
    print(f"    -H 'Content-Type: application/json' \\")
    print(f"    -d '{{\"query_text\": \"is hail damage covered\", \"top_k\": 3}}'")


if __name__ == "__main__":
    main()
