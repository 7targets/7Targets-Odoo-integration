from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class SevenTargetsLeadConnectionStatus(models.Model):
    _name = "seven.targets.lead.connection.status"
    _description = "Seven Targets Lead Connection Status Mapping"
    
    name = fields.Selection([('Cold','Cold'),('Engaged','Engaged'),('Warm', 'Warm'),('Hot','Hot'),('Responded','Responded'),('DeActivated','DeActivated'),('UnSubscribed','UnSubscribed'),('Processed','Processed'),('Pending','Pending'),('New','New'),],string="Seven Targets State", required=True)
    odoo_stage = fields.Selection([],string="Odoo Stage", required=True)
    
    @api.model
    def _get_odoo_stage_values(self):
        odoo_stage_model = self.env['crm.stage']
        odoo_stages = odoo_stage_model.search([])
        values = [(odoo_stage.name, odoo_stage.name) for odoo_stage in odoo_stages]
        return values
    
    odoo_stage = fields.Selection(_get_odoo_stage_values, string="Odoo Stage")
    
    @api.constrains('odoo_stage')
    def _check_odoo_stage_unique(self):
        odoo_stage_counts = self.search_count([('odoo_stage', '=', self.odoo_stage), ('id', '!=', self.id)])
        if odoo_stage_counts > 0:
            raise ValidationError("Odoo Stage already exists!")