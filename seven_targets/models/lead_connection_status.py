from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class SevenTargetsLeadConnectionStatus(models.Model):
    _name = "seven.targets.lead.connection.status"
    _description = "Seven Targets Lead Connection Status Mapping"
    
    name = fields.Selection([('Cold','Cold'),('Engaged','Engaged'),('Warm', 'Warm'),('Hot','Hot'),('Responded','Responded'),('DeActivated','DeActivated'),('UnSubscribed','UnSubscribed'),('Processed','Processed'),('Pending','Pending'),('New','New'),],string="Seven Targets State", required=True)
    odoo_stage = fields.Many2one("crm.stage",string="Odoo Stage", required=True)
    
    @api.constrains('odoo_stage')
    def _check_unique_odoo_stage(self):
        for record in self:
            if record.odoo_stage:
                domain = [('odoo_stage', '=', record.odoo_stage.id)]
                if self.search_count(domain) > 1:
                    raise ValidationError("Odoo Stage already exists!")