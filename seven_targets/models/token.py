from odoo import api, fields, models, _

class AccessToken(models.Model):
    _name = "seven.targets.access.token"
    _description = "Seven Targets Access Token"
    
    token = fields.Char()
    user_identifier = fields.Char()

