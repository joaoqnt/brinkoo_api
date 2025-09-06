from flask import Blueprint, request, jsonify, g
from werkzeug.utils import secure_filename
import os
import paramiko
import traceback  # <-- Adicionado

image_bp = Blueprint('image_bp', __name__)

REMOTE_HOST = '216.238.116.111'
REMOTE_PORT = 22
REMOTE_USER = 'root'  # substitua
REMOTE_PASS = 'u6]LiT[3#Xgi_wR)'    # ou use chave SSH
REMOTE_DIR_BASE = '/var/www/imagens'


@image_bp.route('/upload', methods=['POST'])
def upload_imagem():
    pasta = request.form.get('pasta')
    imagem = request.files.get('imagem')

    if not pasta or not imagem:
        return jsonify({'erro': 'Pasta e imagem são obrigatórios'}), 400

    nome_arquivo = secure_filename(imagem.filename)
    caminho_remoto = f"{REMOTE_DIR_BASE}/{pasta}/{nome_arquivo}"

    caminho_tmp = f"/tmp/{nome_arquivo}"
    imagem.save(caminho_tmp)

    try:
        transport = paramiko.Transport((REMOTE_HOST, REMOTE_PORT))
        transport.connect(username=REMOTE_USER, password=REMOTE_PASS)
        sftp = paramiko.SFTPClient.from_transport(transport)

        # Cria diretório remoto
        try:
            sftp.mkdir(f"{REMOTE_DIR_BASE}/{pasta}")
        except IOError:
            pass  # já existe

        # Upload do arquivo
        sftp.put(caminho_tmp, caminho_remoto)

        sftp.close()
        transport.close()

        os.remove(caminho_tmp)

        return jsonify({
            'mensagem': 'Imagem enviada com sucesso',
            'caminho': caminho_remoto
        })

    except Exception as e:
        print("Erro durante upload:")
        traceback.print_exc()  # <-- Mostra a stack completa no terminal
        return jsonify({
            'erro': 'Falha ao enviar imagem',
            'detalhes': str(e)
        }), 500


@image_bp.route("/criancas/exportar_imagens", methods=["POST"])
def exportar_imagens():
    try:
        # Paginação
        limit = request.args.get("limit", type=int, default=50000)
        offset = request.args.get("offset", type=int, default=0)

        cursor = g.conn.cursor()
        cursor.execute("""
            SELECT id, imagem
            FROM crianca
            WHERE imagem IS NOT NULL
            ORDER BY id
            LIMIT %s OFFSET %s
        """, (limit, offset))
        registros = cursor.fetchall()
        cursor.close()

        if not registros:
            return jsonify({"mensagem": "Nenhuma imagem encontrada nesse lote"}), 200

        # Conexão SSH
        transport = paramiko.Transport((REMOTE_HOST, REMOTE_PORT))
        transport.connect(username=REMOTE_USER, password=REMOTE_PASS)
        sftp = paramiko.SFTPClient.from_transport(transport)

        pasta = f"{REMOTE_DIR_BASE}/00000000000000/criança"
        try:
            sftp.mkdir(pasta)
        except IOError:
            pass  # já existe

        enviados = []
        for crianca_id, imagem_blob in registros:
            if not imagem_blob:
                continue

            nome_arquivo = f"{crianca_id}.png"
            caminho_tmp = f"/tmp/{nome_arquivo}"

            # Salva tmp
            with open(caminho_tmp, "wb") as f:
                f.write(imagem_blob)

            # Envia remoto
            caminho_remoto = f"{pasta}/{nome_arquivo}"
            sftp.put(caminho_tmp, caminho_remoto)
            enviados.append(caminho_remoto)

            os.remove(caminho_tmp)

        sftp.close()
        transport.close()

        return jsonify({
            "mensagem": f"{len(enviados)} imagens exportadas",
            "arquivos": enviados
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"erro": str(e)}), 500
