# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import requests
import json
import logging
from datetime import datetime, date

_logger = logging.getLogger(__name__)


class AviationTicket(models.Model):
    _name = 'aviation.ticket'
    _description = 'Aviation Ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'ticket_no'
    _order = 'transaction_date desc, id desc'

    # ─── Core Ticket Fields ───────────────────────────────────────────────────
    ticket_no = fields.Char(
        string='Ticket Number', size=50, required=True, copy=False,
        index=True, tracking=True,
        help='Unique ticket identifier'
    )
    passenger_name = fields.Char(string='Passenger Name', size=255)
    rloc = fields.Char(string='RLOC / PNR', size=20)
    ticket_class = fields.Char(string='Class', size=10)
    fare_basis = fields.Char(string='Fare Basis', size=20)
    product_code = fields.Char(string='Product Code', size=20)

    # ─── Flight Info ─────────────────────────────────────────────────────────
    flight_no = fields.Char(string='Flight Number')
    flight_date = fields.Char(string='Flight Date', size=120)
    route = fields.Char(string='Route', size=20)
    transaction_date = fields.Char(string='Transaction Date')
    date_of_issue = fields.Char(string='Date of Issue', size=120)
    ticket_expires = fields.Date(string='Ticket Expiry Date')
    created_at = fields.Datetime(string='Created At', default=fields.Datetime.now)

    # ─── Ticket Status ────────────────────────────────────────────────────────
    status = fields.Selection([
        ('flown', 'Flown'),
        ('unutilised', 'Unutilised / Open'),
        ('expired', 'Expired'),
        ('refunded', 'Refunded'),
        ('reissued', 'Reissued'),
        ('void', 'Void'),
        ('cancelled', 'Cancelled'),
    ], string='Status', size=10, tracking=True, index=True)

    et_status = fields.Char(string='ET Status', size=5)

    # ─── Point of Sale ────────────────────────────────────────────────────────
    pos_channel = fields.Selection([
        ('paystack', 'Paystack (Online)'),
        ('airvend', 'Airvend'),
        ('gds', 'GDS (Global Distribution System)'),
        ('website', 'Website'),
        ('mobile_app', 'Mobile App'),
        ('agent', 'Travel Agent'),
        ('bank', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('charter', 'Charter'),
        ('other', 'Other'),
    ], string='Point of Sale / Channel', index=True, tracking=True)

    sale_type = fields.Selection([
        ('direct', 'Direct Sale'),
        ('indirect', 'Indirect / Agency Sale'),
    ], string='Sale Type', tracking=True)

    gds_name = fields.Char(string='GDS Name', size=50,
                            help='e.g. Amadeus, Sabre, Galileo')
    agent_code = fields.Char(string='Agent Code / IATA', size=20)
    agent_name = fields.Char(string='Agency Name', size=120)
    issue_agent_id = fields.Char(string='Issue Agent ID', size=20)
    issue_office = fields.Char(string='Issue Office', size=20)

    # ─── Fare & Currency ─────────────────────────────────────────────────────
    fare_curr = fields.Char(string='Fare Currency', size=5)
    fop = fields.Char(string='Form of Payment', size=50)
    fop_desc = fields.Char(string='FOP Description', size=50)

    # ─── Financial Fields ────────────────────────────────────────────────────
    face_value = fields.Float(string='Face Value', digits=(15, 2))
    net_fare = fields.Float(string='Net Fare', digits=(15, 2))
    comm = fields.Float(string='Commission', digits=(15, 2))
    comm_pct = fields.Float(string='Commission %', digits=(5, 2),
                             compute='_compute_comm_pct', store=True)
    net_sales = fields.Float(string='Net Sales (After Commission)',
                              compute='_compute_net_sales', store=True,
                              digits=(15, 2))

    # ─── Tax Fields ───────────────────────────────────────────────────────────
    # G5 = PSC (Passenger Service Charge)
    g5 = fields.Float(string='G5 (PSC)', digits=(15, 2))
    # NG = Nigerian tax
    ng = fields.Float(string='NG Tax', digits=(15, 2))
    # QT = Other government tax
    qt = fields.Float(string='QT Tax', digits=(15, 2))
    # S9 = Security charge
    s9 = fields.Float(string='S9 (Security)', digits=(15, 2))
    # TE = Ticket surcharge
    te = fields.Float(string='TE Surcharge', digits=(15, 2))
    # YQ = Fuel surcharge
    yq = fields.Float(string='YQ (Fuel Surcharge)', digits=(15, 2))
    # XT = Miscellaneous taxes
    xt = fields.Float(string='XT (Misc Taxes)', digits=(15, 2))
    other_tax = fields.Float(string='Other Tax', digits=(15, 2))

    total_taxes = fields.Float(string='Total Taxes & Fees',
                                compute='_compute_totals', store=True,
                                digits=(15, 2))
    total_amount = fields.Float(string='Total Amount',
                                 compute='_compute_totals', store=True,
                                 digits=(15, 2))

    # ─── VAT ──────────────────────────────────────────────────────────────────
    vat_amount = fields.Float(string='VAT Amount', digits=(15, 2))
    psc_amount = fields.Float(string='PSC Amount', digits=(15, 2),
                               compute='_compute_psc', store=True)

    # ─── Refund / Reissue ────────────────────────────────────────────────────
    is_refund = fields.Boolean(string='Is Refund', tracking=True)
    is_reissue = fields.Boolean(string='Is Reissue', tracking=True)
    original_ticket_id = fields.Many2one('aviation.ticket',
                                          string='Original Ticket',
                                          ondelete='set null')
    refund_date = fields.Date(string='Refund/Reissue Date')
    refund_amount = fields.Float(string='Refund Amount', digits=(15, 2))
    refund_channel = fields.Selection([
        ('paystack', 'Paystack'),
        ('airvend', 'Airvend'),
        ('bank', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('agent', 'Through Agent'),
        ('other', 'Other'),
    ], string='Refund Channel')
    refund_reason = fields.Text(string='Refund / Cancellation Reason')

    # ─── Ancillary Services ──────────────────────────────────────────────────
    ancillary_ids = fields.One2many('aviation.ancillary', 'ticket_id',
                                     string='Ancillary Services')
    total_ancillary = fields.Float(string='Total Ancillary Revenue',
                                    compute='_compute_ancillary', store=True,
                                    digits=(15, 2))

    # ─── Sync ─────────────────────────────────────────────────────────────────
    sync_source = fields.Char(string='Sync Source', size=50)
    external_id = fields.Char(string='External Reference', size=100, index=True)
    last_synced = fields.Datetime(string='Last Synced')

    # ─── Computed Fields ─────────────────────────────────────────────────────

    @api.depends('face_value', 'comm')
    def _compute_comm_pct(self):
        for rec in self:
            rec.comm_pct = (rec.comm / rec.face_value * 100) if rec.face_value else 0.0

    @api.depends('face_value', 'comm')
    def _compute_net_sales(self):
        for rec in self:
            rec.net_sales = rec.face_value - rec.comm

    @api.depends('g5', 'ng', 'qt', 's9', 'te', 'yq', 'xt', 'other_tax', 'vat_amount')
    def _compute_totals(self):
        for rec in self:
            rec.total_taxes = (
                rec.g5 + rec.ng + rec.qt + rec.s9 +
                rec.te + rec.yq + rec.xt + rec.other_tax + rec.vat_amount
            )
            rec.total_amount = rec.face_value + rec.total_taxes

    @api.depends('g5')
    def _compute_psc(self):
        for rec in self:
            rec.psc_amount = rec.g5  # G5 is PSC

    @api.depends('ancillary_ids.amount')
    def _compute_ancillary(self):
        for rec in self:
            rec.total_ancillary = sum(rec.ancillary_ids.mapped('amount'))

    # ─── Constraints ─────────────────────────────────────────────────────────

    _sql_constraints = [
        ('ticket_no_uniq', 'UNIQUE(ticket_no)', 'Ticket number must be unique!'),
    ]

    # ─── Business Logic ───────────────────────────────────────────────────────

    def action_mark_flown(self):
        self.write({'status': 'flown'})

    def action_mark_expired(self):
        self.write({'status': 'expired'})

    def action_refund(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Process Refund',
            'res_model': 'aviation.refund.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_ticket_id': self.id},
        }

    def action_reissue(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reissue Ticket',
            'res_model': 'aviation.reissue.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_original_ticket_id': self.id},
        }


