from utils.db import get_licenca_connection

def carregar_empresas_ativas():
    """Carrega as empresas ativas do banco de licenças"""
    empresas = []

    try:
        conn = get_licenca_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, cnpj FROM empresa WHERE ativo = TRUE;")
        rows = cursor.fetchall()

        for row in rows:
            empresas.append({
                'id': row[0],
                'nome': row[1],
                'cnpj': row[2]
            })

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[ERRO] Falha ao carregar licenças: {e}")

    return empresas


def validar_tenant(cnpj: str, empresas_ativas: list) -> dict | None:
    if not cnpj:
        return None

    return next((e for e in empresas_ativas if e["cnpj"] == cnpj), None)

