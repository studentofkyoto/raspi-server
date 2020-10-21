from pathlib import Path

from flask import Flask, jsonify, render_template, request

from lib.irrp import Irrp

from config import cofigure_app
from models import db, init_db, Code


DIST_PATH = Path(__file__).parent.resolve() / "frontend/dist"


def create_app():
    app = Flask(__name__,
                static_folder=str(DIST_PATH / 'static'),
                template_folder=str(DIST_PATH)
                )
    cofigure_app(app)
    init_db(app)

    return app


app = create_app()
irrp = Irrp()


@app.route('/')
def index(path):
    return render_template('index.html')


@app.route('/codes', methods=["GET"])
def get_all_codes():
    ret = {}
    codes = [code.as_dict() for code in Code.query.all()]
    ret["codes"] = codes

    return jsonify(ret)


@app.route('/record', methods=["POST"])
def record():
    ret = {}
    recorded = irrp.record()
    code_name = request.json["code_name"]
    if not recorded:
        return "recording failed"
    code = Code(name=code_name, code=recorded)
    code.update(db.session)
    ret["is_succsess"] = True
    ret["result"] = code.as_dict()
    return jsonify(ret)


@app.route('/record/first', methods=["GET"])
def record_first():
    ret = {}
    recorded = irrp.record_first()
    ret["is_succsess"] = True
    ret["result"] = {"code": recorded}
    return jsonify(ret)


@app.route('/record/confirm', methods=["POST"])
def record_confirm():
    ret = {}
    recorded = irrp.record_confirm()
    code_name = request.json["code_name"]
    if not recorded:
        return "recording failed"
    code = Code(name=code_name, code=recorded)
    code.update(db.session)
    ret["is_succsess"] = True
    ret["result"] = code.as_dict()
    return jsonify(ret)


@app.route("/delete", methods=["POST"])
def del_code():
    ret = {}
    code_id = request.json["id"]
    code = Code.query.filter_by(id=code_id).one()
    code.delete(db.session)
    ret["is_succsess"] = True
    return jsonify(ret)


@app.route('/playback', methods=["POST"])
def playback():
    ret = {}
    code_id = request.json["id"]
    code = Code.query.filter_by(id=code_id).one()
    code.playback()
    ret["is_succsess"] = True
    return jsonify(ret)


if __name__ == "__main__":
    app.run(debug=True)
