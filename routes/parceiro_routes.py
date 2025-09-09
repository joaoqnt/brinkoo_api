from flask import Blueprint, jsonify, request, g
from utils.db_helpers import select_dict, generate_insert_sql, generate_update_sql

parceiro_bp = Blueprint("parceiro_routes", __name__)

def build_query(filtros: dict = None, limit: int = None, offset: int = None):
    base_query = "SELECT * FROM parceiro"
    where_clauses = []
    params = []

    if filtros:
        for key, value in filtros.items():
            if value is not None:
                if isinstance(value, bool):
                    where_clauses.append(f"{key} = %s")
                    params.append(value)
                elif key == 'nome':
                    where_clauses.append("unaccent(lower(nome)) LIKE unaccent(lower(%s))")
                    params.append(f"%{value.lower().strip()}%")
                else:
                    where_clauses.append(f"{key} = %s")
                    params.append(value)

    query = base_query

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    query += " ORDER BY nome asc"

    if limit is not None:
        query += " LIMIT %s"
        params.append(limit)

    if offset is not None:
        query += " OFFSET %s"
        params.append(offset)

    return query, params

@parceiro_bp.route("/parceiros", methods=["GET"])
def listar_parceiros():
    try:
        filtros = {
            "id": request.args.get("id", type=int),
            "nome": request.args.get("nome"),
            "pessoa_fisica": request.args.get("pessoa_fisica", type=lambda x: x.lower() == 'true'),
            "cpf_cnpj": request.args.get("cpf_cnpj"),
            "telefone": request.args.get("telefone"),
            "email": request.args.get("email"),
            "cep": request.args.get("cep"),
            "cidade": request.args.get("cidade"),
            "estado": request.args.get("estado"),
            "bairro": request.args.get("bairro"),
            "endereco": request.args.get("endereco"),
            "cliente": request.args.get("cliente", type=lambda x: x.lower() == 'true'),
            "fornecedor": request.args.get("fornecedor", type=lambda x: x.lower() == 'true'),
            "funcionario": request.args.get("funcionario", type=lambda x: x.lower() == 'true'),
            "transportador": request.args.get("transportador", type=lambda x: x.lower() == 'true'),
            "agencia_bancaria": request.args.get("agencia_bancaria", type=lambda x: x.lower() == 'true'),
        }

        filtros = {k: v for k, v in filtros.items() if v is not None}

        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", type=int)

        query, params = build_query(filtros, limit, offset)

        cursor = g.conn.cursor()
        parceiros = select_dict(cursor, query, params)
        cursor.close()

        return jsonify(parceiros)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@parceiro_bp.route("/parceiros", methods=["POST"])
def criar_parceiro():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        if 'id' in data and data['id'] is None:
            data.pop('id')

        sql, params = generate_insert_sql("parceiro", data, returning="id")
        cursor = g.conn.cursor()
        cursor.execute(sql, params)
        novo_id = cursor.fetchone()[0]
        g.conn.commit()
        cursor.close()

        return jsonify({"id": novo_id, "mensagem": "Parceiro criado com sucesso"}), 201
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500

@parceiro_bp.route("/parceiros/<int:parceiro_id>", methods=["PUT"])
def atualizar_parceiro(parceiro_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        sql, params = generate_update_sql("parceiro", data, where_keys=["id"], where_values=[parceiro_id])
        cursor = g.conn.cursor()
        cursor.execute(sql, params)
        g.conn.commit()
        cursor.close()

        return jsonify({"mensagem": "Parceiro atualizado com sucesso"})
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500

@parceiro_bp.route("/parceiros/<int:parceiro_id>", methods=["DELETE"])
def deletar_parceiro(parceiro_id):
    try:
        cursor = g.conn.cursor()
        cursor.execute("DELETE FROM parceiro WHERE id = %s", (parceiro_id,))
        g.conn.commit()
        cursor.close()

        return jsonify({"mensagem": "Parceiro removido com sucesso"})
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500
