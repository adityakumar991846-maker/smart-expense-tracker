"""
Package initialization for config.
Hooks PyMySQL as MySQLdb driver if available to ensure MySQL support
works out of the box across environments.
"""
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass
