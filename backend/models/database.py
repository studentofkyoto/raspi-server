from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import sqlalchemy as sa

db = SQLAlchemy()


def init_db(app):
    db.init_app(app)
    Migrate(app, db)
    engine = db.get_engine(app)
    if sa.inspect(engine).get_table_names() == []:
        with app.test_request_context():
            db.create_all()
            print('databse created')
