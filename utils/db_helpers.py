import json
from datetime import date, datetime

from datetime import date, datetime
from decimal import Decimal
import json

def select_dict(cursor, query: str, params=None):
    """
    Executa SELECT e retorna resultado como lista de dicionários.
    Converte automaticamente:
    - Datas para strings no formato ISO
    - JSON strings para objetos Python (se claramente for JSON)
    - Decimal para float
    - Mantém tipos originais sempre que possível
    """
    cursor.execute(query, params or ())
    rows = cursor.fetchall()
    colunas = [desc[0] for desc in cursor.description]
    
    def convert_value(value):
        if value is None:
            return None
        elif isinstance(value, (date, datetime)):
            return value.isoformat()
        elif isinstance(value, Decimal):
            # Converte para float (ou str se quiser evitar perda de precisão)
            return float(value)
        elif isinstance(value, (dict, list)):
            return value
        elif isinstance(value, str):
            # Só tenta json.loads se a string parecer JSON
            if value.strip().startswith(('{', '[', '"')):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    return value
            return value
        elif hasattr(value, '__dict__'):
            return vars(value)
        else:
            return value  # Mantém o tipo original
    
    result = []
    for row in rows:
        row_dict = {}
        for col_name, value in zip(colunas, row):
            row_dict[col_name] = convert_value(value)
        result.append(row_dict)
    
    return result

def generate_insert_sql(table: str, data: dict, returning: str = None):
    colunas = list(data.keys())
    valores = list(data.values())
    placeholders = ", ".join(["%s"] * len(colunas))
    colunas_sql = ", ".join(colunas)

    sql = f"INSERT INTO {table} ({colunas_sql}) VALUES ({placeholders})"

    if returning:
        sql += f" RETURNING {returning}"

    return sql, valores



def generate_update_sql(table: str, data: dict, where_keys: list, where_values: list = None, returning: str = None):
    # Filtra colunas para atualizar (excluindo as usadas no WHERE)
    set_cols = [k for k in data.keys() if k not in where_keys]
    
    # Gera a cláusula SET
    set_clause = ", ".join([f"{col} = %s" for col in set_cols])
    
    # Gera a cláusula WHERE
    where_clause = " AND ".join([f"{col} = %s" for col in where_keys])

    sql = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"

    # Prepara os valores na ordem correta: primeiro SET, depois WHERE
    valores = []
    
    # Valores para SET
    for col in set_cols:
        val = data[col]
        # Converte explicitamente None para NULL do SQL
        valores.append(val if val is not None else None)
    
    # Valores para WHERE (usando where_values se fornecido, senão do data)
    if where_values:
        valores.extend(where_values)
    else:
        for col in where_keys:
            val = data.get(col)
            valores.append(val if val is not None else None)
    
    if returning:
        sql += f" RETURNING {returning}"
    
    return sql, valores
