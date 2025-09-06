import psycopg2
from config import LICENCA_DB_CONFIG, TENANT_DB_CONFIG


def get_licenca_connection():
    """Retorna uma conexão com o banco de licenças"""
    return psycopg2.connect(**LICENCA_DB_CONFIG)


def conectar_banco_empresa(nome_banco: str):
    """Conecta ao banco de dados de uma empresa"""
    config = {
        **TENANT_DB_CONFIG,
        'dbname': nome_banco
    }
    return psycopg2.connect(**config)
