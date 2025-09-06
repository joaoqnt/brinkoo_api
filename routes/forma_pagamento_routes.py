from flask import Blueprint, jsonify, request, g
from utils.db_helpers import select_dict, generate_insert_sql, generate_update_sql

forma_pagamento_bp = Blueprint("forma_pagamento_routes", __name__)

def build_query(filtros: dict = None, limit: int = None, offset: int = None):
    base_query = """
        SELECT 
            f.* 
        FROM forma_pagamento f
    """
    where_clauses = []
    params = []

    if filtros:
        if filtros.get('id') is not None:
            where_clauses.append("id = %s")
            params.append(filtros['id'])

        if filtros.get('descricao'):
            search_term = filtros['descricao'].lower().strip()
            where_clauses.append("unaccent(lower(descricao)) LIKE unaccent(lower(%s))")
            params.append(f"%{search_term}%")

        if filtros.get('ativo') is not None:
            where_clauses.append("ativo = %s")
            params.append(filtros['ativo'])

    query = base_query

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    if filtros and filtros.get('descricao'):
        query += " ORDER BY similarity(unaccent(lower(descricao)), unaccent(lower(%s))) DESC"
        params.append(filtros['descricao'].lower())
    else:
        query += " ORDER BY id DESC"

    if limit is not None:
        query += " LIMIT %s"
        params.append(limit)

    if offset is not None:
        query += " OFFSET %s"
        params.append(offset)

    return query, params

@forma_pagamento_bp.route("/forma_pagamento", methods=["GET"])
def listar_formas_pagamento():
    try:
        filtros = {
            "id": request.args.get("id", type=int),
            "descricao": request.args.get("descricao"),
            "ativo": request.args.get("ativo", type=lambda v: v.lower() == 'true' if v else None)
        }
        filtros = {k: v for k, v in filtros.items() if v is not None}

        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", type=int)

        query, params = build_query(filtros=filtros, limit=limit, offset=offset)

        cursor = g.conn.cursor()
        formas = select_dict(cursor, query, params)
        cursor.close()

        return jsonify(formas)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@forma_pagamento_bp.route("/forma_pagamento", methods=["POST"])
def criar_forma_pagamento():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        if 'id' in data and data['id'] is None:
            data.pop('id')

        sql, params = generate_insert_sql("forma_pagamento", data, returning="id")
        cursor = g.conn.cursor()
        cursor.execute(sql, params)
        forma_id = cursor.fetchone()[0]
        g.conn.commit()
        cursor.close()

        return jsonify({"id": forma_id, "mensagem": "Forma de pagamento criada com sucesso"}), 201
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500

@forma_pagamento_bp.route("/forma_pagamento/<int:forma_id>", methods=["PUT"])
def atualizar_forma_pagamento(forma_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        sql, params = generate_update_sql(
            "forma_pagamento",
            data,
            where_keys=['id'],
            where_values=[forma_id]
        )
        cursor = g.conn.cursor()
        cursor.execute(sql, params)
        g.conn.commit()
        cursor.close()

        return jsonify({"mensagem": "Forma de pagamento atualizada com sucesso"})
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500

@forma_pagamento_bp.route("/forma_pagamento/<int:forma_id>", methods=["DELETE"])
def deletar_forma_pagamento(forma_id):
    try:
        cursor = g.conn.cursor()
        cursor.execute("DELETE FROM forma_pagamento WHERE id = %s", (forma_id,))
        g.conn.commit()
        cursor.close()
        return jsonify({"mensagem": "Forma de pagamento removida com sucesso"})
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500
