from flask import Blueprint, jsonify, g, request
from utils.db_helpers import select_dict, generate_insert_sql, generate_update_sql

checkin_bp = Blueprint("checkin_routes", __name__)


def build_checkin_query(filtros: dict = None, limit: int = None, offset: int = None):
    base_query = """
        SELECT
            ch.*,
            (
                SELECT row_to_json(crianca_data)
                FROM (
                    SELECT 
                        c.*,
                        (
                            SELECT json_agg(
                                json_build_object(
                                    'id', r.id,
                                    'nome', r.nome,
                                    'documento', r.documento,
                                    'celular', r.celular,
                                    'email', r.email,
                                    'url_image', r.url_image,
                                    'parentesco', cr.parentesco
                                ) 
                            ) as responsavel
                            FROM responsavel r
                            JOIN crianca_responsavel cr ON r.id = cr.responsavel_id
                            WHERE cr.crianca_id = c.id
                        ) AS responsaveis
                    FROM crianca c
                    WHERE c.id = ch.crianca
                ) crianca_data
            ) AS crianca,
            row_to_json(re.*) AS responsavel_entrada,
            row_to_json(rs.*) AS responsavel_saida,
            row_to_json(gv.*) AS guarda_volume,
            row_to_json(fp.*) AS forma_pagamento,
            (
                SELECT json_agg(row_to_json(a.*))
                FROM checkin_atividade ca
                JOIN atividade a ON a.id = ca.atividade
                WHERE ca.checkin = ch.id
            ) AS atividades,
            (
                SELECT json_agg(row_to_json(a.*))
                FROM checkin_responsavel_checkout ca
                JOIN responsavel a ON a.id = ca.responsavel
                WHERE ca.checkin = ch.id
            ) AS responsaveis_possiveis_checkout
        FROM checkin ch
        JOIN crianca c ON ch.crianca = c.id
        JOIN responsavel re ON ch.responsavel_entrada = re.id
        LEFT JOIN responsavel rs ON ch.responsavel_saida = rs.id
        LEFT JOIN guarda_volume gv ON gv.id = ch.guarda_volume
        LEFT JOIN forma_pagamento fp ON fp.id = ch.forma_pagamento
    """

    where_clauses = []
    params = []

    if filtros:
        for campo, valor in filtros.items():
            if valor is None:
                where_clauses.append(f"{campo} IS NULL")
            elif isinstance(valor, (list, tuple)) and len(valor) == 2:
                where_clauses.append(f"{campo} BETWEEN %s AND %s")
                params.extend(valor)
            elif isinstance(valor, str):
                # Se não tiver '%' no valor, aplica busca parcial automática
                if "%" not in valor:
                    valor = f"%{valor}%"
                where_clauses.append(f"{campo} ILIKE %s")
                params.append(valor)
            else:
                where_clauses.append(f"{campo} = %s")
                params.append(valor)

    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)

    base_query += " ORDER BY ch.data_entrada DESC"

    if limit is not None:
        base_query += " LIMIT %s"
        params.append(limit)

    if offset is not None:
        base_query += " OFFSET %s"
        params.append(offset)

    return base_query, params


@checkin_bp.route("/checkins", methods=["GET"])
@checkin_bp.route("/checkins/search", methods=["GET"])
def listar_e_buscar_checkins():
    try:
        filtros = request.args.to_dict()  # Pega todos args como dict
        limit = filtros.pop("limit", None)
        offset = filtros.pop("offset", None)

        # Converte tipos numéricos e booleanos conforme necessário
        for k, v in list(filtros.items()):
            if v and v.isdigit():
                filtros[k] = int(v)
            elif v in ["true", "false"]:
                filtros[k] = v == "true"

        query, params = build_checkin_query(filtros, limit=int(limit) if limit else None,
                                            offset=int(offset) if offset else None)

        cursor = g.conn.cursor()
        checkins = select_dict(cursor, query, params)
        cursor.close()

        return jsonify(checkins)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@checkin_bp.route("/checkins", methods=["POST"])
