from typing import Dict, List

from backend.lib.irrp import Irrp
from .database import db


class Code(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    code = db.Column(db.PickleType, nullable=False)

    def __init__(self,
                 name: str,
                 code: List):
        self.name = name
        self.code = code

    def playback(self):
        Irrp().playback(self.code)

    def delete(self, session: db.session):
        session.delete(self)
        session.commit()

    def as_dict(self) -> Dict:
        ret = {
            "name": self.name,
            "id": self.id,
            "code": self.code
        }
        return ret

    def update(self, session: db.session):
        session.add(self)
        session.commit()
