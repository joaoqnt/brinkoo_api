from flask import Blueprint, jsonify, g, request
from utils.db_helpers import select_dict, generate_insert_sql, generate_update_sql

atividade_bp = Blueprint("atividade_routes", __name__)

@atividade_bp.route("/atividades", methods=["GET"])
def listar_atividades():
    try:
        cursor = g.conn.cursor()
        atividades = select_dict(cursor, "SELECT * FROM atividade ORDER BY descricao")
        cursor.close()
        return jsonify(atividades)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500



@atividade_bp.route("/atividades/<int:atividade_id>", methods=["GET"])
def obter_atividade(atividade_id):
    try:
        cursor = g.conn.cursor()
        cursor.execute("SELECT * FROM atividade WHERE id = %s", (atividade_id,))
        atividade = select_dict(cursor)
        cursor.close()

        if atividade:
            return jsonify(atividade[0])
        else:
            return jsonify({"erro": "Atividade não encontrada"}), 404
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@atividade_bp.route("/atividades", methods=["POST"])
def criar_atividade():
    try:
        data = request.get_json()
        if not data or "descricao" not in data:
            return jsonify({"erro": "Descrição é obrigatória"}), 400

        data.pop("id", None)
        cursor = g.conn.cursor()
        sql, params = generate_insert_sql("atividade", data, returning="id")
        cursor.execute(sql, params)
        atividade_id = cursor.fetchone()[0]
        g.conn.commit()
        cursor.close()

        return jsonify({"id": atividade_id, "mensagem": "Atividade criada com sucesso"}), 201
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500


@atividade_bp.route("/atividades/<int:atividade_id>", methods=["PUT"])
def atualizar_atividade(atividade_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        cursor = g.conn.cursor()
        sql, params = generate_update_sql("atividade", data, ["id"])
        cursor.execute(sql, params + [atividade_id])
        g.conn.commit()
        cursor.close()

        return jsonify({"mensagem": "Atividade atualizada com sucesso"})
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500


@atividade_bp.route("/atividades/<int:atividade_id>", methods=["DELETE"])
def deletar_atividade(atividade_id):
    try:
        cursor = g.conn.cursor()
        cursor.execute("DELETE FROM atividade WHERE id = %s", (atividade_id,))
        g.conn.commit()
        cursor.close()

        return jsonify({"mensagem": "Atividade removida com sucesso"})
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500
