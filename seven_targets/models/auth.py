from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class SevenTargetsAuth(models.Model):
    _name = "seven.targets.auth"
    _description = "Seven Targets API Key"

    client_id = fields.Char(string="Client ID",required=True)
    client_secret = fields.Char(string="Client Secret",required=True)
    user_identifier = fields.Char(string="Seven Targets User Identifier",required=True)
    
    @api.constrains('user_identifier')
    def _check_user_identifier_unique(self):
        auth_counts = self.search_count([('user_identifier', '=', self.user_identifier), ('id', '!=', self.id)])
        if auth_counts > 0:
            raise ValidationError("User Identifier already exists!")