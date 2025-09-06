from flask import Blueprint, jsonify, g, request
from utils.db_helpers import select_dict, generate_insert_sql, generate_update_sql

financeiro_bp = Blueprint("financeiro_routes", __name__)


def build_financeiro_query(filtros: dict = None, limit: int = None, offset: int = None):
    base_query = """
        SELECT
            f.*,
            row_to_json(ch.*) AS checkin,
            row_to_json(p.*) AS parceiro,
            row_to_json(fp.*) AS forma_pagamento,
            row_to_json(u.*) AS usuario
        FROM financeiro f
        LEFT JOIN checkin ch ON f.checkin = ch.id
        LEFT JOIN parceiro p ON f.parceiro = p.id
        LEFT JOIN forma_pagamento fp ON f.forma_pagamento = fp.id
        LEFT JOIN usuario u ON f.usuario = u.id
    """

    where_clauses = []
    params = []

    if filtros:
        if filtros.get("checkin"):
            where_clauses.append("f.checkin = %s")
            params.append(filtros["checkin"])
        if filtros.get("parceiro"):
            where_clauses.append("f.parceiro = %s")
            params.append(filtros["parceiro"])
        if filtros.get("forma_pagamento"):
            where_clauses.append("f.forma_pagamento = %s")
            params.append(filtros["forma_pagamento"])
        if filtros.get("usuario"):
            where_clauses.append("f.usuario = %s")
            params.append(filtros["usuario"])
        if filtros.get("receita_despesa"):
            where_clauses.append("f.receita_despesa = %s")
            params.append(filtros["receita_despesa"])
        if filtros.get("data_inicio") and filtros.get("data_fim"):
            where_clauses.append("f.data_negociacao BETWEEN %s AND %s")
            params.append(filtros["data_inicio"])
            params.append(filtros["data_fim"])

    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)

    base_query += " ORDER BY f.data_negociacao DESC"

    if limit is not None:
        base_query += " LIMIT %s"
        params.append(limit)

    if offset is not None:
        base_query += " OFFSET %s"
        params.append(offset)

    return base_query, params


@financeiro_bp.route("/financeiro", methods=["GET"])
def listar_financeiro():
    try:
        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", type=int)

        filtros = {
            "checkin": request.args.get("checkin"),
            "parceiro": request.args.get("parceiro"),
            "forma_pagamento": request.args.get("forma_pagamento"),
            "usuario": request.args.get("usuario"),
            "receita_despesa": request.args.get("receita_despesa"),
            "data_inicio": request.args.get("data_inicio"),
            "data_fim": request.args.get("data_fim"),
        }

        # Remove filtros None
        filtros = {k: v for k, v in filtros.items() if v is not None}

        cursor = g.conn.cursor()
        query, params = build_financeiro_query(filtros=filtros, limit=limit, offset=offset)
        registros = select_dict(cursor, query, params)
        cursor.close()

        return jsonify(registros)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500



@financeiro_bp.route("/financeiro/search", methods=["GET"])
def buscar_financeiro():
    try:
        filtros = {
            "checkin": request.args.get("checkin", type=int),
            "parceiro": request.args.get("parceiro", type=int),
            "forma_pagamento": request.args.get("forma_pagamento", type=int),
            "usuario": request.args.get("usuario", type=int),
            "receita_despesa": request.args.get("receita_despesa"),
            "data_inicio": request.args.get("data_inicio"),
            "data_fim": request.args.get("data_fim"),
        }
        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", type=int)

        cursor = g.conn.cursor()
        query, params = build_financeiro_query(filtros, limit, offset)
        registros = select_dict(cursor, query, params)
        cursor.close()

        return jsonify(registros)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@financeiro_bp.route("/financeiro", methods=["POST"])
def criar_financeiro():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        data.pop("id", None)

        # Garantir que campos de chave estrangeira sejam IDs
        for campo in ["checkin", "parceiro", "forma_pagamento", "usuario"]:
            if isinstance(data.get(campo), dict):
                data[campo] = data[campo].get("id")

        cursor = g.conn.cursor()
        sql, params = generate_insert_sql("financeiro", data, returning="id")
        cursor.execute(sql, params)
        registro_id = cursor.fetchone()[0]

        g.conn.commit()
        cursor.close()

        return jsonify({"id": registro_id, "mensagem": "Registro financeiro criado com sucesso"}), 201
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500


@financeiro_bp.route("/financeiro/<int:registro_id>", methods=["PUT"])
def atualizar_financeiro(registro_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        data.pop("id", None)

        for campo in ["checkin", "parceiro", "forma_pagamento", "usuario"]:
            if isinstance(data.get(campo), dict):
                data[campo] = data[campo].get("id")

        cursor = g.conn.cursor()
        sql, params = generate_update_sql("financeiro", data, where_keys=["id"], where_values=[registro_id])
        cursor.execute(sql, params)

        g.conn.commit()
        cursor.close()

        return jsonify({"id": registro_id, "mensagem": "Registro financeiro atualizado com sucesso"}), 200
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500


@financeiro_bp.route("/financeiro/<int:registro_id>", methods=["DELETE"])
def deletar_financeiro(registro_id):
    try:
        cursor = g.conn.cursor()
        cursor.execute("DELETE FROM financeiro WHERE id = %s", (registro_id,))
        g.conn.commit()
        cursor.close()
        return jsonify({"mensagem": "Registro financeiro removido com sucesso"})
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500
