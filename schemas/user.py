from ma import ma
from marshmallow import fields

class UserSchema(ma.Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str()
    username = fields.Str()
    #posts = fields.List(fields.Nested(PostSchema))
