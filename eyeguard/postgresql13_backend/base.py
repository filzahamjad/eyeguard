"""
PostgreSQL backend that allows PostgreSQL 13 (Django 5.2+ normally requires 14+).
Re-exports django.db.backends.postgresql.base with a DatabaseWrapper that uses
minimum_database_version = (13,).
"""
from django.db.backends.postgresql.base import *  # noqa: F401, F403
from django.db.backends.postgresql.base import DatabaseWrapper as _BaseDatabaseWrapper
from django.db.backends.postgresql import features as _pg_features


class DatabaseFeatures(_pg_features.DatabaseFeatures):
    minimum_database_version = (13,)


class DatabaseWrapper(_BaseDatabaseWrapper):
    features_class = DatabaseFeatures
