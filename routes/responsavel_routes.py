from flask import Blueprint, jsonify, request, g
from utils.db_helpers import select_dict, generate_insert_sql, generate_update_sql

responsavel_bp = Blueprint("responsavel_routes", __name__)

def build_query(filtros: dict = None, limit: int = None, offset: int = None):
    base_query = """
        SELECT * FROM responsavel
    """
    where_clauses = []
    params = []

    if filtros:
        if filtros.get('id'):
            where_clauses.append("id = %s")
            params.append(filtros['id'])

        if filtros.get('nome'):
            search_term = filtros['nome'].lower().strip()
            where_clauses.append("unaccent(lower(nome)) LIKE unaccent(lower(%s))")
            params.append(f"%{search_term}%")

        if filtros.get('documento'):
            where_clauses.append("documento = %s")
            params.append(filtros['documento'])

    query = base_query

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    if filtros and filtros.get('nome'):
        query += " ORDER BY similarity(unaccent(lower(nome)), unaccent(lower(%s))) DESC"
        params.append(filtros['nome'].lower())
    else:
        query += " ORDER BY nome asc"

    if limit is not None:
        query += " LIMIT %s"
        params.append(limit)

    if offset is not None:
        query += " OFFSET %s"
        params.append(offset)

    return query, params

@responsavel_bp.route("/responsaveis", methods=["GET"])
def listar_responsaveis():
    try:
        filtros = {
            "id": request.args.get("id", type=int),
            "nome": request.args.get("nome"),
            "documento": request.args.get("documento")
        }
        filtros = {k: v for k, v in filtros.items() if v is not None}

        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", type=int)

        query, params = build_query(filtros=filtros, limit=limit, offset=offset)

        cursor = g.conn.cursor()
        responsaveis = select_dict(cursor, query, params)
        cursor.close()

        return jsonify(responsaveis)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@responsavel_bp.route("/responsaveis", methods=["POST"])
def criar_responsavel():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        if 'id' in data and data['id'] is None:
            data.pop('id')

        sql, params = generate_insert_sql("responsavel", data, returning="id")
        cursor = g.conn.cursor()
        cursor.execute(sql, params)
        responsavel_id = cursor.fetchone()[0]
        g.conn.commit()
        cursor.close()

        return jsonify({"id": responsavel_id, "mensagem": "Responsável criado com sucesso"}), 201
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500

@responsavel_bp.route("/responsaveis/<int:responsavel_id>", methods=["PUT"])
def atualizar_responsavel(responsavel_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        sql, params = generate_update_sql(
            "responsavel",
              data, 
            where_keys=['id'],
            where_values=[responsavel_id]
        )
        cursor = g.conn.cursor()
        cursor.execute(sql, params)
        g.conn.commit()
        cursor.close()

        return jsonify({"mensagem": "Responsável atualizado com sucesso"})
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500

@responsavel_bp.route("/responsaveis/<int:responsavel_id>", methods=["DELETE"])
def deletar_responsavel(responsavel_id):
    try:
        cursor = g.conn.cursor()
        cursor.execute("DELETE FROM responsavel WHERE id = %s", (responsavel_id,))
        g.conn.commit()
        cursor.close()
        return jsonify({"mensagem": "Responsável removido com sucesso"})
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500
