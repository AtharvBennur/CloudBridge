from logging.config import fileConfig

from alembic import context

from app import create_app
from app.extensions import db

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

flask_app = create_app()
target_metadata = db.metadata


def get_database_url() -> str:
    return flask_app.config["SQLALCHEMY_DATABASE_URI"]


def run_migrations_offline() -> None:
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with flask_app.app_context():
        connectable = db.engine
        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
