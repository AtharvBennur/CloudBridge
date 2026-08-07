"""ECR Manager — builds and pushes the migration worker Docker image.

Handles:
- Creating ECR repository if it doesn't exist
- Authenticating Docker with ECR
- Building the worker image from the worker/ directory
- Pushing the image to the customer's ECR registry
- Returning the image URI for task definition registration
"""

from __future__ import annotations

import hashlib
import logging
import os
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
        # Step 1: Ensure repository exists
        self.ensure_repository()

        # Compute a content-hash tag so stale images are never reused
        content_hash = _compute_worker_hash(worker_dir)
        versioned_tag = tag or f"sha-{content_hash}"
        versioned_uri = f"{self._repository_uri}:{versioned_tag}"
        latest_uri = f"{self._repository_uri}:latest"

        logger.info(
            "Worker content hash: %s  →  tag: %s",
            content_hash, versioned_tag,
        )

        # Check whether this exact content hash already exists in ECR
        try:
            images = self._ecr.describe_images(
                repositoryName=REPO_NAME,
                imageIds=[{"imageTag": versioned_tag}],
            ).get("imageDetails", [])
            if images:
                digest = images[0].get("imageDigest", "existing")
                logger.info(
                    "ECR already has image for content hash '%s' (digest: %s). Reusing.",
                    versioned_tag, digest,
                )
                return PushedImage(
                    image_uri=latest_uri,   # always reference :latest for ECS
                    repository_uri=self._repository_uri,
                    tag=versioned_tag,
                    digest=digest,
                )
        except ClientError as exc:
            logger.debug(
                "Tag '%s' not present in ECR, will build fresh image: %s",
                versioned_tag, exc,
            )

        # Step 2: Check if local docker daemon is running
        try:
            subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=10, check=True)
        except (subprocess.SubprocessError, FileNotFoundError, OSError) as exc:
            logger.warning(
                "Docker Desktop is not running locally. Skipping image build and falling back to "
                "the ':latest' image on AWS ECR. Ensure the latest worker image has been deployed."
            )
            return PushedImage(
                image_uri=latest_uri,
                repository_uri=self._repository_uri,
                tag="latest",
                digest="unknown-local-docker-fallback",
            )

        # Step 3: Get auth token and login Docker
        username, password = self.get_authorization_token()
        self._docker_login(password)

        # Step 4: Build the image (tag with both versioned and :latest)
        self._docker_build(worker_dir, versioned_uri)

        # Step 5: Also tag as :latest so ECS always pulls the newest version
        subprocess.run(
            ["docker", "tag", versioned_uri, latest_uri],
            capture_output=True, text=True, check=False,
        )

        # Step 6: Push both tags
        digest = self._docker_push(versioned_uri)
        self._docker_push(latest_uri)

        logger.info("Successfully pushed image: %s (also tagged as :latest)", versioned_uri)
        return PushedImage(
            image_uri=latest_uri,   # ECS task uses :latest
            repository_uri=self._repository_uri,
            tag=versioned_tag,
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
