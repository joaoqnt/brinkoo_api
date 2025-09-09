from flask import Blueprint, jsonify, g, request
from utils.db_helpers import select_dict, generate_insert_sql, generate_update_sql

convenio_bp = Blueprint("convenio_routes", __name__)

def build_convenio_query(filtros: dict = None, limit: int = None, offset: int = None):
    base_query = """
        SELECT
            c.*,
            row_to_json(p) AS parceiro,
            row_to_json(e) AS empresa,
            row_to_json(n) AS natureza,
            row_to_json(cc) AS centro_custo
        FROM convenio c
        LEFT JOIN parceiro p ON p.id = c.parceiro
        LEFT JOIN empresa e ON e.id = c.empresa
        LEFT JOIN natureza n ON n.id = c.natureza
        LEFT JOIN centro_custo cc ON cc.id = c.centro_custo
        """

    
    where_clauses = []
    params = []

    if filtros:
        for campo, valor in filtros.items():
            if valor in [None, "", "null", "NULL"]:
                where_clauses.append(f"{campo} IS NULL")
            elif isinstance(valor, (list, tuple)) and len(valor) == 2:
                where_clauses.append(f"{campo} BETWEEN %s AND %s")
                params.extend(valor)
            elif isinstance(valor, str):
                if "%" not in valor:
                    valor = f"%{valor}%"
                where_clauses.append(f"{campo} ILIKE %s")
                params.append(valor)
            else:
                where_clauses.append(f"{campo} = %s")
                params.append(valor)

    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)

    base_query += " ORDER BY c.descricao"

    if limit is not None:
        base_query += " LIMIT %s"
        params.append(limit)

    if offset is not None:
        base_query += " OFFSET %s"
        params.append(offset)
    print(base_query)
    return base_query, params


@convenio_bp.route("/convenios", methods=["GET"])
@convenio_bp.route("/convenios/search", methods=["GET"])
def listar_e_buscar_convenios():
    try:
        filtros = request.args.to_dict()
        limit = filtros.pop("limit", None)
        offset = filtros.pop("offset", None)

        for k, v in list(filtros.items()):
            if v is None or v.lower() in ["null", "none", ""]:
                filtros[k] = None
            elif v and v.isdigit():
                filtros[k] = int(v)
            elif v in ["true", "false"]:
                filtros[k] = v == "true"

        query, params = build_convenio_query(
            filtros,
            limit=int(limit) if limit else None,
            offset=int(offset) if offset else None
        )

        cursor = g.conn.cursor()
        convenios = select_dict(cursor, query, params)
        cursor.close()
        return jsonify(convenios)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@convenio_bp.route("/convenios", methods=["POST"])
def criar_convenio():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        data.pop("id", None)  # Remove ID se enviado

        cursor = g.conn.cursor()
        sql, params = generate_insert_sql("convenio", data, returning="id")
        cursor.execute(sql, params)
        convenio_id = cursor.fetchone()[0]

        g.conn.commit()
        cursor.close()
        return jsonify({"id": convenio_id, "mensagem": "Convênio criado com sucesso"}), 201
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500


@convenio_bp.route("/convenios/<int:convenio_id>", methods=["PUT"])
def atualizar_convenio(convenio_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        data.pop("id", None)  # Remove ID se enviado

        cursor = g.conn.cursor()
        sql, params = generate_update_sql("convenio", data, where_keys=["id"], where_values=[convenio_id])
        cursor.execute(sql, params)
        g.conn.commit()
        cursor.close()
        return jsonify({"id": convenio_id, "mensagem": "Convênio atualizado com sucesso"}), 200
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500


@convenio_bp.route("/convenios/<int:convenio_id>", methods=["DELETE"])
def deletar_convenio(convenio_id):
    try:
        cursor = g.conn.cursor()
        cursor.execute("DELETE FROM convenio WHERE id = %s", (convenio_id,))
        g.conn.commit()
        cursor.close()
        return jsonify({"mensagem": "Convênio removido com sucesso"})
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500
