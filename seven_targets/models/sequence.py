from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class SevenTargetsSequence(models.Model):
    _name = "seven.targets.sequence"
    _description = "Seven Targets Sequence"
    
    name = fields.Char(string="Sequence Name", required=True)
    sequence_seven_targets_id = fields.Integer(required=True)
    
    @api.constrains('sequence_seven_targets_id')
    def _check_sequence_unique(self):
        sequence_counts = self.search_count([('sequence_seven_targets_id', '=', self.sequence_seven_targets_id), ('id', '!=', self.id)])
        if sequence_counts > 0:
            raise ValidationError("Sequence already exists!")