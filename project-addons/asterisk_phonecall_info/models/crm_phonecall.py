# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
import os
import pexpect
import logging
import csv

_logger = logging.getLogger(__name__)

DIR_NAME = os.path.dirname(__file__)
RELATIVE_PATH = '../cdr_logs/Master.csv'
ABSOLUTE_PATH = os.path.join(DIR_NAME, RELATIVE_PATH)

class CrmPhonecall(models.Model):
    _inherit = "crm.phonecall"

    extension = fields.Char("Extension")
    length = fields.Float("Length")
    notes = fields.Char("Notes")
    asterisk_id = fields.Char()

    # duplicated data
    tag_ids = fields.Many2many(
        comodel_name="crm.lead.tag",
        relation="crm_phonecall_tag_rel",
        column1="phone_id",
        column2="tag_id",
        string="Tags",
    )
    duration = fields.Float(help="Duration in minutes and seconds.")
    campaign_id = fields.Many2one("utm.campaign", "Campaing", readonly=True)
    source_id = fields.Many2one(
        "utm.source",
        string="Source",
        help="This is the link source, e.g. Search Engine, another domain,or name of email list",
        default=lambda self: self.env.ref("utm.utm_source_newsletter", False),
    )
    medium_id = fields.Many2one(
        "utm.medium",
        string="Medium",
        help="This is the delivery method, e.g. Postcard, Email, or Banner Ad",
        default=lambda self: self.env.ref("utm.utm_medium_email", False),
    )

    def _parse_row_vals(self, row):

        if row[3] == 'odoo-cola':
            dest = row[1]
            origin = row[2]
            direction = 'inbound'
            message = _("Asterisk Imported Incoming Call")
        else:
            dest = row[2]
            origin = row[5][4:14]
            direction = 'outbound'
            message = _("Asterisk Imported Outgoing Call")

        record_number = self.env['phone.common'].get_record_from_phone_number(dest)
        if not record_number or not record_number[0] or not record_number[1]:
            raise UserError(_("Record number {} not recognized".format(dest)))

        object_id = self.env[record_number[0]].browse(record_number[1])
        partner_id = None
        opportunity_id = None

        if record_number[0] == 'crm.lead':
            opportunity_id = object_id
            if opportunity_id.partner_id:
                partner_id = opportunity_id.partner_id
        elif record_number[0] == 'res.partner':
            partner_id = object_id
        
        if not partner_id and not opportunity_id:
            raise UserError(_("Not partner_id or opportunity_id for record number {}".format(record_number)))

        user_id = self.env['res.users'].search([
            ('resource', 'ilike', origin)
        ], limit=1)

        res = {
            "date": row[9],
            "name": message,
            "extension": origin,
            "asterisk_id": row[16],
            "length": row[12],
            "partner_id": partner_id.id if partner_id else None,
            "opportunity_id": opportunity_id.id if opportunity_id else None,
            'user_id': user_id.id if user_id else self.env.user.id,
            "direction": direction,
            "state": "done",
        }
            
        return res

    def process_asterisk_cdr_logs(self):
        # user
        user = self.env.user
        # server
        ast_server = user.get_asterisk_server_from_user()
        
        # Uncomment this if you need to download the file via scp.
        #server_name = ast_server.cdr_user+'@'+ast_server.ip_address
        #server_file = server_name+':'+ast_server.cdr_file_path
        #command = 'scp ' + server_file + ' ' + ABSOLUTE_PATH
        
        #try:   
        #    ssh = pexpect.spawn(command)
        #    ssh.expect(server_name+"'s password:")
        #    ssh.sendline(ast_server.cdr_pass)
        #    ssh.expect(pexpect.EOF, timeout=10)
        #except Exception as e:
        #    _logger.error('Unable to download the Master.csv file: {}.'.format(e))

        self.import_master_file(ast_server.cdr_last_imported_date)
        ast_server.cdr_last_imported_date = datetime.now()

    def import_master_file(self, cdr_last_imported_date):    
        _logger.info('import_master_file')

        # we use this function to remove the empty lines, otherwise we'll get an error on the loop
        def mycsv_reader(csv_reader): 
            while True: 
                try: 
                    yield next(csv_reader) 
                except StopIteration:
                    return
                except csv.Error: 
                    pass
                continue 
            return

        reader = mycsv_reader(csv.reader(open(ABSOLUTE_PATH, 'rU'), delimiter=',', quotechar='"'))
        _logger.info('reader: {}.'.format(reader))

        calls = [x for x in reader if x and x[3] in ['odoo-cola', 'from-outlet'] \
            and x[14] == 'ANSWERED' \
            and x[7] == 'Dial' \
            and datetime.strptime(x[9], "%Y-%m-%d %H:%M:%S") > cdr_last_imported_date]
        
        for line in calls:

            _logger.info('line: {}.'.format(line))

            try:

                phonecall_id = self.env['crm.phonecall'].search([
                    ("asterisk_id", "=", line[16])
                ])

                if phonecall_id:
                    phonecall_id.update({"length": line[12]})
                    _logger.info('Updated crm.phonecall: {}.'.format(phonecall_id.id))
                else:
                    row_vals = self._parse_row_vals(line)
                    if not row_vals:
                        raise UserError(_('Could not create row vals for row: {}.'.format(line)))
                        continue
                    phonecall_id = self.env['crm.phonecall'].create(row_vals)
                    _logger.info('Created crm.phonecall: {}.'.format(phonecall_id.id))
            except Exception as e:
                _logger.error('Error procesing the line with data: {}. ERROR: {}'.format(line, e))