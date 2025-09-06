from flask import Blueprint, jsonify, request, g
from utils.db_helpers import select_dict, generate_insert_sql, generate_update_sql

parametro_bp = Blueprint("parametro_routes", __name__)


@parametro_bp.route("/parametro", methods=["GET"])
def obter_parametro():
    try:
        cursor = g.conn.cursor()
        resultado = select_dict(cursor, "SELECT * FROM parametro LIMIT 1")
        cursor.close()
        if resultado:
            return jsonify(resultado[0])
        return jsonify({"mensagem": "Nenhum parâmetro cadastrado"}), 404
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@parametro_bp.route("/parametro", methods=["POST"])
def criar_parametro():
    try:
        cursor = g.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM parametro")
        count = cursor.fetchone()[0]
        if count > 0:
            cursor.close()
            return jsonify({"erro": "Parâmetro já existe"}), 400

        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        sql, params = generate_insert_sql("parametro", data)
        cursor.execute(sql, params)
        g.conn.commit()
        cursor.close()

        return jsonify({"mensagem": "Parâmetro criado com sucesso"}), 201
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500


@parametro_bp.route("/parametro/", methods=["PUT"])
def atualizar_parametro():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        cursor = g.conn.cursor()
        existing = select_dict(cursor, "SELECT * FROM parametro LIMIT 1")
        if not existing:
            cursor.close()
            return jsonify({"erro": "Parâmetro ainda não existe"}), 404

        sql, params = generate_update_sql(
            "parametro", data, where_keys=[1], where_values=[1])
        cursor.execute(sql, params)
        g.conn.commit()
        cursor.close()

        return jsonify({"mensagem": "Parâmetro atualizado com sucesso"})
    except Exception as e:
        g.conn.rollback()
        return jsonify({"erro": str(e)}), 500
