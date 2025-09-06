import os

# Configuração do banco central de licenças
LICENCA_DB_CONFIG = {
    'host': os.getenv('LICENCA_DB_HOST', '216.238.116.111'),
    'port': os.getenv('LICENCA_DB_PORT', '5432'),
    'dbname': os.getenv('LICENCA_DB_NAME', 'licenca'),
    'user': os.getenv('LICENCA_DB_USER', 'postgres'),
    'password': os.getenv('LICENCA_DB_PASSWORD', 'brinkoo2025')
}

TENANT_DB_CONFIG = {
    'host': '216.238.116.111',
    'port': '5432',
    'user': 'postgres',
    'password': 'brinkoo2025'
}
