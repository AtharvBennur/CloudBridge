"""Packaged Lambda handlers for CloudBridge MySQL migrations.

The orchestrator is invoked once by Render.  It discovers real MySQL schema and
queues bounded chunks; the SQS worker is idempotent and reports durable progress
to the CloudBridge API.  Database credentials are read only from Secrets Manager.
"""
import json
import os
import re
import urllib.request

import boto3
import pymysql
from boto3.dynamodb.conditions import Key

TABLE = boto3.resource("dynamodb").Table(os.environ["MIGRATION_METADATA_TABLE"])
SQS = boto3.client("sqs")
IDENTIFIER = re.compile(r"^[A-Za-z0-9_$]+$")


def _quote(name):
    if not IDENTIFIER.match(name or ""):
        raise ValueError("Unsafe MySQL identifier")
    return "`%s`" % name


def _secret(arn):
    return json.loads(boto3.client("secretsmanager").get_secret_value(SecretId=arn)["SecretString"])


def _db(config):
    if config.get("db_type", "").upper() != "MYSQL":
        raise ValueError("Only MySQL migrations are supported by this stack")
    return pymysql.connect(host=config["host"], port=int(config["port"]), user=config["username"], password=config["password"], database=config["database_name"], connect_timeout=10, autocommit=False)


def _report(payload):
    url = os.environ["CLOUDBRIDGE_API_URL"].rstrip("/") + "/migration-engine/status-update"
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST", headers={"Content-Type": "application/json", "X-CloudBridge-Worker-Secret": os.environ["WORKER_API_SECRET"]})
    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status >= 300:
            raise RuntimeError("CloudBridge progress callback rejected: %s" % response.status)


def validation_handler(event, context):
    config = event["config"]
    connection = _db(config)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchmany(5)]
        return {"status": "success", "tables": tables}
    finally:
        connection.close()


def orchestrator_handler(event, context):
    if event.get("action") != "run_migration":
        raise ValueError("Unsupported orchestrator action")
    migration_id = str(event["migration_id"])
    source_arn, destination_arn = event["source_secret_arn"], event["destination_secret_arn"]
    source = _secret(source_arn)
    chunk_size = max(1, min(int(event.get("chunk_size") or 10000), 50000))
    source_db = _db(source)
    chunks = []
    try:
        with source_db.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            for row in cursor.fetchall():
                table = row[0]
                cursor.execute("SELECT COUNT(*) FROM " + _quote(table))
                count = int(cursor.fetchone()[0])
                cursor.execute("SHOW CREATE TABLE " + _quote(table))
                create_sql = cursor.fetchone()[1]
                for offset in range(0, count, chunk_size):
                    chunks.append({"migration_id": migration_id, "chunk_id": "%s#%s#%s" % (migration_id, table, offset), "table_name": table, "offset": offset, "limit": min(chunk_size, count - offset), "total_rows": count, "create_sql": create_sql, "source_secret_arn": source_arn, "destination_secret_arn": destination_arn})
    finally:
        source_db.close()
    if not chunks:
        _report({"migration_id": migration_id, "status": "COMPLETED", "current_stage": "COMPLETED", "progress_percent": 100, "rows_migrated": 0, "total_rows": 0, "chunks_total": 0, "chunks_completed": 0, "chunks_failed": 0})
        return {"status": "success", "chunks": 0}
    for chunk in chunks:
        TABLE.put_item(Item={"migration_id": migration_id, "chunk_id": chunk["chunk_id"], "status": "PENDING", "rows_migrated": 0, "table_name": chunk["table_name"]})
        SQS.send_message(QueueUrl=os.environ["CHUNK_QUEUE_URL"], MessageBody=json.dumps(chunk))
    _report({"migration_id": migration_id, "status": "RUNNING", "current_stage": "MIGRATING", "progress_percent": 0, "rows_migrated": 0, "total_rows": sum(c["limit"] for c in chunks), "chunks_total": len(chunks), "chunks_completed": 0, "chunks_failed": 0})
    return {"status": "success", "chunks": len(chunks)}


def worker_handler(event, context):
    for record in event["Records"]:
        chunk = json.loads(record["body"])
        _migrate_chunk(chunk, context.aws_request_id)


def _migrate_chunk(chunk, request_id):
    key = {"migration_id": chunk["migration_id"], "chunk_id": chunk["chunk_id"]}
    current = TABLE.get_item(Key=key).get("Item", {})
    if current.get("status") == "COMPLETED":
        return
    TABLE.update_item(Key=key, UpdateExpression="SET #s=:s, request_id=:r", ExpressionAttributeNames={"#s": "status"}, ExpressionAttributeValues={":s": "RUNNING", ":r": request_id})
    source, destination = _db(_secret(chunk["source_secret_arn"])), _db(_secret(chunk["destination_secret_arn"]))
    try:
        with source.cursor() as read_cursor, destination.cursor() as write_cursor:
            write_cursor.execute(chunk["create_sql"])
            read_cursor.execute("SELECT * FROM %s LIMIT %%s OFFSET %%s" % _quote(chunk["table_name"]), (chunk["limit"], chunk["offset"]))
            rows = read_cursor.fetchall()
            columns = [d[0] for d in read_cursor.description]
            if rows:
                quoted = ", ".join(_quote(c) for c in columns)
                placeholders = ", ".join(["%s"] * len(columns))
                updates = ", ".join("%s=VALUES(%s)" % (_quote(c), _quote(c)) for c in columns)
                write_cursor.executemany("INSERT INTO %s (%s) VALUES (%s) ON DUPLICATE KEY UPDATE %s" % (_quote(chunk["table_name"]), quoted, placeholders, updates), rows)
        destination.commit()
        TABLE.update_item(Key=key, UpdateExpression="SET #s=:s, rows_migrated=:r", ExpressionAttributeNames={"#s": "status"}, ExpressionAttributeValues={":s": "COMPLETED", ":r": len(rows)})
    except Exception as exc:
        destination.rollback()
        TABLE.update_item(Key=key, UpdateExpression="SET #s=:s, error=:e", ExpressionAttributeNames={"#s": "status"}, ExpressionAttributeValues={":s": "FAILED", ":e": str(exc)[:1000]})
        raise
    finally:
        source.close(); destination.close()
    items = TABLE.query(KeyConditionExpression=Key("migration_id").eq(chunk["migration_id"]))["Items"]
    total, completed = len(items), [x for x in items if x.get("status") == "COMPLETED"]
    failed = [x for x in items if x.get("status") == "FAILED"]
    rows_done = sum(int(x.get("rows_migrated", 0)) for x in completed)
    done = total > 0 and len(completed) == total
    _report({"migration_id": chunk["migration_id"], "status": "COMPLETED" if done else "RUNNING", "current_stage": "COMPLETED" if done else "MIGRATING", "progress_percent": (100.0 * len(completed) / total) if total else 0, "rows_migrated": rows_done, "chunks_total": total, "chunks_completed": len(completed), "chunks_failed": len(failed), "current_table": chunk["table_name"]})
