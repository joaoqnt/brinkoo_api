from flask import Blueprint, jsonify, g, request
from utils.db_helpers import select_dict, generate_insert_sql, generate_update_sql

crianca_bp = Blueprint("crianca_routes", __name__)


def build_query(filtros: dict = None, limit: int = None, offset: int = None):
    base_query = """
        SELECT 
            c.*,
            (
                SELECT json_agg(
                    to_jsonb(r) || jsonb_build_object('parentesco', cr.parentesco)
                )
                FROM responsavel r
                JOIN crianca_responsavel cr ON r.id = cr.responsavel_id
                WHERE cr.crianca_id = c.id
            ) AS responsaveis
        FROM crianca c

    """

    where_clauses = []
    params = []
    joins = []

    if filtros:
        # Filtro por nome da criança (exatamente como no teste SQL)
        if filtros.get('nome_crianca'):
            search_term = filtros['nome_crianca'].lower().strip()
            where_clauses.append(
                "unaccent(LOWER(c.nome)) LIKE unaccent(LOWER(%s))")
            params.append(f'%{search_term}%')

        # Filtro por ID da criança
        if filtros.get('id'):
            where_clauses.append("c.id = %s")
            params.append(filtros['id'])

        # Filtro por nome do responsável (mesma lógica aplicada)
        if filtros.get('nome_responsavel'):
            search_term = filtros['nome_responsavel'].lower().strip()
            joins.append("""
                JOIN crianca_responsavel cr_filtro ON c.id = cr_filtro.crianca_id
                JOIN responsavel r_filtro ON cr_filtro.responsavel_id = r_filtro.id
            """)
            where_clauses.append(
                "unaccent(LOWER(r_filtro.nome)) LIKE unaccent(LOWER(%s))")
            params.append(f'%{search_term}%')

    # Monta a query final
    query = base_query

    if joins:
        query += " " + " ".join(joins)

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    # Ordenação por similaridade (exatamente como no teste SQL)
    if filtros and filtros.get('nome_crianca'):
        query += " ORDER BY similarity(unaccent(LOWER(c.nome)), unaccent(LOWER(%s))) DESC"
        params.append(filtros['nome_crianca'].lower())
    else:
        query += " ORDER BY c.nome asc"

    # Paginação
    if limit is not None:
        query += " LIMIT %s"
        params.append(limit)

    if offset is not None:
        query += " OFFSET %s"
        params.append(offset)

    return query, params


@crianca_bp.route("/criancas", methods=["GET"])
def listar_criancas():
    try:
        # Parâmetros de paginação
        limit = request.args.get('limit', type=int)
        offset = request.args.get('offset', type=int)

        # Parâmetros de filtro
        filtros = {
            "nome_crianca": request.args.get('nome_crianca'),
            "nome_responsavel": request.args.get('nome_responsavel'),
            "id": request.args.get('id', type=int)
        }

        # Remove filtros vazios/nulos
        filtros = {k: v for k, v in filtros.items() if v is not None}

        cursor = g.conn.cursor()

        # Se não houver filtros, passa None para build_query
        query_params = filtros if filtros else None
        query, params = build_query(
            filtros=query_params, limit=limit, offset=offset)

        criancas = select_dict(cursor, query, params)
        cursor.close()

        return jsonify(criancas)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


def _salvar_responsaveis(cursor, crianca_id, responsaveis):
    for responsavel_data in responsaveis:
        parentesco = responsavel_data.pop('parentesco', None)
        
        if 'id' in responsavel_data and responsavel_data['id'] is None:
            responsavel_data.pop('id')

        cursor.execute(
            "SELECT id FROM responsavel WHERE documento = %s",
            (responsavel_data.get('documento'),)
        )
        responsavel_existente = cursor.fetchone()

        if responsavel_existente:
            responsavel_id = responsavel_existente[0]
            if responsavel_data:  # Só atualiza se houver dados
                sql_responsavel, params_responsavel = generate_update_sql(
                    'responsavel',
                    responsavel_data,
                    where_keys=['id'],
                    where_values=[responsavel_id]  # ✅ usa where_values explicitamente
                )
                cursor.execute(sql_responsavel, params_responsavel)

        else:
            # Insere novo responsável
            sql_responsavel, params_responsavel = generate_insert_sql(
                'responsavel',
                responsavel_data,
                returning='id'
            )
            cursor.execute(sql_responsavel, params_responsavel)
            responsavel_id = cursor.fetchone()[0]

        # Insere relacionamento com parentesco
        cursor.execute(
            "INSERT INTO crianca_responsavel (crianca_id, responsavel_id, parentesco) "
            "VALUES (%s, %s, %s)",
            (crianca_id, responsavel_id, parentesco)
        )


@crianca_bp.route("/criancas", methods=["POST"])
def criar_crianca():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        responsaveis = data.pop('responsaveis', [])
        # Remove id se for None na criança
        if 'id' in data and data['id'] is None:
            data.pop('id')

        cursor = g.conn.cursor()

        # Insere criança
        sql_crianca, params_crianca = generate_insert_sql(
            'crianca', data, returning="id")
        cursor.execute(sql_crianca, params_crianca)
        crianca_id = cursor.fetchone()[0]

        # Insere/atualiza responsáveis e relacionamento
        _salvar_responsaveis(cursor, crianca_id, responsaveis)

        g.conn.commit()
        cursor.close()

        return jsonify({"id": crianca_id, "mensagem": "Criança criada com sucesso"}), 201

    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500


@crianca_bp.route("/criancas/<int:crianca_id>", methods=["PUT"])
def atualizar_crianca(crianca_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        responsaveis = data.pop('responsaveis', [])

        cursor = g.conn.cursor()

        # Atualiza dados da criança se houver
        if data:
            sql_crianca, params_crianca = generate_update_sql(
                # ✅ passando explicitamente
                'crianca', data, where_keys=["id"], where_values=[crianca_id]
            )
            cursor.execute(sql_crianca, params_crianca)

        if responsaveis:
            # Remove relacionamentos antigos para recriar
            cursor.execute(
                "DELETE FROM crianca_responsavel WHERE crianca_id = %s", (crianca_id,))
            _salvar_responsaveis(cursor, crianca_id, responsaveis)

        g.conn.commit()

        # Buscar e retornar a criança atualizada
        query, params = build_query({'id': crianca_id})
        cursor.execute(query, params)
        crianca = cursor.fetchone()

        cursor.close()

        if crianca:
            return jsonify({"id": crianca_id, "mensagem": "Crianca atualizada com sucesso"})
        else:
            return jsonify({"erro": "Criança não encontrada"}), 404

    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500


@crianca_bp.route("/criancas/<int:crianca_id>", methods=["DELETE"])
def deletar_crianca(crianca_id):
    try:
        cursor = g.conn.cursor()

        # Primeiro remove os relacionamentos
        cursor.execute(
            "DELETE FROM crianca_responsavel WHERE crianca_id = %s",
            (crianca_id,)
        )

        # Depois remove a criança
        cursor.execute(
            "DELETE FROM crianca WHERE id = %s",
            (crianca_id,)
        )

        g.conn.commit()
        cursor.close()

        return jsonify({"mensagem": "Criança removida com sucesso"})
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500