class AviationTicketSyncConfig(models.Model):
    _name = 'aviation.sync.config'
    _description = 'Aviation Sync Configuration'
    _rec_name = 'name'

    name = fields.Char(string='Configuration Name', required=True)
    api_url = fields.Char(string='Integration Service URL', required=True,
                           help='Base URL of your integration service endpoint')
    api_key = fields.Char(string='API Key / Token', groups='base.group_system')
    api_secret = fields.Char(string='API Secret', groups='base.group_system')
    auth_type = fields.Selection([
        ('none', 'No Auth'),
        ('api_key', 'API Key (Header)'),
        ('bearer', 'Bearer Token'),
        ('basic', 'Basic Auth'),
    ], string='Auth Type', default='bearer')
    auth_header_name = fields.Char(string='Auth Header Name',
                                    default='Authorization')
    active = fields.Boolean(default=True)
    batch_size = fields.Integer(string='Batch Size', default=500)
    last_sync_date = fields.Datetime(string='Last Successful Sync')
    sync_log_ids = fields.One2many('aviation.sync.log', 'config_id',
                                    string='Sync Logs')

    def action_test_connection(self):
        self.ensure_one()
        try:
            headers = self._get_auth_headers()
            resp = requests.get(self.api_url, headers=headers, timeout=10)
            resp.raise_for_status()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Successful'),
                    'message': _('Connected to integration service. Status: %s') % resp.status_code,
                    'sticky': False,
                    'type': 'success',
                },
            }
        except Exception as e:
            raise UserError(_('Connection failed: %s') % str(e))

    def _get_auth_headers(self):
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        if self.auth_type == 'bearer':
            headers['Authorization'] = 'Bearer %s' % (self.api_key or '')
        elif self.auth_type == 'api_key':
            headers[self.auth_header_name or 'X-API-Key'] = self.api_key or ''
        elif self.auth_type == 'basic':
            import base64
            cred = base64.b64encode(
                ('%s:%s' % (self.api_key, self.api_secret)).encode()
            ).decode()
            headers['Authorization'] = 'Basic %s' % cred
        return headers

    def action_sync_now(self):
        self.ensure_one()
        return self._run_sync()

    def _run_sync(self):
        """Fetch tickets from the integration service and upsert into Odoo."""
        self.ensure_one()
        log = self.env['aviation.sync.log'].create({
            'config_id': self.id,
            'start_time': fields.Datetime.now(),
            'status': 'running',
        })
        created = updated = errors = 0
        try:
            headers = self._get_auth_headers()
            page = 1
            has_more = True
            while has_more:
                params = {'page': page, 'limit': self.batch_size}
                resp = requests.get(
                    self.api_url, headers=headers,
                    params=params, timeout=60
                )
                resp.raise_for_status()
                payload = resp.json()

                # Support both {"data": [...]} and plain list responses
                records = payload.get('data', payload) if isinstance(payload, dict) else payload
                if not records:
                    has_more = False
                    break

                for item in records:
                    try:
                        vals = self._map_record(item)
                        existing = self.env['aviation.ticket'].search(
                            [('ticket_no', '=', vals['ticket_no'])], limit=1
                        )
                        if existing:
                            existing.write(vals)
                            updated += 1
                        else:
                            self.env['aviation.ticket'].create(vals)
                            created += 1
                    except Exception as e:
                        errors += 1
                        _logger.error('Sync error for ticket %s: %s',
                                      item.get('ticket_no', 'N/A'), str(e))

                # Pagination: stop if fewer records than batch size
                if len(records) < self.batch_size:
                    has_more = False
                else:
                    page += 1

            self.last_sync_date = fields.Datetime.now()
            log.write({
                'end_time': fields.Datetime.now(),
                'status': 'success',
                'records_created': created,
                'records_updated': updated,
                'records_failed': errors,
                'message': 'Sync completed: %d created, %d updated, %d errors' % (
                    created, updated, errors),
            })
        except Exception as e:
            log.write({
                'end_time': fields.Datetime.now(),
                'status': 'failed',
                'message': str(e),
            })
            raise UserError(_('Sync failed: %s') % str(e))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sync Complete'),
                'message': _('%d created, %d updated, %d errors') % (
                    created, updated, errors),
                'sticky': errors > 0,
                'type': 'success' if not errors else 'warning',
            },
        }

    def _map_record(self, item):
        """Map JSON record from integration service → aviation.ticket vals."""
        def safe_float(val):
            try:
                return float(val) if val is not None else 0.0
            except (ValueError, TypeError):
                return 0.0

        # Determine POS channel from form of payment or product code
        fop = (item.get('fop') or '').lower()
        product = (item.get('product_code') or '').lower()
        pos_channel = 'other'
        if 'paystack' in fop or 'paystack' in product:
            pos_channel = 'paystack'
        elif 'airvend' in fop or 'airvend' in product:
            pos_channel = 'airvend'
        elif 'gds' in product or item.get('issue_office', '').startswith('GDS'):
            pos_channel = 'gds'
        elif 'web' in fop or 'online' in fop:
            pos_channel = 'website'
        elif 'mobile' in fop or 'app' in fop:
            pos_channel = 'mobile_app'
        elif 'cash' in fop:
            pos_channel = 'cash'
        elif 'bank' in fop or 'transfer' in fop:
            pos_channel = 'bank'
        elif item.get('issue_agent_id'):
            pos_channel = 'agent'

        sale_type = 'indirect' if pos_channel == 'agent' else 'direct'

        # Parse ticket_expires date
        ticket_expires = None
        raw_exp = item.get('ticket_expires') or item.get('ticketExpires')
        if raw_exp:
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
                try:
                    ticket_expires = datetime.strptime(str(raw_exp), fmt).date()
                    break
                except ValueError:
                    pass

        return {
            'ticket_no': item.get('ticket_no') or item.get('ticketNo', ''),
            'passenger_name': item.get('passenger_name') or item.get('passenger'),
            'rloc': item.get('rloc'),
            'ticket_class': item.get('class') or item.get('ticketClass'),
            'fare_basis': item.get('fare_basis') or item.get('fareBasis'),
            'product_code': item.get('product_code') or item.get('productCode'),
            'transaction_date': item.get('transaction_date') or item.get('transactionDate'),
            'flight_no': item.get('flight_no') or item.get('flightNo'),
            'flight_date': item.get('flight_date') or item.get('flightDate'),
            'route': item.get('route'),
            'status': self._map_status(item.get('status')),
            'et_status': item.get('et_status') or item.get('etStatus'),
            'fare_curr': item.get('fare_curr') or item.get('fareCurr'),
            'face_value': safe_float(item.get('face_value') or item.get('faceValue')),
            'g5': safe_float(item.get('g5')),
            'ng': safe_float(item.get('ng')),
            'qt': safe_float(item.get('qt')),
            's9': safe_float(item.get('s9')),
            'te': safe_float(item.get('te')),
            'yq': safe_float(item.get('yq')),
            'xt': safe_float(item.get('xt')),
            'date_of_issue': item.get('date_of_issue') or item.get('dateOfIssue'),
            'other_tax': safe_float(item.get('other_tax') or item.get('otherTax')),
            'comm': safe_float(item.get('comm')),
            'net_fare': safe_float(item.get('net_fare') or item.get('netFare')),
            'fop': item.get('fop'),
            'fop_desc': item.get('fop_desc') or item.get('fopDesc'),
            'issue_agent_id': item.get('issue_agent_id') or item.get('issueAgentId'),
            'issue_office': item.get('issue_office') or item.get('issueOffice'),
            'ticket_expires': ticket_expires,
            'pos_channel': pos_channel,
            'sale_type': sale_type,
            'sync_source': 'integration_service',
            'last_synced': fields.Datetime.now(),
            'external_id': str(item.get('id') or item.get('ticket_no', '')),
        }

    def _map_status(self, raw):
        mapping = {
            'flown': 'flown', 'fl': 'flown', 'used': 'flown',
            'open': 'unutilised', 'unused': 'unutilised', 'active': 'unutilised',
            'expired': 'expired', 'exp': 'expired',
            'refunded': 'refunded', 'ref': 'refunded',
            'reissued': 'reissued', 'rei': 'reissued',
            'void': 'void', 'cancelled': 'cancelled', 'cancel': 'cancelled',
        }
        return mapping.get((raw or '').lower(), 'unutilised')
