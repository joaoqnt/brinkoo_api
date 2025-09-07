from flask import Blueprint, jsonify, request, g
from utils.db_helpers import select_dict, generate_insert_sql, generate_update_sql

usuario_bp = Blueprint("usuario_routes", __name__)

def build_usuario_query(filtros: dict = None, limit: int = None, offset: int = None, modo_login: bool = False):
    base_query = """
        SELECT 
            u.*,
            row_to_json(e) empresa 
        FROM usuario u
        LEFT JOIN empresa e ON e.id = u.empresa
    """
    where_clauses = []
    params = []

    if filtros:
        if filtros.get('id'):
            where_clauses.append("u.id = %s")
            params.append(filtros['id'])

        if filtros.get('login'):
            if modo_login:
                # login exato
                where_clauses.append("u.login = %s")
                params.append(filtros['login'])
            else:
                # busca com LIKE + similarity
                search_term = filtros['login'].lower().strip()
                where_clauses.append("unaccent(lower(u.login)) LIKE unaccent(lower(%s))")
                params.append(f"%{search_term}%")

        if filtros.get('senha'):
            where_clauses.append("u.senha = %s")
            params.append(filtros['senha'])

    query = base_query

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    # ordenação só em busca normal
    if not modo_login:
        if filtros and filtros.get('login'):
            query += " ORDER BY similarity(unaccent(lower(u.login)), unaccent(lower(%s))) DESC"
            params.append(filtros['login'].lower())
        else:
            query += " ORDER BY u.id DESC"

    if limit is not None:
        query += " LIMIT %s"
        params.append(limit)

    if offset is not None:
        query += " OFFSET %s"
        params.append(offset)

    print(query, params)  # debug
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
    
@usuario_bp.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        if not data or "login" not in data or "senha" not in data:
            return jsonify({"erro": "Login e senha são obrigatórios"}), 400

        filtros = {
            "login": data["login"],
            "senha": data["senha"]
        }

        query, params = build_usuario_query(filtros=filtros, limit=1, modo_login=True)

        cursor = g.conn.cursor()
        usuarios = select_dict(cursor, query, params)
        cursor.close()

        if not usuarios:
            return jsonify({"erro": "Usuário ou senha inválidos"}), 401

        return jsonify(usuarios[0])
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
