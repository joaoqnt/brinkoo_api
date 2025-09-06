from flask import Blueprint, jsonify
import requests

viacep_bp = Blueprint("viacep", __name__)

@viacep_bp.route("/viacep/<cep>", methods=["GET"])
def buscar_cep(cep):
    try:
        # Limpa caracteres não numéricos
        cep_limpo = ''.join(filter(str.isdigit, cep))

        # Chama API ViaCEP
        url = f"https://viacep.com.br/ws/{cep_limpo}/json/"
        response = requests.get(url, timeout=5)
        response.raise_for_status()

        dados = response.json()

        if "erro" in dados:
            return jsonify({"erro": "CEP não encontrado"}), 404

        return jsonify(dados)
    
    except requests.RequestException as e:
        return jsonify({"erro": str(e)}), 500
