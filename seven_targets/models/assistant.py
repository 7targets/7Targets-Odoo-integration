import re
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _

class SevenTargetsAssistant(models.Model):
    _name = "seven.targets.assistant"
    _description = "Seven Targets Assistants"
    
    name = fields.Char(string="Assistant Name", required=True)
    email_id = fields.Char(string="Assistant Email", required=True)
    seven_targets_assistant_id = fields.Integer(required=True)

    @api.onchange('email_id')
    def validate_mail(self):
        if self.email_id:
            match = re.match('^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', self.email_id)
            if match == None:
                raise ValidationError('Not a valid Email ID')
    
    @api.constrains('email_id')
    def _check_assistant_unique(self):
        assistant_counts = self.search_count([('email_id', '=', self.email_id), ('id', '!=', self.id)])
        if assistant_counts > 0:
            raise ValidationError("Assistant already exists!")