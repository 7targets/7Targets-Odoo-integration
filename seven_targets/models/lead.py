import requests
import base64
import json
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class CRMLead(models.Model):
    _inherit = 'crm.lead'
    
    assistant = fields.Selection([], string="Assistant", tracking=True)
    lead_connection_status = fields.Selection([],string="Lead Connection Status", tracking=True)
    seven_targets_sequence = fields.Selection([], string="Seven Targets Sequence", tracking=True)
    seven_targets_lead_id = fields.Integer(default=None)
    crm_user_id = fields.Char()
    
    @api.model
    def _get_assistant_values(self):
        assistant_model = self.env['seven.targets.assistant']
        assistants = assistant_model.search([])
        values = [(assistant.email_id, assistant.name) for assistant in assistants]
        return values

    assistant = fields.Selection(_get_assistant_values, string='Assistant')
    
    @api.model
    def _get_sequence_values(self):
        sequence_model = self.env['seven.targets.sequence']
        sequences = sequence_model.search([])
        values = [(str(sequence.sequence_seven_targets_id), sequence.name) for sequence in sequences]
        return values

    seven_targets_sequence = fields.Selection(_get_sequence_values, string='Seven Targets Sequence')
    
    @api.model
    def _get_lead_connection_status_values(self):
        """
        Get Dropdown list values
        """
        lead_connection_status_model = self.env['seven.targets.lead.connection.status']
        lead_connection_status = lead_connection_status_model.search([])
        values = [(status.seven_targets_state, status.odoo_stage) for status in lead_connection_status]
        return values
    
    lead_connection_status = fields.Selection(_get_lead_connection_status_values, string="Lead Connection Status")
    
    def write(self, vals):
        if len(vals) > 0 and not vals.get('iap_enrich_done'):
            first_name, last_name = self._get_first_name_and_last_name(vals)
            schedule_id = None
            if self.seven_targets_sequence is not None and not \
                isinstance(self.seven_targets_sequence, (bool)):
                schedule_id = self.seven_targets_sequence
            data = {
                "name": first_name,
                "lastName": last_name, 
                "crm": "ODOO",
                "additionalInformationLine": "", 
                "email": self.email_from,
                "assistantEmail" : None,
                "scheduleId" : schedule_id
            }
            if not vals.get('assistant') and not self.assistant:
                raise ValidationError("Select an assistant to assign Lead to Seven Targets.")
            if vals.get('assistant') and not isinstance(vals.get('assistant'), (bool)):
                data['assistantEmail'] = vals['assistant']
            if self.stage_id is not None:
                data['state'] = self._set_seven_targets_state()
            if vals.get('seven_targets_sequence'):
                data['scheduleId'] = vals['seven_targets_sequence']
            vals['lead_connection_status'] = self._set_seven_targets_state()
            bearer_token, user_identifier = self._get_seven_targets_authentication()
            if self.seven_targets_lead_id in [None,0]:
                seven_targets_lead_id = self._create_new_seven_targets_lead(data, bearer_token, user_identifier)
                if seven_targets_lead_id is not None:
                    vals['seven_targets_lead_id'] = seven_targets_lead_id
            else:
                data['id'] = self.seven_targets_lead_id
                self._update_existing_seven_targets_lead(data, bearer_token, user_identifier)
        return super(CRMLead, self).write(vals)
        
    
    @api.model
    def _set_seven_targets_state(self):
        stage_state_mapping_model = self.env['seven.targets.lead.connection.status']
        stage_record = stage_state_mapping_model.search([('odoo_stage', '=', self.stage_id.name)], limit=1)
        if not stage_record:
            raise ValidationError("No mapping found for " + self.stage_id.name + " in Lead Connection Status Mapping")
        return stage_record.seven_targets_state
        
    
    def _create_new_seven_targets_lead(self, data, bearer_token, user_identifier):
        headers = {
            "Authorization": "Bearer " + bearer_token,
            "7ts-user-identifier": user_identifier
        }
        response = requests.post('https://api-qa.7targets.com/leads',
                                 data=json.dumps(data),headers=headers,timeout=30)
        print("Creating a Lead")
        print(response.text)
        if response.status_code == 200:
            lead = response.json()
            self._add_note_for_lead(lead['id'])
            return lead['id']
        else:
            # add Failure Note
            # Remove Assistant & Schedule
            # raise ValidationError(response.json()['message'])
            return None

    def _update_existing_seven_targets_lead(self, data, bearer_token, user_identifier):
        headers = {
            "Authorization": "Bearer " + bearer_token,
            "7ts-user-identifier": user_identifier,
        }
        response = requests.put('https://api-qa.7targets.com/leads',
                                data=json.dumps(data),headers=headers,timeout=30)
        print("Updating a Lead")
        print(response.text)
        if response.status_code == 201:
            print("Lead Updated")
            # add Note
        else:
            # add Failure Note
            # Remove Assistant & Schedule
            print(response.text)
    
    @api.model
    def _add_note_for_lead(self,seven_targets_lead_id):
        log_note = {
            'model': 'crm.lead',
            'res_id': self.id,
            'message_type': 'notification',
            'body': "<strong>Assistant's Note:</strong> Thanks. I will start working on this. You can edit the message sequence or other details of this lead by clicking <a href=\'" + "https://solution-qa.7targets.com/all-leads?id=" + str(seven_targets_lead_id) + "\' target='_blank'>here</a>"
        }
        self.env['mail.message'].create(log_note)

    
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
            print("Token Not Found")
            return None, None
        elif (datetime.now() - token.write_date).seconds/3600 > 1:
            print("Bearer Token Expired")
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
    def _save_or_update_access_token(self, access_token, user_identifier):
        seven_targets_token_model = self.env['seven.targets.access.token']
        token = seven_targets_token_model.search([],limit=1)
        if token['token']:
            token.token = access_token
            token.write({'token': access_token})
            self.env.cr.commit()
            print("Updating Token")
        else:
            seven_targets_token_model.create({'token':access_token, 'user_identifier':user_identifier})
            self.env.cr.commit()
            print("Creating a token")


    def _get_access_token_from_seven_targets(self, encoded_id_secret_string):
        headers = {
            'Authorization': 'Basic ' + encoded_id_secret_string,
            'content-type': 'application/x-www-form-urlencoded',
        }
        data = {
            'grant_type':'client_credentials',
            'scope':'leads/post'
        }
        response = requests.post('https://login-qa.7targets.com/oauth2/token',
                                 headers=headers,data=data)
        if response.status_code == 200:
            print(response.json()['access_token'])
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
    