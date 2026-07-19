"""ECR Manager — builds and pushes the migration worker Docker image.

Handles:
- Creating ECR repository if it doesn't exist
- Authenticating Docker with ECR
- Building the worker image from the worker/ directory
- Pushing the image to the customer's ECR registry
- Returning the image URI for task definition registration
"""

from __future__ import annotations

import logging
import subprocess
import time
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


@dataclass(frozen=True)
class PushedImage:
    """Result of building and pushing a Docker image to ECR."""

    image_uri: str  # e.g. 123456789.dkr.ecr.us-east-1.amazonaws.com/cloudbridge-migration-worker:latest
    repository_uri: str  # e.g. 123456789.dkr.ecr.us-east-1.amazonaws.com/cloudbridge-migration-worker
    tag: str
    digest: str  # SHA256 digest returned by ECR


class ECRManager:
    """Manages ECR repository creation, Docker build, and image push."""

    def __init__(self, ecr_client: Any, account_id: str, region: str) -> None:
        self._ecr = ecr_client
        self._account_id = account_id
        self._region = region
        self._repository_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/{REPO_NAME}"

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
        """Build the worker Docker image and push it to ECR.

        Args:
            worker_dir: Path to the worker/ directory containing Dockerfile
            tag: Optional image tag (defaults to 'latest')

        Returns:
            PushedImage with the full ECR image URI
        """
        image_tag = tag or IMAGE_TAG
        image_uri = f"{self._repository_uri}:{image_tag}"

        # Step 1: Ensure repository exists
        self.ensure_repository()

        # Step 2: Get auth token and login Docker
        username, password = self.get_authorization_token()
        self._docker_login(password)

        # Step 3: Build the image
        self._docker_build(worker_dir, image_uri)

        # Step 4: Push the image
        digest = self._docker_push(image_uri)

        logger.info("Successfully pushed image: %s", image_uri)
        return PushedImage(
            image_uri=image_uri,
            repository_uri=self._repository_uri,
            tag=image_tag,
            digest=digest,
        )

    def _docker_login(self, password: str) -> None:
        """Authenticate Docker with ECR."""
        endpoint = f"{self._account_id}.dkr.ecr.{self._region}.amazonaws.com"
        cmd = [
            "docker", "login",
            "--username", "AWS",
            "--password", password,
            endpoint,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise ecr_auth_error(
                f"Docker login to ECR failed: {result.stderr.strip()}"
            )
        logger.info("Docker login to ECR successful")

    def _docker_build(self, context_dir: str, tag: str) -> None:
        """Build the Docker image."""
        cmd = [
            "docker", "build",
            "-t", tag,
            "-f", f"{context_dir}/Dockerfile",
            context_dir,
        ]
        logger.info("Building Docker image: %s", tag)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise ecr_push_error(
                f"Docker build failed: {result.stderr.strip()}",
                tag,
                retryable=False,
            )
        logger.info("Docker build successful")

    def _docker_push(self, tag: str) -> str:
        """Push the Docker image to ECR. Returns the image digest."""
        cmd = ["docker", "push", tag]
        logger.info("Pushing Docker image: %s", tag)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise ecr_push_error(
                f"Docker push failed: {result.stderr.strip()}",
                tag,
                retryable=True,
            )

        # Extract digest from push output
        digest = self._extract_digest(result.stdout)
        return digest

    def _extract_digest(self, push_output: str) -> str:
        """Extract the SHA256 digest from docker push output."""
        for line in push_output.splitlines():
            if "digest:" in line and "sha256:" in line:
                # Format: "digest: sha256:abc123... size: 1234"
                parts = line.strip().split()
                for i, part in enumerate(parts):
                    if part == "sha256:" and i + 1 < len(parts):
                        return f"sha256:{parts[i + 1]}"
        return "unknown"
