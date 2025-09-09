from flask import Blueprint, jsonify, request, g
from utils.db_helpers import select_dict, generate_insert_sql, generate_update_sql

centro_custo_bp = Blueprint("centro_custo_routes", __name__)

def build_query(filtros: dict = None, limit: int = None, offset: int = None):
    base_query = """
        SELECT * FROM centro_custo
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
        query += " ORDER BY descricao"

    if limit is not None:
        query += " LIMIT %s"
        params.append(limit)

    if offset is not None:
        query += " OFFSET %s"
        params.append(offset)

    return query, params

@centro_custo_bp.route("/centros-custo", methods=["GET"])
def listar_centros_custo():
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
        centros = select_dict(cursor, query, params)
        cursor.close()

        return jsonify(centros)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@centro_custo_bp.route("/centros-custo", methods=["POST"])
def criar_centro_custo():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        if 'id' in data and data['id'] is None:
            data.pop('id')

        sql, params = generate_insert_sql("centro_custo", data, returning="id")
        cursor = g.conn.cursor()
        cursor.execute(sql, params)
        centro_id = cursor.fetchone()[0]
        g.conn.commit()
        cursor.close()

        return jsonify({"id": centro_id, "mensagem": "Centro de custo criado com sucesso"}), 201
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500

@centro_custo_bp.route("/centros-custo/<int:centro_id>", methods=["PUT"])
def atualizar_centro_custo(centro_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        sql, params = generate_update_sql(
            "centro_custo",
            data,
            where_keys=['id'],
            where_values=[centro_id]
        )
        cursor = g.conn.cursor()
        cursor.execute(sql, params)
        g.conn.commit()
        cursor.close()

        return jsonify({"mensagem": "Centro de custo atualizado com sucesso"})
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500

@centro_custo_bp.route("/centros-custo/<int:centro_id>", methods=["DELETE"])
def deletar_centro_custo(centro_id):
    try:
        cursor = g.conn.cursor()
        cursor.execute("DELETE FROM centro_custo WHERE id = %s", (centro_id,))
        g.conn.commit()
        cursor.close()
        return jsonify({"mensagem": "Centro de custo removido com sucesso"})
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500
