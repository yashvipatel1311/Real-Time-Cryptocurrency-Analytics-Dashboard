"""
Database Package for Real-Time Cryptocurrency Analytics Platform.

This package provides:
    - db_connection: SQLAlchemy engine, session management, and connection testing.
    - create_tables: ORM model definitions and table creation/drop utilities.
    - schema.sql: Raw SQL DDL for PostgreSQL (reference / manual setup).

Usage:
    from database.db_connection import get_engine, get_session, test_connection
    from database.create_tables import create_all_tables, drop_all_tables
"""
