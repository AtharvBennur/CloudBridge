"""Schema Discovery Service — discovers and migrates database schemas.

This service handles:
- Discovering source database schema (tables, columns, indexes, foreign keys)
- Creating destination schema
- Detecting schema drift between source and destination
- Generating DDL statements for schema migration
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from app.services.validators import get_validator

logger = logging.getLogger(__name__)


class ColumnType(Enum):
    """Supported column types."""
    INTEGER = "integer"
    VARCHAR = "varchar"
    TEXT = "text"
    DECIMAL = "decimal"
    DATE = "date"
    DATETIME = "datetime"
    TIMESTAMP = "timestamp"
    BOOLEAN = "boolean"
    FLOAT = "float"
    JSON = "json"
    BLOB = "blob"


@dataclass
class ColumnInfo:
    """Information about a database column."""
    name: str
    type: str
    nullable: bool
    default: Optional[str]
    max_length: Optional[int]
    precision: Optional[int]
    scale: Optional[int]
    is_primary_key: bool
    is_auto_increment: bool


@dataclass
class TableInfo:
    """Information about a database table."""
    name: str
    columns: List[ColumnInfo]
    row_count: Optional[int]
    indexes: List[Dict[str, Any]]
    foreign_keys: List[Dict[str, Any]]
    primary_keys: List[str]


@dataclass
class SchemaInfo:
    """Complete database schema information."""
    database_name: str
    tables: List[TableInfo]
    collation: Optional[str]
    charset: Optional[str]


class SchemaDiscoveryService:
    """Service for discovering and migrating database schemas."""

    def discover_schema(
        self,
        database_type: str,
        host: str,
        port: int,
        username: str,
        password: str,
        database_name: str,
    ) -> SchemaInfo:
        """Discover the complete schema of a database.
        
        Args:
            database_type: Type of database (mysql, postgresql)
            host: Database host
            port: Database port
            username: Database username
            password: Database password
            database_name: Name of the database
            
        Returns:
            SchemaInfo containing complete schema information
        """
        logger.info("Discovering schema for database: %s", database_name)
        
        validator = get_validator(database_type, host, port, username, password, database_name, timeout=300)
        
        try:
            validator.connect()
            
            # Discover tables
            tables = self._discover_tables(validator, database_type)
            
            # For each table, discover detailed schema
            table_infos = []
            for table_name in tables:
                table_info = self._discover_table_schema(validator, table_name, database_type)
                table_infos.append(table_info)
            
            schema_info = SchemaInfo(
                database_name=database_name,
                tables=table_infos,
                collation=None,  # TODO: Discover collation
                charset=None,    # TODO: Discover charset
            )
            
            logger.info("Schema discovery completed: %d tables discovered", len(table_infos))
            return schema_info
            
        finally:
            validator.close()

    def _discover_tables(self, validator: Any, database_type: str) -> List[str]:
        """Discover all tables in the database."""
        try:
            if database_type.lower() == "mysql":
                return validator.discover_tables()
            elif database_type.lower() == "postgresql":
                # PostgreSQL table discovery
                query = """
                    SELECT tablename 
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                    ORDER BY tablename
                """
                with validator.connection.cursor() as cursor:
                    cursor.execute(query)
                    return [row[0] for row in cursor.fetchall()]
            else:
                raise ValueError(f"Unsupported database type: {database_type}")
        except Exception as exc:
            logger.error("Failed to discover tables: %s", exc)
            raise

    def _discover_table_schema(self, validator: Any, table_name: str, database_type: str) -> TableInfo:
        """Discover detailed schema for a single table."""
        logger.debug("Discovering schema for table: %s", table_name)
        
        columns = self._discover_columns(validator, table_name, database_type)
        row_count = self._get_row_count(validator, table_name, database_type)
        indexes = self._discover_indexes(validator, table_name, database_type)
        foreign_keys = self._discover_foreign_keys(validator, table_name, database_type)
        primary_keys = self._discover_primary_keys(validator, table_name, database_type)
        
        return TableInfo(
            name=table_name,
            columns=columns,
            row_count=row_count,
            indexes=indexes,
            foreign_keys=foreign_keys,
            primary_keys=primary_keys,
        )

    def _discover_columns(self, validator: Any, table_name: str, database_type: str) -> List[ColumnInfo]:
        """Discover column information for a table."""
        columns = []
        
        try:
            if database_type.lower() == "mysql":
                query = f"""
                    SELECT 
                        COLUMN_NAME,
                        DATA_TYPE,
                        IS_NULLABLE,
                        COLUMN_DEFAULT,
                        CHARACTER_MAXIMUM_LENGTH,
                        NUMERIC_PRECISION,
                        NUMERIC_SCALE,
                        COLUMN_KEY,
                        EXTRA
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table_name}'
                    ORDER BY ORDINAL_POSITION
                """
                with validator.connection.cursor() as cursor:
                    cursor.execute(query)
                    for row in cursor.fetchall():
                        columns.append(ColumnInfo(
                            name=row[0],
                            type=row[1],
                            nullable=row[2] == "YES",
                            default=row[3],
                            max_length=row[4],
                            precision=row[5],
                            scale=row[6],
                            is_primary_key=row[7] == "PRI",
                            is_auto_increment="auto_increment" in (row[8] or ""),
                        ))
            
            elif database_type.lower() == "postgresql":
                query = f"""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length,
                        numeric_precision,
                        numeric_scale
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE table_schema = 'public' AND table_name = '{table_name}'
                    ORDER BY ordinal_position
                """
                with validator.connection.cursor() as cursor:
                    cursor.execute(query)
                    for row in cursor.fetchall():
                        columns.append(ColumnInfo(
                            name=row[0],
                            type=row[1],
                            nullable=row[2] == "YES",
                            default=row[3],
                            max_length=row[4],
                            precision=row[5],
                            scale=row[6],
                            is_primary_key=False,  # TODO: Discover primary keys separately
                            is_auto_increment=False,  # TODO: Discover auto increment
                        ))
            
        except Exception as exc:
            logger.error("Failed to discover columns for table %s: %s", table_name, exc)
            raise
        
        return columns

    def _get_row_count(self, validator: Any, table_name: str, database_type: str) -> Optional[int]:
        """Get the row count for a table."""
        try:
            if database_type.lower() == "mysql":
                query = f"SELECT COUNT(*) FROM `{table_name}`"
            elif database_type.lower() == "postgresql":
                query = f'SELECT COUNT(*) FROM "{table_name}"'
            else:
                return None
            
            with validator.connection.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as exc:
            logger.warning("Failed to get row count for table %s: %s", table_name, exc)
            return None

    def _discover_indexes(self, validator: Any, table_name: str, database_type: str) -> List[Dict[str, Any]]:
        """Discover indexes for a table."""
        indexes = []
        
        try:
            if database_type.lower() == "mysql":
                query = f"""
                    SELECT 
                        INDEX_NAME,
                        COLUMN_NAME,
                        NON_UNIQUE,
                        SEQ_IN_INDEX
                    FROM INFORMATION_SCHEMA.STATISTICS
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table_name}'
                    ORDER BY INDEX_NAME, SEQ_IN_INDEX
                """
                with validator.connection.cursor() as cursor:
                    cursor.execute(query)
                    for row in cursor.fetchall():
                        indexes.append({
                            "name": row[0],
                            "column": row[1],
                            "unique": row[2] == 0,
                            "sequence": row[3],
                        })
            
            elif database_type.lower() == "postgresql":
                query = f"""
                    SELECT 
                        i.relname as index_name,
                        a.attname as column_name,
                        ix.indisunique as is_unique
                    FROM pg_class t
                    JOIN pg_index ix ON t.oid = ix.indrelid
                    JOIN pg_class i ON i.oid = ix.indexrelid
                    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
                    WHERE t.relname = '{table_name}'
                """
                with validator.connection.cursor() as cursor:
                    cursor.execute(query)
                    for row in cursor.fetchall():
                        indexes.append({
                            "name": row[0],
                            "column": row[1],
                            "unique": row[2],
                        })
            
        except Exception as exc:
            logger.warning("Failed to discover indexes for table %s: %s", table_name, exc)
        
        return indexes

    def _discover_foreign_keys(self, validator: Any, table_name: str, database_type: str) -> List[Dict[str, Any]]:
        """Discover foreign key constraints for a table."""
        foreign_keys = []
        
        try:
            if database_type.lower() == "mysql":
                query = f"""
                    SELECT 
                        CONSTRAINT_NAME,
                        COLUMN_NAME,
                        REFERENCED_TABLE_NAME,
                        REFERENCED_COLUMN_NAME
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                    WHERE TABLE_SCHEMA = DATABASE() 
                        AND TABLE_NAME = '{table_name}'
                        AND REFERENCED_TABLE_NAME IS NOT NULL
                """
                with validator.connection.cursor() as cursor:
                    cursor.execute(query)
                    for row in cursor.fetchall():
                        foreign_keys.append({
                            "name": row[0],
                            "column": row[1],
                            "referenced_table": row[2],
                            "referenced_column": row[3],
                        })
            
            elif database_type.lower() == "postgresql":
                query = f"""
                    SELECT
                        tc.constraint_name,
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND tc.table_name = '{table_name}'
                """
                with validator.connection.cursor() as cursor:
                    cursor.execute(query)
                    for row in cursor.fetchall():
                        foreign_keys.append({
                            "name": row[0],
                            "column": row[1],
                            "referenced_table": row[2],
                            "referenced_column": row[3],
                        })
            
        except Exception as exc:
            logger.warning("Failed to discover foreign keys for table %s: %s", table_name, exc)
        
        return foreign_keys

    def _discover_primary_keys(self, validator: Any, table_name: str, database_type: str) -> List[str]:
        """Discover primary key columns for a table."""
        primary_keys = []
        
        try:
            if database_type.lower() == "mysql":
                query = f"""
                    SELECT COLUMN_NAME
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                    WHERE TABLE_SCHEMA = DATABASE() 
                        AND TABLE_NAME = '{table_name}'
                        AND CONSTRAINT_NAME = 'PRIMARY'
                    ORDER BY ORDINAL_POSITION
                """
                with validator.connection.cursor() as cursor:
                    cursor.execute(query)
                    primary_keys = [row[0] for row in cursor.fetchall()]
            
            elif database_type.lower() == "postgresql":
                query = f"""
                    SELECT a.attname
                    FROM pg_index i
                    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                    WHERE i.indrelid = '{table_name}'::regclass
                        AND i.indisprimary
                """
                with validator.connection.cursor() as cursor:
                    cursor.execute(query)
                    primary_keys = [row[0] for row in cursor.fetchall()]
            
        except Exception as exc:
            logger.warning("Failed to discover primary keys for table %s: %s", table_name, exc)
        
        return primary_keys

    def generate_create_table_ddl(self, table_info: TableInfo, database_type: str) -> str:
        """Generate CREATE TABLE DDL statement for a table."""
        column_defs = []
        
        for col in table_info.columns:
            col_def = f"`{col.name}` {col.type}"
            
            if col.max_length and col.type in ["varchar", "char"]:
                col_def += f"({col.max_length})"
            elif col.precision and col.scale and col.type in ["decimal", "numeric"]:
                col_def += f"({col.precision},{col.scale})"
            
            if not col.nullable:
                col_def += " NOT NULL"
            
            if col.default:
                col_def += f" DEFAULT {col.default}"
            
            if col.is_auto_increment:
                col_def += " AUTO_INCREMENT"
            
            if col.is_primary_key and len(table_info.primary_keys) == 1:
                col_def += " PRIMARY KEY"
            
            column_defs.append(col_def)
        
        # Add primary key constraint if composite
        if len(table_info.primary_keys) > 1:
            pk_cols = ", ".join([f"`{pk}`" for pk in table_info.primary_keys])
            column_defs.append(f"PRIMARY KEY ({pk_cols})")
        
        ddl = f"CREATE TABLE `{table_info.name}` (\n"
        ddl += ",\n".join(f"    {col_def}" for col_def in column_defs)
        ddl += "\n)"
        
        return ddl

    def compare_schemas(self, source_schema: SchemaInfo, dest_schema: SchemaInfo) -> Dict[str, Any]:
        """Compare two schemas and detect differences.
        
        Returns:
            Dictionary containing:
            - new_tables: Tables in source but not in destination
            - removed_tables: Tables in destination but not in source
            - modified_tables: Tables with schema differences
            - table_differences: Detailed differences per table
        """
        source_table_names = {table.name for table in source_schema.tables}
        dest_table_names = {table.name for table in dest_schema.tables}
        
        new_tables = source_table_names - dest_table_names
        removed_tables = dest_table_names - source_table_names
        common_tables = source_table_names & dest_table_names
        
        modified_tables = set()
        table_differences = {}
        
        for table_name in common_tables:
            source_table = next(t for t in source_schema.tables if t.name == table_name)
            dest_table = next(t for t in dest_schema.tables if t.name == table_name)
            
            differences = self._compare_tables(source_table, dest_table)
            if differences:
                modified_tables.add(table_name)
                table_differences[table_name] = differences
        
        return {
            "new_tables": sorted(new_tables),
            "removed_tables": sorted(removed_tables),
            "modified_tables": sorted(modified_tables),
            "table_differences": table_differences,
        }

    def _compare_tables(self, source_table: TableInfo, dest_table: TableInfo) -> Dict[str, Any]:
        """Compare two tables and return differences."""
        differences = {
            "new_columns": [],
            "removed_columns": [],
            "modified_columns": [],
            "new_indexes": [],
            "removed_indexes": [],
            "new_foreign_keys": [],
            "removed_foreign_keys": [],
        }
        
        # Compare columns
        source_columns = {col.name: col for col in source_table.columns}
        dest_columns = {col.name: col for col in dest_table.columns}
        
        differences["new_columns"] = sorted(source_columns.keys() - dest_columns.keys())
        differences["removed_columns"] = sorted(dest_columns.keys() - source_columns.keys())
        
        for col_name in source_columns.keys() & dest_columns.keys():
            source_col = source_columns[col_name]
            dest_col = dest_columns[col_name]
            
            if (source_col.type != dest_col.type or
                source_col.nullable != dest_col.nullable or
                source_col.max_length != dest_col.max_length):
                differences["modified_columns"].append(col_name)
        
        # Compare indexes
        source_index_names = {idx["name"] for idx in source_table.indexes}
        dest_index_names = {idx["name"] for idx in dest_table.indexes}
        
        differences["new_indexes"] = sorted(source_index_names - dest_index_names)
        differences["removed_indexes"] = sorted(dest_index_names - source_index_names)
        
        # Compare foreign keys
        source_fk_names = {fk["name"] for fk in source_table.foreign_keys}
        dest_fk_names = {fk["name"] for fk in dest_table.foreign_keys}
        
        differences["new_foreign_keys"] = sorted(source_fk_names - dest_fk_names)
        differences["removed_foreign_keys"] = sorted(dest_fk_names - source_fk_names)
        
        # Return differences only if there are any
        if any(differences.values()):
            return differences
        
        return {}
