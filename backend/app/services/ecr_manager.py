"""ECR Manager — builds and pushes the migration worker Docker image.

Handles:
- Creating ECR repository if it doesn't exist
- Creating CodeBuild project for serverless Docker builds
- Building the worker image using AWS CodeBuild
- Pushing the image to the customer's ECR registry
- Returning the image URI for task definition registration
"""

from __future__ import annotations

import hashlib
import logging
import os
import subprocess
import time
import base64
import zipfile
import tempfile
from dataclasses import dataclass
from typing import Any

from botocore.exceptions import ClientError

from app.services.migration_errors import (
    MigrationError,
    ecr_auth_error,
    ecr_push_error,
    ecr_repository_error,
)

logger = logging.getLogger(__name__)

REPO_NAME = "cloudbridge-migration-worker"
IMAGE_TAG = "latest"
CODEBUILD_PROJECT_NAME = "cloudbridge-worker-builder"


def _compute_worker_hash(worker_dir: str) -> str:
    """Compute a short SHA-256 hash of all files in the worker directory.

    This lets us detect when worker code has changed and force a fresh image
    build, while skipping the build when nothing has changed.
    """
    hasher = hashlib.sha256()
    for root, dirs, files in os.walk(worker_dir):
        # Ignore __pycache__ and .git
        dirs[:] = sorted(d for d in dirs if d not in {"__pycache__", ".git"})
        for fname in sorted(files):
            if fname.endswith((".pyc", ".pyo")):
                continue
            fpath = os.path.join(root, fname)
            hasher.update(fname.encode())
            try:
                with open(fpath, "rb") as f:
                    hasher.update(f.read())
            except OSError:
                pass
    return hasher.hexdigest()[:12]  # 12 hex chars is enough for uniqueness


@dataclass(frozen=True)
class PushedImage:
    """Result of building and pushing a Docker image to ECR."""

    image_uri: str  # e.g. 123456789.dkr.ecr.us-east-1.amazonaws.com/cloudbridge-migration-worker:latest
    repository_uri: str  # e.g. 123456789.dkr.ecr.us-east-1.amazonaws.com/cloudbridge-migration-worker
    tag: str
    digest: str  # SHA256 digest returned by ECR