def criar_checkin():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        atividades = data.pop("atividades", [])
        # New line for checkout responsibles
        responsaveis_checkout = data.pop("responsaveis_possiveis_checkout", [])
        data.pop("id", None)

        # Garante que campos esperados como inteiros venham corretos
        for campo in ["responsavel_entrada", "responsavel_saida", "crianca"]:
            if isinstance(data.get(campo), dict):
                data[campo] = data[campo].get("id")

        cursor = g.conn.cursor()

        sql, params = generate_insert_sql("checkin", data, returning="id")
        cursor.execute(sql, params)
        checkin_id = cursor.fetchone()[0]

        # Inserir atividades (pegando apenas os IDs)
        for atividade in atividades:
            atividade_id = atividade.get("id")
            if atividade_id:
                cursor.execute(
                    "INSERT INTO checkin_atividade (checkin, atividade) VALUES (%s, %s)",
                    (checkin_id, atividade_id)
                )

        # Inserir responsáveis pelo checkout
        for responsavel in responsaveis_checkout:
            responsavel_id = responsavel.get("id") if isinstance(
                responsavel, dict) else responsavel
            if responsavel_id:
                cursor.execute(
                    "INSERT INTO checkin_responsavel_checkout (checkin, responsavel) VALUES (%s, %s)",
                    (checkin_id, responsavel_id)
                )

        g.conn.commit()
        cursor.close()

        return jsonify({"id": checkin_id, "mensagem": "Checkin criado com sucesso"}), 201
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500


@checkin_bp.route("/checkins/<int:checkin_id>", methods=["PUT"])
def atualizar_checkin(checkin_id):
    print(checkin_id)
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        print("Dados recebidos:", data)

        # Verificar se checkin existe
        cursor = g.conn.cursor()

        # Extrair atividades e responsáveis pelo checkout
        atividades = data.pop("atividades", [])
        # New line for checkout responsibles
        responsaveis_checkout = data.pop("responsaveis_possiveis_checkout", [])
        data.pop("id", None)  # Remove ID se veio no payload

        print("Dados para atualização:", data)

        # Tratar campos de relacionamento
        for campo in ["responsavel_entrada", "responsavel_saida", "crianca"]:
            if isinstance(data.get(campo), dict):
                data[campo] = data[campo].get("id")

        # Atualizar checkin
        sql, params = generate_update_sql("checkin", data, where_keys=[
                                          "id"], where_values=[checkin_id])
        cursor.execute(sql, params)

        # Atualizar atividades
        cursor.execute(
            "DELETE FROM checkin_atividade WHERE checkin = %s", (checkin_id,))
        for atividade in atividades:
            atividade_id = atividade.get("id")
            if atividade_id:
                cursor.execute(
                    "INSERT INTO checkin_atividade (checkin, atividade) VALUES (%s, %s)",
                    (checkin_id, atividade_id)
                )

        # Atualizar responsáveis pelo checkout
        cursor.execute(
            "DELETE FROM checkin_responsavel_checkout WHERE checkin = %s", (checkin_id,))
        for responsavel in responsaveis_checkout:
            responsavel_id = responsavel.get("id") if isinstance(
                responsavel, dict) else responsavel
            if responsavel_id:
                cursor.execute(
                    "INSERT INTO checkin_responsavel_checkout (checkin, responsavel) VALUES (%s, %s)",
                    (checkin_id, responsavel_id)
                )

        g.conn.commit()
        cursor.close()

        return jsonify({"id": checkin_id, "mensagem": "Check-in atualizado com sucesso"}), 200

    except Exception as e:
        g.conn.rollback()
        print("Erro durante atualização:", str(e))
        return jsonify({"erro": str(e)}), 500


@checkin_bp.route("/checkins/<int:checkin_id>", methods=["DELETE"])
def deletar_checkin(checkin_id):
    try:
        cursor = g.conn.cursor()
        cursor.execute("DELETE FROM checkin WHERE id = %s", (checkin_id,))
        g.conn.commit()
        cursor.close()
        return jsonify({"mensagem": "Checkin removido com sucesso"})
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500
