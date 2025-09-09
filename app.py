from flask import Flask, request, jsonify, g
from flask_cors import CORS
from services.empresa_service import carregar_empresas_ativas, validar_tenant
from utils.db import conectar_banco_empresa
from routes.crianca_routes import crianca_bp
from routes.image_routes import image_bp
from routes.checkin_routes import checkin_bp
from routes.atividade_routes import atividade_bp
from routes.responsavel_routes import responsavel_bp
from routes.centro_custo_routes import centro_custo_bp
from routes.natureza_routes import natureza_bp
from routes.empresa_routes import empresa_bp
from routes.guarda_volume_routes import guarda_volume_bp
from routes.parceiro_routes import parceiro_bp
from routes.parametro_routes import parametro_bp
from routes.usuario_routes import usuario_bp
from routes.convenio_routes import convenio_bp
from routes.viacep_routes import viacep_bp

from routes.forma_pagamento_routes import forma_pagamento_bp
from routes.financeiro_routes import financeiro_bp

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}}, allow_headers=["*"])

# Carrega empresas ativas na inicialização
empresas_ativas = carregar_empresas_ativas()
print(f"[INFO] {len(empresas_ativas)} empresas ativas carregadas.")
app.config["EMPRESAS_ATIVAS"] = empresas_ativas


@app.before_request
def verificar_empresa_antes_da_requisicao():
    if request.method == "OPTIONS":
        return  # Libera o preflight CORS
    if not request.endpoint or request.endpoint == 'static':
        return

    tenant = request.headers.get("tenant")
    print(tenant)
    empresa = validar_tenant(tenant, empresas_ativas)

    if not empresa:
        return jsonify({"erro": "Tenant inválido ou inativo."}), 403

    g.empresa = empresa

    try:
        nome_banco = empresa['nome']
        g.conn = conectar_banco_empresa(nome_banco)
    except Exception as e:
        return jsonify({"erro": f"Erro ao conectar com banco da empresa: {str(e)}"}), 500


@app.teardown_request
def fechar_conexao(exception=None):
    conn = getattr(g, 'conn', None)
    if conn:
        conn.close()


app.register_blueprint(crianca_bp)
app.register_blueprint(image_bp)
app.register_blueprint(checkin_bp)
app.register_blueprint(atividade_bp)
app.register_blueprint(responsavel_bp)
app.register_blueprint(centro_custo_bp)
app.register_blueprint(natureza_bp)
app.register_blueprint(empresa_bp)
app.register_blueprint(guarda_volume_bp)
app.register_blueprint(parceiro_bp)
app.register_blueprint(parametro_bp)
app.register_blueprint(usuario_bp)
app.register_blueprint(forma_pagamento_bp)
app.register_blueprint(financeiro_bp)
app.register_blueprint(viacep_bp)
app.register_blueprint(convenio_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False)
