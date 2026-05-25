from django.db.backends.mysql.base import DatabaseWrapper as MySQLDatabaseWrapper
from django.db.backends.mysql.features import DatabaseFeatures as MySQLDatabaseFeatures
from django.utils.functional import cached_property
from operator import attrgetter


class DatabaseFeatures(MySQLDatabaseFeatures):
    @cached_property
    def minimum_database_version(self):
        if self.connection.mysql_is_mariadb:
            return (10, 4)
        return super().minimum_database_version

    @cached_property
    def can_return_columns_from_insert(self):
        if self.connection.mysql_is_mariadb:
            return self.connection.mysql_version >= (10, 5)
        return super().can_return_columns_from_insert

    can_return_rows_from_bulk_insert = property(attrgetter("can_return_columns_from_insert"))


class DatabaseWrapper(MySQLDatabaseWrapper):
    features_class = DatabaseFeatures
