from flask import Blueprint, jsonify, request, g
from utils.db_helpers import select_dict, generate_insert_sql, generate_update_sql

guarda_volume_bp = Blueprint("guarda_volume_routes", __name__)

def build_query(filtros: dict = None, limit: int = None, offset: int = None):
    base_query = "SELECT * FROM guarda_volume"
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
        
        if filtros.get('utilizado') is not None:
            where_clauses.append("utilizado = %s")
            params.append(filtros['utilizado'])
        
        if filtros.get('empresa') is not None:
            where_clauses.append("empresa = %s")
            params.append(filtros['empresa'])

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

@guarda_volume_bp.route("/guardas-volume", methods=["GET"])
def listar_guardas_volume():
    try:
        filtros = {
            "id": request.args.get("id", type=int),
            "descricao": request.args.get("descricao"),
            "empresa": request.args.get("empresa"),
            "utilizado": request.args.get("utilizado", type=lambda x: x.lower() == 'true'),
        }
        filtros = {k: v for k, v in filtros.items() if v is not None}

        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", type=int)

        query, params = build_query(filtros=filtros, limit=limit, offset=offset)

        cursor = g.conn.cursor()
        resultados = select_dict(cursor, query, params)
        cursor.close()

        return jsonify(resultados)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@guarda_volume_bp.route("/guardas-volume", methods=["POST"])
def criar_guarda_volume():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        if 'id' in data and data['id'] is None:
            data.pop('id')

        sql, params = generate_insert_sql("guarda_volume", data, returning="id")
        cursor = g.conn.cursor()
        cursor.execute(sql, params)
        novo_id = cursor.fetchone()[0]
        g.conn.commit()
        cursor.close()

        return jsonify({"id": novo_id, "mensagem": "Guarda-volume criado com sucesso"}), 201
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500

@guarda_volume_bp.route("/guardas-volume/<int:guarda_id>", methods=["PUT"])
def atualizar_guarda_volume(guarda_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        sql, params = generate_update_sql("guarda_volume", data, where_keys=["id"], where_values=[guarda_id])
        cursor = g.conn.cursor()
        cursor.execute(sql, params)
        g.conn.commit()
        cursor.close()

        return jsonify({"mensagem": "Guarda-volume atualizado com sucesso"})
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500

@guarda_volume_bp.route("/guardas-volume/<int:guarda_id>", methods=["DELETE"])
def deletar_guarda_volume(guarda_id):
    try:
        cursor = g.conn.cursor()
        cursor.execute("DELETE FROM guarda_volume WHERE id = %s", (guarda_id,))
        g.conn.commit()
        cursor.close()
        return jsonify({"mensagem": "Guarda-volume removido com sucesso"})
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500
