import requests
import base64
import json
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class CRMLead(models.Model):
    _inherit = 'crm.lead'

    assistant = fields.Many2one("seven.targets.assistant", string="Assistant", tracking=True)
    lead_connection_status = fields.Many2one("seven.targets.lead.connection.status",string="Lead Connection Status", tracking=True)
    seven_targets_sequence = fields.Many2one("seven.targets.sequence", string="Seven Targets Sequence", tracking=True)
    seven_targets_lead_id = fields.Integer(default=None)
    crm_user_id = fields.Char()

    def write(self, vals):
        if len(vals) > 0 and not vals.get('iap_enrich_done'):
            first_name, last_name = self._get_first_name_and_last_name(vals)
            schedule_id = None
            if self.seven_targets_sequence.sequence_seven_targets_id not in [None, 0] and not \
                isinstance(self.seven_targets_sequence.sequence_seven_targets_id, (bool)):
                schedule_id = self.seven_targets_sequence.sequence_seven_targets_id
            lead_email = self.email_from
            if vals.get('email_from'):
                lead_email = vals.get('email_from')
            subject = self.display_name
            if vals.get('name'):
                subject = vals.get('name')
            data = {
                "name": first_name,
                "lastName": last_name, 
                "crm": "ODOO",
                "additionalInformationLine": "", 
                "email": lead_email,
                "assistantEmail" : None,
                "scheduleId" : schedule_id,
                "userTypedSubject": subject
            }

            if vals.get('assistant') and not isinstance(vals.get('assistant'), bool):
                data['assistantEmail'] = self._set_assistant_email(vals.get('assistant'))
            if self.stage_id is not None:
                data['state'] = self._set_seven_targets_state()
            if vals.get('seven_targets_sequence'):
                data['scheduleId'] = self._set_seven_targets_sequence(vals.get('seven_targets_sequence'))
            vals['lead_connection_status'] = self._set_seven_targets_state()
            bearer_token, user_identifier = self._get_seven_targets_authentication()
            if self.seven_targets_lead_id in [None,0] and data.get('assistantEmail'):
                lead = self._create_new_seven_targets_lead(data, bearer_token, user_identifier)
                if lead.get("id"):
                    vals['seven_targets_lead_id'] = lead['id']
                    vals['lead_connection_status'] = self._get_seven_targets_state_id(lead['state'])
                else:
                    vals["assistant"] = None
                    vals["seven_targets_sequence"] = None
            elif self.seven_targets_lead_id not in [None,0] and self.assistant:
                data['id'] = self.seven_targets_lead_id
                lead = self._update_existing_seven_targets_lead(data, bearer_token, user_identifier)
                if lead.get("id"):
                    vals['lead_connection_status'] = self._get_seven_targets_state_id(lead['state'])
        return super(CRMLead, self).write(vals)

    @api.model
    def _set_seven_targets_state(self):
        stage_state_mapping_model = self.env['seven.targets.lead.connection.status']
        stage_record = stage_state_mapping_model.search([('odoo_stage', '=', self.stage_id.name)], limit=1)
        if not stage_record:
            raise ValidationError("No mapping found for " + self.stage_id.name + " in Lead Connection Status Mapping")
        return stage_record.name


    @api.model
    def _get_seven_targets_state_id(self, seven_targets_lead_state):
        stage_state_mapping_model = self.env['seven.targets.lead.connection.status']
        stage_record = stage_state_mapping_model.search([('name', '=', seven_targets_lead_state)], limit=1)
        if not stage_record:
            raise ValidationError("No mapping found for Seven Targets State" + self.stage_id.name + " in Lead Connection Status Mapping")
        return stage_record.id

    @api.model
    def _set_assistant_email(self, assistant_id):
        assistant_model = self.env['seven.targets.assistant']
        assistant = assistant_model.search([("id", "=", assistant_id)], limit=1)
        if not assistant:
            raise ValidationError("Assistant Not Found")
        return assistant.email_id

    @api.model
    def _set_seven_targets_sequence(self, sequence_id):
        sequence_model = self.env['seven.targets.sequence']
        sequence = sequence_model.search([("id", "=", sequence_id)], limit=1)
        if not sequence:
            return None
        return sequence.sequence_seven_targets_id

    def _create_new_seven_targets_lead(self, data, bearer_token, user_identifier):
        headers = {
            "Authorization": "Bearer " + bearer_token,
            "7ts-user-identifier": user_identifier
        }
        response = requests.post('https://api.7targets.com/leads',
                                 data=json.dumps(data),headers=headers,timeout=30)
        if response.status_code == 201:
            lead = response.json()
            message_body = "<strong>Assistant's Note:</strong> Thanks. I will start working on this Lead. You can edit the message sequence or other details of this lead by clicking <a href=\'" + "https://solution.7targets.com/all-leads?id=" + str(lead['id'])+ "\' target='_blank'>here</a>"
            self.message_post(body=message_body)
            return lead
        else:
            self.message_post(body="Failed to create lead in 7Targets. " + response.json())
            return {}

    def _update_existing_seven_targets_lead(self, data, bearer_token, user_identifier):
        headers = {
            "Authorization": "Bearer " + bearer_token,
            "7ts-user-identifier": user_identifier
        }
        response = requests.put('https://api.7targets.com/leads',
                                data=json.dumps(data),headers=headers,timeout=30)
        if response.status_code == 200:
            self.message_post(body="Updated lead in 7Targets")
            return response.json()
        else:
            self.message_post(body="Failed to Update lead in 7Targets " + response.json())
            return {}

    def _get_seven_targets_authentication(self):
        bearer_token, user_identifier = self._get_seven_targets_token()
        if bearer_token is not None:
            return bearer_token, user_identifier
        bearer_token, user_identifier = self._create_or_update_bearer_token()
        return bearer_token, user_identifier

    @api.model
    def _get_seven_targets_token(self):
        seven_targets_token_model = self.env['seven.targets.access.token']
        token = seven_targets_token_model.search([], limit=1)
        if not token['token']:
            return None, None
        elif (datetime.now() - token.write_date).seconds/3600 > 1:
            return None, None
        return token.token, token.user_identifier

    @api.model
    def _create_or_update_bearer_token(self):
        client_id, client_secret, user_identifier = None, None, None
        seven_targets_auth_model = self.env['seven.targets.auth']
        auths = seven_targets_auth_model.search([])
        if len(auths) < 0:
            raise ValidationError('You need to set client ID, client Secret, User Identifier for Seven Targets Lead Assignment')
        values = [(auth.client_id, auth.client_secret, auth.user_identifier) for auth in auths]
        client_id, client_secret, user_identifier = values[0]
        id_secret_string = client_id + ':' + client_secret
        encoded_id_secret_string = base64.b64encode(id_secret_string.encode('ascii')).decode('ascii')
        access_token = self._get_access_token_from_seven_targets(encoded_id_secret_string)
        # Save or Update Access Token
        if access_token is not None:
            self._save_or_update_access_token(access_token, user_identifier)
        return access_token, user_identifier

    @api.model
    def _set_sequence_using_seven_targets_sequence_id(self, sequence_id):
        sequence_model = self.env['seven.targets.sequence']
        sequence = sequence_model.search([("sequence_seven_targets_id", "=", sequence_id)], limit=1)
        if not sequence:
            return None
        return sequence.id
        
    @api.model
    def _save_or_update_access_token(self, access_token, user_identifier):
        seven_targets_token_model = self.env['seven.targets.access.token']
        token = seven_targets_token_model.search([],limit=1)
        if token['token']:
            token.token = access_token
            token.write({'token': access_token})
            self.env.cr.commit()
        else:
            seven_targets_token_model.create({'token':access_token, 'user_identifier':user_identifier})
            self.env.cr.commit()


    def _get_access_token_from_seven_targets(self, encoded_id_secret_string):
        headers = {
            'Authorization': 'Basic ' + encoded_id_secret_string,
            'content-type': 'application/x-www-form-urlencoded',
        }
        data = {
            'grant_type':'client_credentials',
            'scope':'leads/post'
        }
        response = requests.post('https://login.7targets.com/oauth2/token',
                                 headers=headers,data=data)
        if response.status_code == 200:
            return response.json()['access_token']
        else:
            raise ValidationError('Unable to save lead on 7targets')

    def _get_first_name_and_last_name(self, vals):
        """
        Validate If Contact Name is not Empty
        Extract First & Last Name 
        """
        contact_name = None
        if vals.get('contact_name'):
            contact_name = vals['contact_name']
        else:
            contact_name = self.contact_name
        first_name, last_name = None, None
        if not contact_name or contact_name is None or contact_name.strip() == "":
            raise ValidationError("Contact Name is required to assign Lead to Seven Targets Assistant")
        else:
            contact_name_list = contact_name.split(" ")
            first_name = contact_name_list[0]
            last_name = None
            if len(contact_name_list) > 1:
                last_name = contact_name_list[-1]
        return first_name, last_name
