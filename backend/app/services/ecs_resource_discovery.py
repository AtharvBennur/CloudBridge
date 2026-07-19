"""Auto-discovers or creates AWS ECS infrastructure for migration tasks.

Handles:
- ECS cluster discovery/creation (with ACTIVE waiter)
- VPC discovery (default VPC)
- Subnet discovery/creation (creates subnets if none exist)
- Security group discovery/creation
- IAM execution and task role provisioning
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


# IAM trust policy for ECS tasks (Fargate)
ECS_TASK_TRUST_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "ecs-tasks.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }
    ],
}

# Inline policy for the execution role: pull images, write CloudWatch logs
ECS_EXECUTION_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
            ],
            "Resource": "*",
        }
    ],
}

# Inline policy for the task role: read Secrets Manager, call CloudBridge API
ECS_TASK_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret",
            ],
            "Resource": "*",
        }
    ],
}


@dataclass
class DiscoveredResources:
    """Holds all discovered/created AWS resources needed for ECS task execution."""

    cluster_arn: str
    cluster_name: str
    vpc_id: str
    subnet_ids: list[str] = field(default_factory=list)
    security_group_id: str = ""
    task_role_arn: str = ""
    execution_role_arn: str = ""


class ECSResourceDiscoveryError(Exception):
    """Raised when ECS resource discovery fails."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ECSResourceDiscoveryService:
    """Discovers or creates AWS ECS infrastructure resources."""

    CLUSTER_NAME = "cloudbridge-migration-cluster"
    EXECUTION_ROLE_NAME = "cloudbridge-ecs-execution-role"
    TASK_ROLE_NAME = "cloudbridge-ecs-task-role"

    def __init__(self, ecs_client: Any, ec2_client: Any, iam_client: Any, region: str) -> None:
        self._ecs = ecs_client
        self._ec2 = ec2_client
        self._iam = iam_client
        self._region = region

    def discover_or_create(self, cluster_name: str | None = None) -> DiscoveredResources:
        """Discover existing resources or create missing ones.

        Returns a DiscoveredResources with all ARNs/IDs needed to launch a Fargate task.
        """
        name = cluster_name or self.CLUSTER_NAME
        cluster_arn, cluster_name = self._discover_or_create_cluster(name)
        vpc_id = self._discover_default_vpc()
        subnet_ids = self._discover_or_create_subnets(vpc_id)
        security_group_id = self._discover_or_create_security_group(vpc_id, cluster_name)
        execution_role_arn = self._discover_or_create_execution_role()
        task_role_arn = self._discover_or_create_task_role()

        return DiscoveredResources(
            cluster_arn=cluster_arn,
            cluster_name=cluster_name,
            vpc_id=vpc_id,
            subnet_ids=subnet_ids,
            security_group_id=security_group_id,
            task_role_arn=task_role_arn,
            execution_role_arn=execution_role_arn,
        )

    def _discover_or_create_cluster(self, cluster_name: str) -> tuple[str, str]:
        """Find an existing ECS cluster or create a new one. Waits until ACTIVE."""
        try:
            response = self._ecs.describe_clusters(clusters=[cluster_name])
            clusters = response.get("clusters", [])
            failures = response.get("failures", [])

            if clusters:
                cluster = clusters[0]
                if cluster.get("status") == "ACTIVE":
                    logger.info("Found existing ACTIVE ECS cluster: %s", cluster_name)
                    return cluster["clusterArn"], cluster["clusterName"]
                # Cluster exists but not ACTIVE yet — wait for it
                logger.info("ECS cluster '%s' exists with status '%s', waiting for ACTIVE...", cluster_name, cluster.get("status"))
                return self._wait_for_cluster(cluster_name)

            # No cluster returned — check if it's a real failure or just "MISSING"
            if failures:
                reason = failures[0].get("reason", "")
                if reason == "MISSING":
                    logger.info("ECS cluster '%s' does not exist (MISSING), will create it", cluster_name)
                else:
                    raise ECSResourceDiscoveryError(
                        f"ECS cluster '{cluster_name}' has failures: {failures[0].get('detail', reason)}"
                    )
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code != "ClusterNotFoundException":
                raise ECSResourceDiscoveryError(f"Failed to describe ECS cluster: {exc}") from exc

        # Create the cluster
        logger.info("Creating ECS cluster: %s", cluster_name)
        try:
            response = self._ecs.create_cluster(
                clusterName=cluster_name,
                capacityProviders=["FARGATE"],
                defaultCapacityProviderStrategy=[{"capacityProvider": "FARGATE", "weight": 1}],
                tags=[{"key": "ManagedBy", "value": "CloudBridge"}],
            )
            cluster = response.get("cluster", {})
            logger.info("ECS cluster creation initiated, waiting for ACTIVE status...")
            return self._wait_for_cluster(cluster_name)
        except ClientError as exc:
            raise ECSResourceDiscoveryError(
                f"Failed to create ECS cluster '{cluster_name}'. "
                f"Ensure the IAM role has ecs:CreateCluster permission. Details: {exc}"
            ) from exc

    def _wait_for_cluster(self, cluster_name: str, max_wait_seconds: int = 120) -> tuple[str, str]:
        """Poll the cluster until it reaches ACTIVE status."""
        deadline = time.time() + max_wait_seconds
        while time.time() < deadline:
            try:
                response = self._ecs.describe_clusters(clusters=[cluster_name])
                clusters = response.get("clusters", [])
                if clusters:
                    cluster = clusters[0]
                    status = cluster.get("status", "")
                    if status == "ACTIVE":
                        logger.info("ECS cluster '%s' is now ACTIVE", cluster_name)
                        return cluster["clusterArn"], cluster["clusterName"]
                    if status in ("FAILED", "INACTIVE"):
                        raise ECSResourceDiscoveryError(
                            f"ECS cluster '{cluster_name}' entered terminal status '{status}'. "
                            f"Reason: {cluster.get('statusReason', 'unknown')}"
                        )
                    logger.info("Cluster status: %s, waiting...", status)
            except ClientError as exc:
                logger.warning("Error polling cluster status: %s", exc)
            time.sleep(5)

        raise ECSResourceDiscoveryError(
            f"Timed out waiting for ECS cluster '{cluster_name}' to become ACTIVE after {max_wait_seconds}s. "
            "Check the AWS Console for the cluster status."
        )

    def _discover_default_vpc(self) -> str:
        """Find the default VPC in the region."""
        try:
            response = self._ec2.describe_vpcs(
                Filters=[{"Name": "isDefault", "Values": ["true"]}]
            )
            vpcs = response.get("Vpcs", [])
            if not vpcs:
                raise ECSResourceDiscoveryError(
                    "No default VPC found in this region. Create a default VPC in the AWS Console "
                    "or ensure ec2:DescribeVpcs permission is granted."
                )
            vpc_id = vpcs[0]["VpcId"]
            logger.info("Found default VPC: %s", vpc_id)
            return vpc_id
        except ClientError as exc:
            raise ECSResourceDiscoveryError(
                f"Failed to discover default VPC. Ensure ec2:DescribeVpcs permission is granted. Details: {exc}"
            ) from exc

    def _discover_or_create_subnets(self, vpc_id: str, min_count: int = 2) -> list[str]:
        """Find subnets in the VPC. Creates subnets across AZs if fewer than min_count exist."""
        try:
            response = self._ec2.describe_subnets(
                Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
            )
            all_subnets = response.get("Subnets", [])

            if len(all_subnets) >= min_count:
                # Sort by AZ for deterministic selection
                all_subnets.sort(key=lambda s: s.get("AvailabilityZone", ""))
                # Prefer private subnets (no MapPublicIpOnLaunch)
                private_subnets = [
                    s["SubnetId"]
                    for s in all_subnets
                    if not s.get("MapPublicIpOnLaunch", False)
                ]
                if len(private_subnets) >= min_count:
                    logger.info("Found %d private subnets in VPC %s", len(private_subnets), vpc_id)
                    return private_subnets[:min_count]
                subnet_ids = [s["SubnetId"] for s in all_subnets[:min_count]]
                logger.info("Using %d available subnets in VPC %s", len(subnet_ids), vpc_id)
                return subnet_ids

            # Not enough subnets — create them across AZs
            logger.info("Only %d subnet(s) found in VPC %s, creating additional subnets...", len(all_subnets), vpc_id)
            return self._create_subnets(vpc_id, min_count)
        except ClientError as exc:
            raise ECSResourceDiscoveryError(
                f"Failed to discover subnets. Ensure ec2:DescribeSubnets permission is granted. Details: {exc}"
            ) from exc

    def _create_subnets(self, vpc_id: str, count: int) -> list[str]:
        """Create subnets across different AZs in the VPC."""
        # Get available AZs
        try:
            az_response = self._ec2.describe_availability_zones(
                Filters=[{"Name": "state", "Values": ["available"]}]
            )
            azs = [az["ZoneName"] for az in az_response.get("AvailabilityZones", [])]
        except ClientError as exc:
            raise ECSResourceDiscoveryError(
                f"Failed to describe availability zones: {exc}"
            ) from exc

        if len(azs) < count:
            raise ECSResourceDiscoveryError(
                f"Need at least {count} availability zones but only {len(azs)} available. "
                "Fargate requires subnets in at least 2 AZs."
            )

        # Get VPC CIDR to calculate subnet ranges
        try:
            vpc_response = self._ec2.describe_vpcs(VpcIds=[vpc_id])
            vpc_cidr = vpc_response["Vpcs"][0]["CidrBlock"]
        except ClientError as exc:
            raise ECSResourceDiscoveryError(f"Failed to describe VPC CIDR: {exc}") from exc

        # Parse base CIDR and create /20 subnets
        import ipaddress
        base_network = ipaddress.ip_network(vpc_cidr)
        subnet_cidrs = list(base_network.subnets(new_prefix=20))

        created_ids = []
        for i in range(count):
            az = azs[i]
            cidr = str(subnet_cidrs[i]) if i < len(subnet_cidrs) else f"10.0.{i * 16}.0/20"
            try:
                response = self._ec2.create_subnet(
                    VpcId=vpc_id,
                    CidrBlock=cidr,
                    AvailabilityZone=az,
                    TagSpecifications=[
                        {
                            "ResourceType": "subnet",
                            "Tags": [
                                {"Key": "ManagedBy", "Value": "CloudBridge"},
                                {"Key": "Name", "Value": f"cloudbridge-subnet-{az}"},
                            ],
                        }
                    ],
                )
                subnet_id = response["Subnet"]["SubnetId"]
                created_ids.append(subnet_id)
                logger.info("Created subnet %s in AZ %s with CIDR %s", subnet_id, az, cidr)
            except ClientError as exc:
                raise ECSResourceDiscoveryError(
                    f"Failed to create subnet in AZ {az}. Ensure ec2:CreateSubnet permission is granted. Details: {exc}"
                ) from exc

        logger.info("Created %d subnets in VPC %s", len(created_ids), vpc_id)
        return created_ids

    def _discover_or_create_security_group(self, vpc_id: str, cluster_name: str) -> str:
        """Find or create a security group for ECS tasks."""
        sg_name = f"{cluster_name}-task-sg"

        try:
            response = self._ec2.describe_security_groups(
                Filters=[
                    {"Name": "group-name", "Values": [sg_name]},
                    {"Name": "vpc-id", "Values": [vpc_id]},
                ]
            )
            groups = response.get("SecurityGroups", [])
            if groups:
                sg_id = groups[0]["GroupId"]
                logger.info("Found existing security group: %s", sg_id)
                return sg_id
        except ClientError as exc:
            raise ECSResourceDiscoveryError(
                f"Failed to describe security groups. Ensure ec2:DescribeSecurityGroups permission is granted. Details: {exc}"
            ) from exc

        # Create security group
        logger.info("Creating security group: %s", sg_name)
        try:
            response = self._ec2.create_security_group(
                GroupName=sg_name,
                Description=f"CloudBridge ECS task security group for {cluster_name}",
                VpcId=vpc_id,
                TagSpecifications=[
                    {
                        "ResourceType": "security-group",
                        "Tags": [{"Key": "ManagedBy", "Value": "CloudBridge"}],
                    }
                ],
            )
            sg_id = response["GroupId"]

            # Add egress rule (allow all outbound).
            # AWS automatically adds a default ALL→0.0.0.0/0 egress rule on
            # creation, so this call may return InvalidPermission.Duplicate.
            # Treat that as success — the rule already exists.
            try:
                self._ec2.authorize_security_group_egress(
                    GroupId=sg_id,
                    IpPermissions=[
                        {
                            "IpProtocol": "-1",
                            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                        }
                    ],
                )
            except ClientError as egress_exc:
                code = egress_exc.response.get("Error", {}).get("Code", "")
                if code != "InvalidPermission.Duplicate":
                    raise ECSResourceDiscoveryError(
                        f"Failed to add egress rule to security group '{sg_name}'. "
                        f"Ensure ec2:AuthorizeSecurityGroupEgress permission is granted. Details: {egress_exc}"
                    ) from egress_exc
                logger.info("Default egress rule already exists on %s, skipping", sg_id)

            logger.info("Created security group: %s", sg_id)
            return sg_id
        except ClientError as exc:
            raise ECSResourceDiscoveryError(
                f"Failed to create security group '{sg_name}'. "
                f"Ensure ec2:CreateSecurityGroup and ec2:AuthorizeSecurityGroupEgress permissions are granted. Details: {exc}"
            ) from exc

    def _discover_or_create_execution_role(self) -> str:
        """Find or create the ECS execution role for Fargate tasks."""
        role_name = self.EXECUTION_ROLE_NAME

        try:
            response = self._iam.get_role(RoleName=role_name)
            role_arn = response["Role"]["Arn"]
            logger.info("Found existing execution role: %s", role_arn)
            return role_arn
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code != "NoSuchEntity":
                raise ECSResourceDiscoveryError(
                    f"Failed to get execution role. Ensure iam:GetRole permission is granted. Details: {exc}"
                ) from exc

        # Create the role
        logger.info("Creating ECS execution role: %s", role_name)
        try:
            response = self._iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(ECS_TASK_TRUST_POLICY),
                Description="CloudBridge ECS Fargate execution role for pulling images and writing logs",
                Tags=[{"Key": "ManagedBy", "Value": "CloudBridge"}],
            )
            role_arn = response["Role"]["Arn"]

            # Attach execution policy
            self._iam.put_role_policy(
                RoleName=role_name,
                PolicyName="ECSExecutionPolicy",
                PolicyDocument=json.dumps(ECS_EXECUTION_POLICY),
            )

            logger.info("Created execution role: %s", role_arn)
            return role_arn
        except ClientError as exc:
            raise ECSResourceDiscoveryError(
                f"Failed to create execution role '{role_name}'. "
                f"Ensure iam:CreateRole, iam:PutRolePolicy permissions are granted. Details: {exc}"
            ) from exc

    def _discover_or_create_task_role(self) -> str:
        """Find or create the ECS task role for Fargate tasks."""
        role_name = self.TASK_ROLE_NAME

        try:
            response = self._iam.get_role(RoleName=role_name)
            role_arn = response["Role"]["Arn"]
            logger.info("Found existing task role: %s", role_arn)
            return role_arn
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code != "NoSuchEntity":
                raise ECSResourceDiscoveryError(
                    f"Failed to get task role. Ensure iam:GetRole permission is granted. Details: {exc}"
                ) from exc

        # Create the role
        logger.info("Creating ECS task role: %s", role_name)
        try:
            response = self._iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(ECS_TASK_TRUST_POLICY),
                Description="CloudBridge ECS Fargate task role for accessing AWS services",
                Tags=[{"Key": "ManagedBy", "Value": "CloudBridge"}],
            )
            role_arn = response["Role"]["Arn"]

            # Attach task policy
            self._iam.put_role_policy(
                RoleName=role_name,
                PolicyName="ECSTaskPolicy",
                PolicyDocument=json.dumps(ECS_TASK_POLICY),
            )

            logger.info("Created task role: %s", role_arn)
            return role_arn
        except ClientError as exc:
            raise ECSResourceDiscoveryError(
                f"Failed to create task role '{role_name}'. "
                f"Ensure iam:CreateRole, iam:PutRolePolicy permissions are granted. Details: {exc}"
            ) from exc
