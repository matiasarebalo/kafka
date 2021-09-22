from ma import ma
from marshmallow import fields
from .user import UserSchema

class MeSchema(ma.Schema):
    id = fields.Int(dump_only=True)
    followname = fields.Str()
    user = fields.Nested(UserSchema)
    followid = fields.Int(dump_only=True)
