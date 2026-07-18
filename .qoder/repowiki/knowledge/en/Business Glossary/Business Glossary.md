---
kind: business_term
name: Business Glossary
category: business_term
scope:
    - '**'
---

### CloudBridge
- Definition：The project's product name — an enterprise SaaS platform for orchestrating, monitoring, and managing database migrations across AWS environments, supporting schema migration, change data capture (CDC), schema drift detection, approval workflows, and rollback management.

### Change Data Capture (CDC)
- Definition：A feature that performs real-time replication monitoring with WAL-based change tracking, allowing continuous synchronization of database changes without full re-migration.
- Aliases：cdc

### Schema Drift Detection
- Definition：Automated comparison of database schemas between source and target to detect structural differences (tables, columns, indexes) that deviate from expected state, with support for approval workflows and rollback.
- Aliases：schema drift

### Pre-flight Validation
- Definition：Multi-step readiness checks performed before starting a migration, including connectivity tests, permission validation, and configuration verification to ensure migration can proceed safely.
- Aliases：preflight

### Approval Workflow
- Definition：Multi-level schema change approval process with risk-based auto-approval, requiring human sign-off for risky schema modifications before they can be applied to production databases.
- Aliases：schema approval

### Checkpoint-based Recovery
- Definition：Migration fault tolerance mechanism where long-running migrations periodically save their progress state, allowing them to resume from the last checkpoint rather than restarting from scratch after failures.
- Aliases：checkpoint recovery、migration checkpoint

### ECS/Fargate Orchestration
- Definition：Container execution model where migration workers run as managed tasks on Amazon ECS using Fargate (serverless containers), providing scalable, isolated execution environments for migration jobs.
- Aliases：ecs tasks、fargate workers

### Cross-account Access
- Definition：Security pattern where CloudBridge runs in a control plane AWS account and assumes roles in customer accounts (via STS AssumeRole with ExternalId) to access their databases and resources without sharing long-term credentials.
- Aliases：assume role、cross-account
