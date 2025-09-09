from flask import Blueprint, jsonify, request, g
from utils.db_helpers import select_dict, generate_insert_sql, generate_update_sql

empresa_bp = Blueprint("empresa_routes", __name__)

def build_query(filtros: dict = None, limit: int = None, offset: int = None):
    base_query = """
        SELECT * FROM empresa
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

        if filtros.get('cnpj'):
            where_clauses.append("cnpj = %s")
            params.append(filtros['cnpj'])

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

@empresa_bp.route("/empresas", methods=["GET"])
def listar_empresas():
    try:
        filtros = {
            "id": request.args.get("id", type=int),
            "descricao": request.args.get("descricao"),
            "cnpj": request.args.get("cnpj")
        }
        filtros = {k: v for k, v in filtros.items() if v is not None}

        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", type=int)

        query, params = build_query(filtros=filtros, limit=limit, offset=offset)

        cursor = g.conn.cursor()
        empresas = select_dict(cursor, query, params)
        cursor.close()

        return jsonify(empresas)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@empresa_bp.route("/empresas", methods=["POST"])
def criar_empresa():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        if 'id' in data and data['id'] is None:
            data.pop('id')

        sql, params = generate_insert_sql("empresa", data, returning="id")
        cursor = g.conn.cursor()
        cursor.execute(sql, params)
        empresa_id = cursor.fetchone()[0]
        g.conn.commit()
        cursor.close()

        return jsonify({"id": empresa_id, "mensagem": "Empresa criada com sucesso"}), 201
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500

@empresa_bp.route("/empresas/<int:empresa_id>", methods=["PUT"])
def atualizar_empresa(empresa_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        sql, params = generate_update_sql(
            "empresa",
            data,
            where_keys=['id'],
            where_values=[empresa_id]
        )
        cursor = g.conn.cursor()
        cursor.execute(sql, params)
        g.conn.commit()
        cursor.close()

        return jsonify({"mensagem": "Empresa atualizada com sucesso"})
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500

@empresa_bp.route("/empresas/<int:empresa_id>", methods=["DELETE"])
def deletar_empresa(empresa_id):
    try:
        cursor = g.conn.cursor()
        cursor.execute("DELETE FROM empresa WHERE id = %s", (empresa_id,))
        g.conn.commit()
        cursor.close()
        return jsonify({"mensagem": "Empresa removida com sucesso"})
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500