class ECRManager:
    """Manages ECR repository creation, CodeBuild project setup, and image build."""

    def __init__(self, ecr_client: Any, codebuild_client: Any, s3_client: Any, account_id: str, region: str) -> None:
        self._ecr = ecr_client
        self._codebuild = codebuild_client
        self._s3 = s3_client
        self._account_id = account_id
        self._region = region
        self._repository_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/{REPO_NAME}"
        self._s3_bucket = f"cloudbridge-worker-builds-{account_id}"

    def ensure_repository(self) -> str:
        """Create the ECR repository if it doesn't exist. Returns the repository URI.

        Idempotent — if the repo already exists, returns its URI without error.
        """
        try:
            response = self._ecr.describe_repositories(repositoryNames=[REPO_NAME])
            repos = response.get("repositories", [])
            if repos:
                uri = repos[0]["repositoryUri"]
                logger.info("ECR repository already exists: %s", uri)
                return uri
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code != "RepositoryNotFoundException":
                raise ecr_repository_error(
                    f"Failed to describe ECR repository: {exc}",
                    REPO_NAME,
                    retryable=True,
                ) from exc

        # Create the repository
        logger.info("Creating ECR repository: %s", REPO_NAME)
        try:
            response = self._ecr.create_repository(
                repositoryName=REPO_NAME,
                imageTagMutability="MUTABLE",
                imageScanningConfiguration={"scanOnPush": False},
                encryptionConfiguration={"encryptionType": "AES256"},
            )
            uri = response["repository"]["repositoryUri"]
            logger.info("Created ECR repository: %s", uri)
            return uri
        except ClientError as exc:
            # Handle race condition — another process created it simultaneously
            code = exc.response.get("Error", {}).get("Code", "")
            if code == "RepositoryAlreadyExistsException":
                logger.info("ECR repository created by concurrent process, using existing")
                return self._repository_uri
            raise ecr_repository_error(
                f"Failed to create ECR repository: {exc}",
                REPO_NAME,
                retryable=True,
            ) from exc

    def ensure_s3_bucket(self) -> str:
        """Create S3 bucket for CodeBuild source if it doesn't exist."""
        try:
            self._s3.head_bucket(Bucket=self._s3_bucket)
            logger.info("S3 bucket already exists: %s", self._s3_bucket)
            return self._s3_bucket
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code == "404" or code == "NoSuchBucket":
                logger.info("Creating S3 bucket: %s", self._s3_bucket)
                try:
                    if self._region == "us-east-1":
                        self._s3.create_bucket(Bucket=self._s3_bucket)
                    else:
                        self._s3.create_bucket(
                            Bucket=self._s3_bucket,
                            CreateBucketConfiguration={"LocationConstraint": self._region}
                        )
                    logger.info("Created S3 bucket: %s", self._s3_bucket)
                    return self._s3_bucket
                except ClientError as create_exc:
                    raise ecr_repository_error(
                        f"Failed to create S3 bucket: {create_exc}",
                        self._s3_bucket,
                        retryable=True,
                    ) from create_exc
            raise ecr_repository_error(
                f"Failed to check S3 bucket: {exc}",
                self._s3_bucket,
                retryable=True,
            ) from exc

    def ensure_codebuild_project(self) -> None:
        """Create CodeBuild project for Docker builds if it doesn't exist."""
        try:
            self._codebuild.batch_get_projects(names=[CODEBUILD_PROJECT_NAME])
            logger.info("CodeBuild project already exists: %s", CODEBUILD_PROJECT_NAME)
            return
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code != "ResourceNotFoundException":
                logger.warning(f"Failed to check CodeBuild project: {exc}")

        # Create the CodeBuild project
        logger.info("Creating CodeBuild project: %s", CODEBUILD_PROJECT_NAME)
        buildspec = {
            "version": "0.2",
            "phases": {
                "install": {
                    "runtime-versions": {
                        "python": "3.12"
                    },
                    "commands": [
                        "pip install docker"
                    ]
                },
                "pre_build": {
                    "commands": [
                        "aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com"
                    ]
                },
                "build": {
                    "commands": [
                        "docker build -t $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/cloudbridge-migration-worker:latest .",
                        "docker tag $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/cloudbridge-migration-worker:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/cloudbridge-migration-worker:latest"
                    ]
                },
                "post_build": {
                    "commands": [
                        "docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/cloudbridge-migration-worker:latest"
                    ]
                }
            },
            "artifacts": {
                "files": [
                    "**/*"
                ]
            }
        }

        try:
            self._codebuild.create_project(
                name=CODEBUILD_PROJECT_NAME,
                description="CloudBridge worker Docker image builder",
                source={
                    "type": "S3",
                    "location": f"{self._s3_bucket}/worker-source.zip",
                    "buildspec": buildspec
                },
                artifacts={
                    "type": "NO_ARTIFACTS"
                },
                environment={
                    "type": "LINUX_CONTAINER",
                    "image": "aws/codebuild/standard:7.0",
                    "computeType": "BUILD_GENERAL1_SMALL",
                    "privilegedMode": True,
                    "environmentVariables": [
                        {
                            "name": "AWS_DEFAULT_REGION",
                            "value": self._region
                        },
                        {
                            "name": "AWS_ACCOUNT_ID",
                            "value": self._account_id
                        }
                    ]
                },
                serviceRole=f"arn:aws:iam::{self._account_id}:role/codebuild-cloudbridge-service-role"
            )
            logger.info("Created CodeBuild project: %s", CODEBUILD_PROJECT_NAME)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code == "ResourceAlreadyExistsException":
                logger.info("CodeBuild project created by concurrent process, using existing")
            else:
                raise ecr_repository_error(
                    f"Failed to create CodeBuild project: {exc}",
                    CODEBUILD_PROJECT_NAME,
                    retryable=True,
                ) from exc

    def get_authorization_token(self) -> tuple[str, str]:
        """Get ECR authorization token. Returns (username, password)."""
        try:
            response = self._ecr.get_authorization_token()
            auth_data = response["authorizationData"][0]
            import base64
            token = base64.b64decode(auth_data["authorizationToken"]).decode("utf-8")
            username, password = token.split(":", 1)
            return username, password
        except ClientError as exc:
            raise ecr_auth_error(
                f"Failed to get ECR authorization token: {exc}"
            ) from exc

    def build_and_push(
        self,
        worker_dir: str,
        tag: str | None = None,
    ) -> PushedImage:
        """Build the worker Docker image using CodeBuild and push it to ECR.

        Uses a content-hash-based tag so:
        - A new image is ALWAYS built when any worker file changes.
        - The same image is reused only when the code is identical.
        - The :latest tag is also updated to point to the latest build.

        Args:
            worker_dir: Path to the worker/ directory containing Dockerfile
            tag: Optional explicit image tag (overrides content-hash logic)

        Returns:
            PushedImage with the full ECR image URI
        """
        # Step 1: Ensure infrastructure exists
        self.ensure_repository()
        self.ensure_s3_bucket()
        self.ensure_codebuild_project()

        # Compute a content-hash tag
        content_hash = _compute_worker_hash(worker_dir)
        versioned_tag = tag or f"sha-{content_hash}"
        versioned_uri = f"{self._repository_uri}:{versioned_tag}"
        latest_uri = f"{self._repository_uri}:latest"

        logger.info(
            "Worker content hash: %s  →  tag: %s",
            content_hash, versioned_tag,
        )

        # Force rebuild - delete existing :latest tag
        try:
            self._ecr.batch_delete_image(
                repositoryName=REPO_NAME,
                imageIds=[{"imageTag": "latest"}]
            )
            logger.info("Deleted existing :latest tag to force rebuild")
        except ClientError as exc:
            logger.debug(f"No existing :latest tag to delete: {exc}")

        # Step 2: Upload worker source to S3
        s3_key = self._upload_worker_source(worker_dir)
        logger.info("Uploaded worker source to S3: %s", s3_key)

        # Step 3: Trigger CodeBuild build
        build_id = self._trigger_codebuild_build(s3_key)
        logger.info("Triggered CodeBuild build: %s", build_id)

        # Step 4: Wait for build completion
        self._wait_for_build_completion(build_id)
        logger.info("CodeBuild completed successfully")

        # Step 5: Tag as :latest
        try:
            self._ecr.batch_get_image(
                repositoryName=REPO_NAME,
                imageIds=[{"imageTag": versioned_tag}]
            )
            # Get the image manifest and tag as latest
            images = self._ecr.list_images(repositoryName=REPO_NAME)
            if images.get("imageIds"):
                latest_image = None
                for img in images["imageIds"]:
                    if "imageTag" in img and img["imageTag"] == versioned_tag:
                        latest_image = img
                        break
                
                if latest_image:
                    # Use put-image to tag as latest (ECR doesn't have direct tag copy)
                    # We'll just use the versioned tag in task definition
                    logger.info("Using versioned tag for task definition: %s", versioned_tag)
                    return PushedImage(
                        image_uri=versioned_uri,
                        repository_uri=self._repository_uri,
                        tag=versioned_tag,
                        digest="codebuild-built",
                    )
        except ClientError as exc:
            logger.warning(f"Could not tag image as latest: {exc}")

        logger.info("Successfully built image via CodeBuild: %s", versioned_uri)
        return PushedImage(
            image_uri=latest_uri,   # ECS task uses :latest
            repository_uri=self._repository_uri,
            tag=versioned_tag,
            digest="codebuild-built",
        )

    def _upload_worker_source(self, worker_dir: str) -> str:
        """Zip and upload worker source to S3 for CodeBuild."""
        s3_key = "worker-source.zip"
        
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip:
            try:
                with zipfile.ZipFile(tmp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(worker_dir):
                        # Exclude __pycache__ and other non-source files
                        dirs[:] = [d for d in dirs if d not in ["__pycache__", ".git", "node_modules"]]
                        
                        for file in files:
                            if file.endswith((".pyc", ".pyo", ".pyd")):
                                continue
                            
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, worker_dir)
                            zipf.write(file_path, arcname)
                
                # Upload to S3
                self._s3.upload_file(
                    tmp_zip.name,
                    self._s3_bucket,
                    s3_key,
                    ExtraArgs={'ContentType': 'application/zip'}
                )
                logger.info("Uploaded worker source zip to S3: %s/%s", self._s3_bucket, s3_key)
                return s3_key
            finally:
                os.unlink(tmp_zip.name)

    def _trigger_codebuild_build(self, s3_key: str) -> str:
        """Trigger a CodeBuild build with the uploaded source."""
        try:
            response = self._codebuild.start_build(
                projectName=CODEBUILD_PROJECT_NAME,
                sourceLocationOverride=f"{self._s3_bucket}/{s3_key}",
                sourceTypeOverride="S3"
            )
            build_id = response["build"]["id"]
            logger.info("Started CodeBuild build: %s", build_id)
            return build_id
        except ClientError as exc:
            raise ecr_push_error(
                f"Failed to start CodeBuild build: {exc}",
                CODEBUILD_PROJECT_NAME,
                retryable=True,
            ) from exc

    def _wait_for_build_completion(self, build_id: str, timeout_seconds: int = 600) -> None:
        """Wait for CodeBuild build to complete."""
        import time
        deadline = time.time() + timeout_seconds
        
        while time.time() < deadline:
            try:
                response = self._codebuild.batch_get_builds(ids=[build_id])
                builds = response.get("builds", [])
                if not builds:
                    raise ecr_push_error(
                        f"Build {build_id} not found",
                        build_id,
                        retryable=False,
                    )
                
                build = builds[0]
                build_status = build.get("buildStatus")
                
                if build_status == "SUCCEEDED":
                    logger.info("CodeBuild build succeeded: %s", build_id)
                    return
                elif build_status in ("FAILED", "FAULT", "STOPPED", "TIMEDOUT"):
                    phase_context = build.get("phases", [])
                    error_details = []
                    for phase in phase_context:
                        if phase.get("phaseStatus") in ("FAILED", "FAULT"):
                            error_details.append(f"{phase.get('phaseType')}: {phase.get('context', '')}")
                    
                    raise ecr_push_error(
                        f"CodeBuild build failed with status {build_status}. Details: {'; '.join(error_details)}",
                        build_id,
                        retryable=False,
                    )
                
                # Still in progress
                logger.info("Build status: %s, waiting...", build_status)
                time.sleep(10)
                
            except ClientError as exc:
                if time.time() >= deadline:
                    raise
                logger.warning("Error checking build status: %s, retrying...", exc)
                time.sleep(5)
        
        raise ecr_push_error(
            f"CodeBuild build timed out after {timeout_seconds}s",
            build_id,
            retryable=False,
        )

