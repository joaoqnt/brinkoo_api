from flask import Blueprint, jsonify, request, g
from utils.db_helpers import select_dict, generate_insert_sql, generate_update_sql

natureza_bp = Blueprint("natureza_routes", __name__)

def build_query(filtros: dict = None, limit: int = None, offset: int = None):
    base_query = """
        SELECT * FROM natureza
    """
    where_clauses = []
    params = []

    if filtros:
        if filtros.get('id'):
            where_clauses.append("id = %s")
            params.append(filtros['id'])

        if filtros.get('descricao'):
            search_term = filtros['descricao'].lower().strip()
            where_clauses.append("unaccent(lower(descricao)) LIKE unaccent(lower(%s))")
            params.append(f"%{search_term}%")

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

@natureza_bp.route("/naturezas", methods=["GET"])
def listar_naturezas():
    try:
        filtros = {
            "id": request.args.get("id", type=int),
            "descricao": request.args.get("descricao")
        }
        filtros = {k: v for k, v in filtros.items() if v is not None}

        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", type=int)

        query, params = build_query(filtros=filtros, limit=limit, offset=offset)

        cursor = g.conn.cursor()
        naturezas = select_dict(cursor, query, params)
        cursor.close()

        return jsonify(naturezas)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@natureza_bp.route("/naturezas", methods=["POST"])
def criar_natureza():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        if 'id' in data and data['id'] is None:
            data.pop('id')

        sql, params = generate_insert_sql("natureza", data, returning="id")
        cursor = g.conn.cursor()
        cursor.execute(sql, params)
        natureza_id = cursor.fetchone()[0]
        g.conn.commit()
        cursor.close()

        return jsonify({"id": natureza_id, "mensagem": "Natureza criada com sucesso"}), 201
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500

@natureza_bp.route("/naturezas/<int:natureza_id>", methods=["PUT"])
def atualizar_natureza(natureza_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        sql, params = generate_update_sql(
            "natureza",
            data,
            where_keys=['id'],
            where_values=[natureza_id]
        )
        cursor = g.conn.cursor()
        cursor.execute(sql, params)
        g.conn.commit()
        cursor.close()

        return jsonify({"mensagem": "Natureza atualizada com sucesso"})
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500

@natureza_bp.route("/naturezas/<int:natureza_id>", methods=["DELETE"])
def deletar_natureza(natureza_id):
    try:
        cursor = g.conn.cursor()
        cursor.execute("DELETE FROM natureza WHERE id = %s", (natureza_id,))
        g.conn.commit()
        cursor.close()
        return jsonify({"mensagem": "Natureza removida com sucesso"})
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500
