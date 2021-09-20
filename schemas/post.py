from ma import ma
from marshmallow import fields
from .user import UserSchema

class PostSchema(ma.Schema):
    id = fields.Int(dump_only=True)
    title = fields.Str()
    text = fields.Str()
    img = fields.Str()
    date = fields.DateTime()
    user = fields.Nested(UserSchema)

