from flask import Blueprint, jsonify, request, g
from utils.db_helpers import select_dict, generate_insert_sql, generate_update_sql

usuario_bp = Blueprint("usuario_routes", __name__)

def build_usuario_query(filtros: dict = None, limit: int = None, offset: int = None):
    base_query = """
        SELECT * FROM usuario
    """
    where_clauses = []
    params = []

    if filtros:
        if filtros.get('id'):
            where_clauses.append("id = %s")
            params.append(filtros['id'])

        if filtros.get('login'):
            search_term = filtros['login'].lower().strip()
            where_clauses.append("unaccent(lower(login)) LIKE unaccent(lower(%s))")
            params.append(f"%{search_term}%")

    query = base_query

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    if filtros and filtros.get('login'):
        query += " ORDER BY similarity(unaccent(lower(login)), unaccent(lower(%s))) DESC"
        params.append(filtros['login'].lower())
    else:
        query += " ORDER BY id DESC"

    if limit is not None:
        query += " LIMIT %s"
        params.append(limit)

    if offset is not None:
        query += " OFFSET %s"
        params.append(offset)

    return query, params

@usuario_bp.route("/usuarios", methods=["GET"])
def listar_usuarios():
    try:
        filtros = {
            "id": request.args.get("id", type=int),
            "login": request.args.get("login")
        }
        filtros = {k: v for k, v in filtros.items() if v is not None}

        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", type=int)

        query, params = build_usuario_query(filtros=filtros, limit=limit, offset=offset)

        cursor = g.conn.cursor()
        usuarios = select_dict(cursor, query, params)
        cursor.close()

        return jsonify(usuarios)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@usuario_bp.route("/usuarios", methods=["POST"])
def criar_usuario():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        if 'id' in data and data['id'] is None:
            data.pop('id')

        sql, params = generate_insert_sql("usuario", data, returning="id")
        cursor = g.conn.cursor()
        cursor.execute(sql, params)
        usuario_id = cursor.fetchone()[0]
        g.conn.commit()
        cursor.close()

        return jsonify({"id": usuario_id, "mensagem": "Usuário criado com sucesso"}), 201
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500

@usuario_bp.route("/usuarios/<int:usuario_id>", methods=["PUT"])
def atualizar_usuario(usuario_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        sql, params = generate_update_sql(
            "usuario",
            data,
            where_keys=['id'],
            where_values=[usuario_id]
        )
        cursor = g.conn.cursor()
        cursor.execute(sql, params)
        g.conn.commit()
        cursor.close()

        return jsonify({"mensagem": "Usuário atualizado com sucesso"})
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500

@usuario_bp.route("/usuarios/<int:usuario_id>", methods=["DELETE"])
def deletar_usuario(usuario_id):
    try:
        cursor = g.conn.cursor()
        cursor.execute("DELETE FROM usuario WHERE id = %s", (usuario_id,))
        g.conn.commit()
        cursor.close()
        return jsonify({"mensagem": "Usuário removido com sucesso"})
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500
