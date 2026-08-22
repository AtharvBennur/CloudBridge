from app import create_app


def test_generate_template_includes_dynamodb_and_required_outputs() -> None:
    app = create_app("testing")
    app.config["CLOUDBRIDGE_AWS_ACCOUNT_ID"] = "999999999999"
    client = app.test_client()

    create_response = client.post(
        "/aws-connections",
        json={
            "aws_account_id": "123456789012",
            "aws_region": "us-east-1",
        },
        headers={"Authorization": f"Bearer {__import__('app.middleware.auth', fromlist=['encode_token']).encode_token('test-user', 'test@example.com', 'Test User')}"},
    )
    connection_id = create_response.get_json()["id"]

    response = client.get(
        f"/aws-connections/{connection_id}/cloudformation-template",
        headers={"Authorization": f"Bearer {__import__('app.middleware.auth', fromlist=['encode_token']).encode_token('test-user', 'test@example.com', 'Test User')}"},
    )
    assert response.status_code == 200
    template = response.get_json()["template"]

    resources = template["Resources"]
    assert "MetadataTable" in resources
    metadata_properties = resources["MetadataTable"]["Properties"]
    assert metadata_properties["BillingMode"] == "PAY_PER_REQUEST"
    assert "ProvisionedThroughput" not in metadata_properties
    assert "MigrationOrchestratorLambda" in resources
    assert "MigrationWorkerLambda" in resources
    assert "ValidationLambda" in resources
    assert "_LAMBDA_PLACEHOLDER_CODE" not in str(template)

    role_policy = resources["CloudBridgeMigrationRole"]["Properties"]["Policies"][0]["PolicyDocument"]["Statement"]
    discovery_statement = next(item for item in role_policy if item.get("Sid") == "CloudFormationDiscovery")
    assert discovery_statement["Action"] == ["cloudformation:DescribeStacks"]

    outputs = template["Outputs"]
    assert set(
        [
            "MigrationRoleArn",
            "MigrationOrchestratorLambdaArn",
            "MigrationWorkerLambdaArn",
            "ValidationLambdaArn",
            "MigrationMetadataTableName",
        ]
    ).issubset(outputs.keys())
