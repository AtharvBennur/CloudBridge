# Database Migrations

<cite>
**Referenced Files in This Document**
- [backend/app/models/migration.py](file://backend/app/models/migration.py)
- [backend/app/models/migration_checkpoint.py](file://backend/app/models/migration_checkpoint.py)
- [backend/app/models/schema_snapshot.py](file://backend/app/models/schema_snapshot.py)
- [backend/app/models/audit_log.py](file://backend/app/models/audit_log.py)
- [backend/app/services/migration_service.py](file://backend/app/services/migration_service.py)
- [backend/app/services/schema_approval_service.py](file://backend/app/services/schema_approval_service.py)
- [backend/app/services/rollback_service.py](file://backend/app/services/rollback_service.py)
- [backend/app/routes/migration.py](file://backend/app/routes/migration.py)
- [backend/app/routes/migration_engine.py](file://backend/app/routes/migration_engine.py)
- [backend/app/routes/schema_approval.py](file://backend/app/routes/schema_approval.py)
- [backend/app/routes/rollback.py](file://backend/app/routes/rollback.py)
- [backend/app/exceptions/migration.py](file://backend/app/exceptions/migration.py)
- [backend/app/exceptions/schema_approval.py](file://backend/app/exceptions/schema_approval.py)
- [backend/app/exceptions/rollback.py](file://backend/app/exceptions/rollback.py)
- [backend/migrations/env.py](file://backend/migrations/env.py)
- [backend/migrations/script.py.mako](file://backend/migrations/script.py.mako)
- [backend/migrations/README](file://backend/migrations/README)
- [backend/tests/test_migrations.py](file://backend/tests/test_migrations.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)
10. [Appendices](#appendices)

## Introduction
This document explains the database migration system in CloudBridge with a focus on version-controlled schema changes, lifecycle management, and safe evolution. It covers how migrations are created, reviewed, approved, executed, tracked, and rolled back. It also documents the migration engine architecture, including execution strategies, dependency resolution, error handling, testing strategies, validation rules, and best practices for safe schema evolution.

## Project Structure
CloudBridge organizes migration-related functionality across models, services, routes, exceptions, Alembic configuration, and tests:
- Models define persistent entities for migrations, checkpoints, snapshots, and audit logs.
- Services implement business logic for creating, approving, executing, and rolling back migrations.
- Routes expose APIs to orchestrate the migration lifecycle.
- Exceptions standardize error responses across the migration subsystem.
- Alembic files configure the migration environment and template generation.
- Tests validate core behaviors and edge cases.

```mermaid
graph TB
subgraph "Backend"
A["Models<br/>migration.py, migration_checkpoint.py,<br/>schema_snapshot.py, audit_log.py"]
B["Services<br/>migration_service.py, schema_approval_service.py,<br/>rollback_service.py"]
C["Routes<br/>migration.py, migration_engine.py,<br/>schema_approval.py, rollback.py"]
D["Exceptions<br/>migration.py, schema_approval.py, rollback.py"]
E["Alembic<br/>migrations/env.py, script.py.mako, README"]
F["Tests<br/>test_migrations.py"]
end
C --> B
B --> A
B --> E
C --> D
F --> C
F --> B
```

**Diagram sources**
- [backend/app/models/migration.py](file://backend/app/models/migration.py)
- [backend/app/models/migration_checkpoint.py](file://backend/app/models/migration_checkpoint.py)
- [backend/app/models/schema_snapshot.py](file://backend/app/models/schema_snapshot.py)
- [backend/app/models/audit_log.py](file://backend/app/models/audit_log.py)
- [backend/app/services/migration_service.py](file://backend/app/services/migration_service.py)
- [backend/app/services/schema_approval_service.py](file://backend/app/services/schema_approval_service.py)
- [backend/app/services/rollback_service.py](file://backend/app/services/rollback_service.py)
- [backend/app/routes/migration.py](file://backend/app/routes/migration.py)
- [backend/app/routes/migration_engine.py](file://backend/app/routes/migration_engine.py)
- [backend/app/routes/schema_approval.py](file://backend/app/routes/schema_approval.py)
- [backend/app/routes/rollback.py](file://backend/app/routes/rollback.py)
- [backend/app/exceptions/migration.py](file://backend/app/exceptions/migration.py)
- [backend/app/exceptions/schema_approval.py](file://backend/app/exceptions/schema_approval.py)
- [backend/app/exceptions/rollback.py](file://backend/app/exceptions/rollback.py)
- [backend/migrations/env.py](file://backend/migrations/env.py)
- [backend/migrations/script.py.mako](file://backend/migrations/script.py.mako)
- [backend/migrations/README](file://backend/migrations/README)
- [backend/tests/test_migrations.py](file://backend/tests/test_migrations.py)

**Section sources**
- [backend/app/models/migration.py](file://backend/app/models/migration.py)
- [backend/app/models/migration_checkpoint.py](file://backend/app/models/migration_checkpoint.py)
- [backend/app/models/schema_snapshot.py](file://backend/app/models/schema_snapshot.py)
- [backend/app/models/audit_log.py](file://backend/app/models/audit_log.py)
- [backend/app/services/migration_service.py](file://backend/app/services/migration_service.py)
- [backend/app/services/schema_approval_service.py](file://backend/app/services/schema_approval_service.py)
- [backend/app/services/rollback_service.py](file://backend/app/services/rollback_service.py)
- [backend/app/routes/migration.py](file://backend/app/routes/migration.py)
- [backend/app/routes/migration_engine.py](file://backend/app/routes/migration_engine.py)
- [backend/app/routes/schema_approval.py](file://backend/app/routes/schema_approval.py)
- [backend/app/routes/rollback.py](file://backend/app/routes/rollback.py)
- [backend/app/exceptions/migration.py](file://backend/app/exceptions/migration.py)
- [backend/app/exceptions/schema_approval.py](file://backend/app/exceptions/schema_approval.py)
- [backend/app/exceptions/rollback.py](file://backend/app/exceptions/rollback.py)
- [backend/migrations/env.py](file://backend/migrations/env.py)
- [backend/migrations/script.py.mako](file://backend/migrations/script.py.mako)
- [backend/migrations/README](file://backend/migrations/README)
- [backend/tests/test_migrations.py](file://backend/tests/test_migrations.py)

## Core Components
- Migration model: Represents a migration unit with metadata such as version identifiers, status, and timestamps.
- Migration checkpoint: Tracks per-environment progress and state during execution.
- Schema snapshot: Captures a point-in-time view of the schema for comparison and rollback support.
- Audit log: Records immutable events for approvals, executions, and rollbacks.
- Migration service: Orchestrates creation, validation, approval gating, execution, and rollback flows.
- Schema approval service: Manages review states, approvals, and policy enforcement.
- Rollback service: Executes reverse operations safely with safeguards and verification.
- Routes: Provide REST endpoints that coordinate user actions with services.
- Exceptions: Centralized error types for consistent API responses.
- Alembic integration: Environment setup and migration script templates.

**Section sources**
- [backend/app/models/migration.py](file://backend/app/models/migration.py)
- [backend/app/models/migration_checkpoint.py](file://backend/app/models/migration_checkpoint.py)
- [backend/app/models/schema_snapshot.py](file://backend/app/models/schema_snapshot.py)
- [backend/app/models/audit_log.py](file://backend/app/models/audit_log.py)
- [backend/app/services/migration_service.py](file://backend/app/services/migration_service.py)
- [backend/app/services/schema_approval_service.py](file://backend/app/services/schema_approval_service.py)
- [backend/app/services/rollback_service.py](file://backend/app/services/rollback_service.py)
- [backend/app/routes/migration.py](file://backend/app/routes/migration.py)
- [backend/app/routes/migration_engine.py](file://backend/app/routes/migration_engine.py)
- [backend/app/routes/schema_approval.py](file://backend/app/routes/schema_approval.py)
- [backend/app/routes/rollback.py](file://backend/app/routes/rollback.py)
- [backend/app/exceptions/migration.py](file://backend/app/exceptions/migration.py)
- [backend/app/exceptions/schema_approval.py](file://backend/app/exceptions/schema_approval.py)
- [backend/app/exceptions/rollback.py](file://backend/app/exceptions/rollback.py)
- [backend/migrations/env.py](file://backend/migrations/env.py)
- [backend/migrations/script.py.mako](file://backend/migrations/script.py.mako)
- [backend/migrations/README](file://backend/migrations/README)

## Architecture Overview
The migration system follows a layered architecture:
- Presentation layer (routes) validates inputs and delegates to services.
- Service layer enforces business rules, orchestrates Alembic operations, updates models, and records audit events.
- Data layer persists migration state, checkpoints, snapshots, and audit logs.
- Alembic provides the underlying migration engine and version control.

```mermaid
sequenceDiagram
participant Client as "Client"
participant Route as "Migration Route"
participant Approval as "Schema Approval Service"
participant MigSvc as "Migration Service"
participant Engine as "Alembic Engine"
participant DB as "Database"
participant Audit as "Audit Log"
Client->>Route : "Create migration request"
Route->>MigSvc : "validate_and_create()"
MigSvc->>DB : "Persist migration record"
MigSvc-->>Route : "Created migration"
Route-->>Client : "201 Created"
Client->>Route : "Request approval"
Route->>Approval : "submit_for_review()"
Approval->>DB : "Update approval state"
Approval->>Audit : "Record event"
Approval-->>Route : "Approved or pending"
Route-->>Client : "Status response"
Client->>Route : "Execute migration"
Route->>MigSvc : "execute_migration()"
MigSvc->>Engine : "Run up/down"
Engine->>DB : "Apply changes"
MigSvc->>DB : "Update checkpoints/snapshots"
MigSvc->>Audit : "Log execution"
MigSvc-->>Route : "Execution result"
Route-->>Client : "Result"
```

**Diagram sources**
- [backend/app/routes/migration.py](file://backend/app/routes/migration.py)
- [backend/app/services/migration_service.py](file://backend/app/services/migration_service.py)
- [backend/app/services/schema_approval_service.py](file://backend/app/services/schema_approval_service.py)
- [backend/app/models/migration.py](file://backend/app/models/migration.py)
- [backend/app/models/migration_checkpoint.py](file://backend/app/models/migration_checkpoint.py)
- [backend/app/models/schema_snapshot.py](file://backend/app/models/schema_snapshot.py)
- [backend/app/models/audit_log.py](file://backend/app/models/audit_log.py)
- [backend/migrations/env.py](file://backend/migrations/env.py)

## Detailed Component Analysis

### Migration Model and Lifecycle
The migration model captures the identity and state of each migration unit. The lifecycle includes:
- Creation: Generate a new migration entry with initial status.
- Validation: Ensure required fields and constraints are satisfied.
- Review and Approval: Gate execution until approved by reviewers.
- Execution: Apply forward or backward changes via the migration engine.
- Completion: Update checkpoints and snapshots; persist audit trail.

```mermaid
stateDiagram-v2
[*] --> Draft
Draft --> PendingReview : "Submit for review"
PendingReview --> Approved : "Approve"
PendingReview --> Rejected : "Reject"
Approved --> Executing : "Execute"
Executing --> Completed : "Success"
Executing --> Failed : "Error"
Completed --> [*]
Failed --> [*]
```

**Diagram sources**
- [backend/app/models/migration.py](file://backend/app/models/migration.py)
- [backend/app/services/migration_service.py](file://backend/app/services/migration_service.py)
- [backend/app/services/schema_approval_service.py](file://backend/app/services/schema_approval_service.py)

**Section sources**
- [backend/app/models/migration.py](file://backend/app/models/migration.py)
- [backend/app/services/migration_service.py](file://backend/app/services/migration_service.py)
- [backend/app/services/schema_approval_service.py](file://backend/app/services/schema_approval_service.py)

### Migration Checkpoint and Schema Snapshot
- Migration checkpoint tracks per-environment execution progress, ensuring idempotency and safe retries.
- Schema snapshot captures the current schema state before and after execution to support drift detection and rollback planning.

```mermaid
classDiagram
class Migration {
+id
+version
+status
+created_at
+updated_at
}
class MigrationCheckpoint {
+id
+migration_id
+environment
+step
+state
+updated_at
}
class SchemaSnapshot {
+id
+migration_id
+snapshot_type
+payload
+created_at
}
class AuditLog {
+id
+entity_type
+entity_id
+action
+details
+created_at
}
Migration "1" --> "many" MigrationCheckpoint : "has many"
Migration "1" --> "many" SchemaSnapshot : "produces"
Migration "1" --> "many" AuditLog : "records"
```

**Diagram sources**
- [backend/app/models/migration.py](file://backend/app/models/migration.py)
- [backend/app/models/migration_checkpoint.py](file://backend/app/models/migration_checkpoint.py)
- [backend/app/models/schema_snapshot.py](file://backend/app/models/schema_snapshot.py)
- [backend/app/models/audit_log.py](file://backend/app/models/audit_log.py)

**Section sources**
- [backend/app/models/migration_checkpoint.py](file://backend/app/models/migration_checkpoint.py)
- [backend/app/models/schema_snapshot.py](file://backend/app/models/schema_snapshot.py)
- [backend/app/models/audit_log.py](file://backend/app/models/audit_log.py)

### Approval Workflow System
The approval workflow ensures controlled schema changes:
- Submission: Requesters submit migrations for review.
- Review: Approvers evaluate risk, compatibility, and impact.
- Status tracking: States reflect current stage (pending, approved, rejected).
- Audit trail: All actions are recorded with actor and timestamp.

```mermaid
flowchart TD
Start(["Start"]) --> Submit["Submit for review"]
Submit --> Review["Reviewer evaluates"]
Review --> Decision{"Decision"}
Decision --> |Approve| ApproveState["Set status: Approved"]
Decision --> |Reject| RejectState["Set status: Rejected"]
ApproveState --> Audit["Record audit event"]
RejectState --> Audit
Audit --> End(["End"])
```

**Diagram sources**
- [backend/app/services/schema_approval_service.py](file://backend/app/services/schema_approval_service.py)
- [backend/app/models/audit_log.py](file://backend/app/models/audit_log.py)

**Section sources**
- [backend/app/services/schema_approval_service.py](file://backend/app/services/schema_approval_service.py)
- [backend/app/models/audit_log.py](file://backend/app/models/audit_log.py)

### Migration Engine Architecture
The migration engine integrates with Alembic to execute versioned schema changes:
- Execution strategies: Supports forward (up) and backward (down) operations.
- Dependency resolution: Ensures migrations run in correct order based on versions and dependencies.
- Error handling: Catches failures, marks migrations as failed, and preserves state for recovery.
- Idempotency: Uses checkpoints to avoid reapplying completed steps.

```mermaid
flowchart TD
Entry(["Execute migration"]) --> Validate["Validate prerequisites and approvals"]
Validate --> Plan["Plan steps using Alembic"]
Plan --> ExecuteStep["Execute step"]
ExecuteStep --> StepOK{"Step succeeded?"}
StepOK --> |Yes| NextStep["Next step"]
NextStep --> MoreSteps{"More steps?"}
MoreSteps --> |Yes| ExecuteStep
MoreSteps --> |No| Finalize["Finalize: update checkpoints and snapshots"]
StepOK --> |No| HandleError["Handle error: mark failed, record audit"]
HandleError --> Exit(["Exit"])
Finalize --> Exit
```

**Diagram sources**
- [backend/app/services/migration_service.py](file://backend/app/services/migration_service.py)
- [backend/migrations/env.py](file://backend/migrations/env.py)
- [backend/migrations/script.py.mako](file://backend/migrations/script.py.mako)

**Section sources**
- [backend/app/services/migration_service.py](file://backend/app/services/migration_service.py)
- [backend/migrations/env.py](file://backend/migrations/env.py)
- [backend/migrations/script.py.mako](file://backend/migrations/script.py.mako)

### Rollback Mechanisms
Rollbacks provide safe reversal of applied migrations:
- Target selection: Choose specific versions or latest.
- Safety checks: Verify prerequisites and ensure no conflicting changes.
- Execution: Run down migrations with transactional semantics where possible.
- Verification: Post-rollback validation and snapshot comparison.

```mermaid
sequenceDiagram
participant Client as "Client"
participant Route as "Rollback Route"
participant RollbackSvc as "Rollback Service"
participant Engine as "Alembic Engine"
participant DB as "Database"
participant Audit as "Audit Log"
Client->>Route : "Initiate rollback"
Route->>RollbackSvc : "prepare_rollback(target)"
RollbackSvc->>DB : "Check current state"
RollbackSvc->>Engine : "Plan down steps"
RollbackSvc->>DB : "Execute down steps"
RollbackSvc->>DB : "Update checkpoints/snapshots"
RollbackSvc->>Audit : "Record rollback event"
RollbackSvc-->>Route : "Rollback result"
Route-->>Client : "Result"
```

**Diagram sources**
- [backend/app/routes/rollback.py](file://backend/app/routes/rollback.py)
- [backend/app/services/rollback_service.py](file://backend/app/services/rollback_service.py)
- [backend/app/models/migration_checkpoint.py](file://backend/app/models/migration_checkpoint.py)
- [backend/app/models/schema_snapshot.py](file://backend/app/models/schema_snapshot.py)
- [backend/app/models/audit_log.py](file://backend/app/models/audit_log.py)

**Section sources**
- [backend/app/routes/rollback.py](file://backend/app/routes/rollback.py)
- [backend/app/services/rollback_service.py](file://backend/app/services/rollback_service.py)
- [backend/app/models/migration_checkpoint.py](file://backend/app/models/migration_checkpoint.py)
- [backend/app/models/schema_snapshot.py](file://backend/app/models/schema_snapshot.py)
- [backend/app/models/audit_log.py](file://backend/app/models/audit_log.py)

### API Workflows

#### Create Migration
```mermaid
sequenceDiagram
participant Client as "Client"
participant Route as "Migration Route"
participant Svc as "Migration Service"
participant DB as "Database"
Client->>Route : "POST /migrations"
Route->>Svc : "create_migration(payload)"
Svc->>DB : "Insert migration record"
Svc-->>Route : "Migration ID"
Route-->>Client : "201 Created"
```

**Diagram sources**
- [backend/app/routes/migration.py](file://backend/app/routes/migration.py)
- [backend/app/services/migration_service.py](file://backend/app/services/migration_service.py)
- [backend/app/models/migration.py](file://backend/app/models/migration.py)

**Section sources**
- [backend/app/routes/migration.py](file://backend/app/routes/migration.py)
- [backend/app/services/migration_service.py](file://backend/app/services/migration_service.py)
- [backend/app/models/migration.py](file://backend/app/models/migration.py)

#### Approve Migration
```mermaid
sequenceDiagram
participant Client as "Client"
participant Route as "Schema Approval Route"
participant ApprovalSvc as "Schema Approval Service"
participant DB as "Database"
participant Audit as "Audit Log"
Client->>Route : "POST /approvals/{id}/approve"
Route->>ApprovalSvc : "approve(id, reviewer)"
ApprovalSvc->>DB : "Update approval status"
ApprovalSvc->>Audit : "Record approval event"
ApprovalSvc-->>Route : "Status updated"
Route-->>Client : "200 OK"
```

**Diagram sources**
- [backend/app/routes/schema_approval.py](file://backend/app/routes/schema_approval.py)
- [backend/app/services/schema_approval_service.py](file://backend/app/services/schema_approval_service.py)
- [backend/app/models/audit_log.py](file://backend/app/models/audit_log.py)

**Section sources**
- [backend/app/routes/schema_approval.py](file://backend/app/routes/schema_approval.py)
- [backend/app/services/schema_approval_service.py](file://backend/app/services/schema_approval_service.py)
- [backend/app/models/audit_log.py](file://backend/app/models/audit_log.py)

#### Execute Migration
```mermaid
sequenceDiagram
participant Client as "Client"
participant Route as "Migration Engine Route"
participant Svc as "Migration Service"
participant Engine as "Alembic Engine"
participant DB as "Database"
participant Audit as "Audit Log"
Client->>Route : "POST /migrations/{id}/execute"
Route->>Svc : "execute(id)"
Svc->>Engine : "Run up/down"
Engine->>DB : "Apply changes"
Svc->>DB : "Update checkpoints/snapshots"
Svc->>Audit : "Record execution event"
Svc-->>Route : "Execution result"
Route-->>Client : "Result"
```

**Diagram sources**
- [backend/app/routes/migration_engine.py](file://backend/app/routes/migration_engine.py)
- [backend/app/services/migration_service.py](file://backend/app/services/migration_service.py)
- [backend/app/models/migration_checkpoint.py](file://backend/app/models/migration_checkpoint.py)
- [backend/app/models/schema_snapshot.py](file://backend/app/models/schema_snapshot.py)
- [backend/app/models/audit_log.py](file://backend/app/models/audit_log.py)

**Section sources**
- [backend/app/routes/migration_engine.py](file://backend/app/routes/migration_engine.py)
- [backend/app/services/migration_service.py](file://backend/app/services/migration_service.py)
- [backend/app/models/migration_checkpoint.py](file://backend/app/models/migration_checkpoint.py)
- [backend/app/models/schema_snapshot.py](file://backend/app/models/schema_snapshot.py)
- [backend/app/models/audit_log.py](file://backend/app/models/audit_log.py)

### Practical Examples

- Creating a migration:
  - Use the create endpoint to generate a new migration entry and associated Alembic file.
  - Reference: [backend/app/routes/migration.py](file://backend/app/routes/migration.py), [backend/app/services/migration_service.py](file://backend/app/services/migration_service.py)

- Managing versions:
  - Track versions via the migration model and Alembic’s versioning.
  - Reference: [backend/app/models/migration.py](file://backend/app/models/migration.py), [backend/migrations/env.py](file://backend/migrations/env.py)

- Implementing rollback procedures:
  - Initiate rollback via the rollback route and service; verify post-rollback state.
  - Reference: [backend/app/routes/rollback.py](file://backend/app/routes/rollback.py), [backend/app/services/rollback_service.py](file://backend/app/services/rollback_service.py)

- Testing migrations:
  - Use test utilities to simulate execution and validate outcomes.
  - Reference: [backend/tests/test_migrations.py](file://backend/tests/test_migrations.py)

**Section sources**
- [backend/app/routes/migration.py](file://backend/app/routes/migration.py)
- [backend/app/services/migration_service.py](file://backend/app/services/migration_service.py)
- [backend/app/models/migration.py](file://backend/app/models/migration.py)
- [backend/migrations/env.py](file://backend/migrations/env.py)
- [backend/app/routes/rollback.py](file://backend/app/routes/rollback.py)
- [backend/app/services/rollback_service.py](file://backend/app/services/rollback_service.py)
- [backend/tests/test_migrations.py](file://backend/tests/test_migrations.py)

## Dependency Analysis
The migration subsystem exhibits clear separation of concerns:
- Routes depend on services for business logic.
- Services depend on models for persistence and Alembic for execution.
- Exceptions provide centralized error handling across layers.

```mermaid
graph LR
R1["Routes: migration.py"] --> S1["Service: migration_service.py"]
R2["Routes: schema_approval.py"] --> S2["Service: schema_approval_service.py"]
R3["Routes: rollback.py"] --> S3["Service: rollback_service.py"]
S1 --> M1["Model: migration.py"]
S1 --> M2["Model: migration_checkpoint.py"]
S1 --> M3["Model: schema_snapshot.py"]
S1 --> M4["Model: audit_log.py"]
S2 --> M4
S3 --> M2
S3 --> M3
S1 --> A1["Alembic: env.py"]
S1 --> A2["Alembic: script.py.mako"]
R1 --> E1["Exception: migration.py"]
R2 --> E2["Exception: schema_approval.py"]
R3 --> E3["Exception: rollback.py"]
```

**Diagram sources**
- [backend/app/routes/migration.py](file://backend/app/routes/migration.py)
- [backend/app/routes/schema_approval.py](file://backend/app/routes/schema_approval.py)
- [backend/app/routes/rollback.py](file://backend/app/routes/rollback.py)
- [backend/app/services/migration_service.py](file://backend/app/services/migration_service.py)
- [backend/app/services/schema_approval_service.py](file://backend/app/services/schema_approval_service.py)
- [backend/app/services/rollback_service.py](file://backend/app/services/rollback_service.py)
- [backend/app/models/migration.py](file://backend/app/models/migration.py)
- [backend/app/models/migration_checkpoint.py](file://backend/app/models/migration_checkpoint.py)
- [backend/app/models/schema_snapshot.py](file://backend/app/models/schema_snapshot.py)
- [backend/app/models/audit_log.py](file://backend/app/models/audit_log.py)
- [backend/app/exceptions/migration.py](file://backend/app/exceptions/migration.py)
- [backend/app/exceptions/schema_approval.py](file://backend/app/exceptions/schema_approval.py)
- [backend/app/exceptions/rollback.py](file://backend/app/exceptions/rollback.py)
- [backend/migrations/env.py](file://backend/migrations/env.py)
- [backend/migrations/script.py.mako](file://backend/migrations/script.py.mako)

**Section sources**
- [backend/app/routes/migration.py](file://backend/app/routes/migration.py)
- [backend/app/routes/schema_approval.py](file://backend/app/routes/schema_approval.py)
- [backend/app/routes/rollback.py](file://backend/app/routes/rollback.py)
- [backend/app/services/migration_service.py](file://backend/app/services/migration_service.py)
- [backend/app/services/schema_approval_service.py](file://backend/app/services/schema_approval_service.py)
- [backend/app/services/rollback_service.py](file://backend/app/services/rollback_service.py)
- [backend/app/models/migration.py](file://backend/app/models/migration.py)
- [backend/app/models/migration_checkpoint.py](file://backend/app/models/migration_checkpoint.py)
- [backend/app/models/schema_snapshot.py](file://backend/app/models/schema_snapshot.py)
- [backend/app/models/audit_log.py](file://backend/app/models/audit_log.py)
- [backend/app/exceptions/migration.py](file://backend/app/exceptions/migration.py)
- [backend/app/exceptions/schema_approval.py](file://backend/app/exceptions/schema_approval.py)
- [backend/app/exceptions/rollback.py](file://backend/app/exceptions/rollback.py)
- [backend/migrations/env.py](file://backend/migrations/env.py)
- [backend/migrations/script.py.mako](file://backend/migrations/script.py.mako)

## Performance Considerations
- Batch operations: Group small schema changes into single migrations to reduce round trips.
- Idempotent steps: Design steps to be rerunnable without side effects, improving retry resilience.
- Indexing strategy: Defer index creation to later steps to minimize write amplification during heavy writes.
- Connection pooling: Ensure database connections are pooled to handle concurrent migration requests efficiently.
- Snapshot size: Keep schema snapshots concise to reduce storage overhead and improve comparison performance.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and resolutions:
- Migration fails mid-execution:
  - Inspect checkpoints and snapshots to identify the last successful step.
  - Review audit logs for detailed error context.
  - Reference: [backend/app/models/migration_checkpoint.py](file://backend/app/models/migration_checkpoint.py), [backend/app/models/schema_snapshot.py](file://backend/app/models/schema_snapshot.py), [backend/app/models/audit_log.py](file://backend/app/models/audit_log.py)

- Approval stuck in pending:
  - Verify reviewer permissions and workflow policies.
  - Check audit trail for missing approvals.
  - Reference: [backend/app/services/schema_approval_service.py](file://backend/app/services/schema_approval_service.py), [backend/app/models/audit_log.py](file://backend/app/models/audit_log.py)

- Rollback conflicts:
  - Ensure no newer migrations are applied after the target version.
  - Validate preconditions and dependencies before initiating rollback.
  - Reference: [backend/app/services/rollback_service.py](file://backend/app/services/rollback_service.py)

- Alembic environment misconfiguration:
  - Confirm env.py settings and script template alignment.
  - Reference: [backend/migrations/env.py](file://backend/migrations/env.py), [backend/migrations/script.py.mako](file://backend/migrations/script.py.mako)

**Section sources**
- [backend/app/models/migration_checkpoint.py](file://backend/app/models/migration_checkpoint.py)
- [backend/app/models/schema_snapshot.py](file://backend/app/models/schema_snapshot.py)
- [backend/app/models/audit_log.py](file://backend/app/models/audit_log.py)
- [backend/app/services/schema_approval_service.py](file://backend/app/services/schema_approval_service.py)
- [backend/app/services/rollback_service.py](file://backend/app/services/rollback_service.py)
- [backend/migrations/env.py](file://backend/migrations/env.py)
- [backend/migrations/script.py.mako](file://backend/migrations/script.py.mako)

## Conclusion
CloudBridge’s migration system provides robust, auditable, and safe schema evolution through version-controlled migrations, structured approval workflows, and resilient execution and rollback mechanisms. By leveraging checkpoints, snapshots, and comprehensive logging, teams can confidently manage complex database changes while maintaining data integrity and operational visibility.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### Best Practices for Safe Schema Evolution
- Prefer additive changes: Add columns and indexes before removing deprecated ones.
- Backward-compatible APIs: Ensure application code remains compatible during transitions.
- Small, focused migrations: Each migration should address a single concern.
- Pre-flight checks: Validate dependencies and environment readiness before execution.
- Automated testing: Include unit and integration tests for critical schema changes.
- Rollback drills: Regularly practice rollback procedures to ensure reliability.

[No sources needed since this section provides general guidance]