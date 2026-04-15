# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AviationReportWizard(models.TransientModel):
    _name = 'aviation.report.wizard'
    _description = 'Aviation Report Wizard'

    report_type = fields.Selection([
        ('ticket_sales', '1. Ticket Sales (Direct & Indirect)'),
        ('pos_summary', '2. Sales by Point of Sale'),
        ('commission', '3. Agency Commissions'),
        ('refunds', '4. Refunds & Reissues'),
        ('taxes', '5. Taxes & Regulatory Fees'),
        ('ticket_status', '6. Flown / Unutilised / Expired Tickets'),
        ('ancillary', '7. Ancillary Revenue (Baggage, Cargo, Charter)'),
    ], string='Report Type', required=True, default='ticket_sales')

    date_from = fields.Date(string='Date From', required=True,
                             default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date(string='Date To', required=True,
                           default=fields.Date.today)

    pos_channel = fields.Selection([
        ('all', 'All Channels'),
        ('paystack', 'Paystack'),
        ('airvend', 'Airvend'),
        ('gds', 'GDS'),
        ('website', 'Website'),
        ('mobile_app', 'Mobile App'),
        ('agent', 'Travel Agent'),
        ('bank', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('charter', 'Charter'),
    ], string='Point of Sale', default='all')

    sale_type = fields.Selection([
        ('all', 'All'),
        ('direct', 'Direct Sales'),
        ('indirect', 'Indirect / Agency Sales'),
    ], string='Sale Type', default='all')

    status = fields.Selection([
        ('all', 'All Statuses'),
        ('flown', 'Flown'),
        ('unutilised', 'Unutilised'),
        ('expired', 'Expired'),
        ('refunded', 'Refunded'),
        ('reissued', 'Reissued'),
    ], string='Ticket Status', default='all')

    currency = fields.Char(string='Currency Filter', size=5)
    include_ancillary = fields.Boolean(string='Include Ancillary Revenue',
                                        default=True)
    group_by = fields.Selection([
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
        ('pos_channel', 'Point of Sale'),
        ('route', 'Route'),
        ('agent', 'Agent'),
        ('status', 'Status'),
    ], string='Group By', default='month')

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from > rec.date_to:
                raise ValidationError(_('Date From must be before Date To.'))

    def _build_domain(self):
        domain = []
        if self.date_from:
            domain += [('transaction_date', '>=', str(self.date_from))]
        if self.date_to:
            domain += [('transaction_date', '<=', str(self.date_to))]
        if self.pos_channel and self.pos_channel != 'all':
            domain += [('pos_channel', '=', self.pos_channel)]
        if self.sale_type and self.sale_type != 'all':
            domain += [('sale_type', '=', self.sale_type)]
        if self.status and self.status != 'all':
            domain += [('status', '=', self.status)]
        if self.currency:
            domain += [('fare_curr', '=', self.currency)]
        return domain

    def action_print_report(self):
        self.ensure_one()
        report_map = {
            'ticket_sales': 'aviation_ticket_management.action_report_ticket_sales',
            'pos_summary': 'aviation_ticket_management.action_report_ticket_sales',
            'commission': 'aviation_ticket_management.action_report_commission',
            'refunds': 'aviation_ticket_management.action_report_refund',
            'taxes': 'aviation_ticket_management.action_report_tax',
            'ticket_status': 'aviation_ticket_management.action_report_ticket_status',
            'ancillary': 'aviation_ticket_management.action_report_ticket_sales',
        }
        report_ref = report_map.get(self.report_type,
                                    'aviation_ticket_management.action_report_ticket_sales')
        return self.env.ref(report_ref).report_action(self)

    def action_view_records(self):
        self.ensure_one()
        domain = self._build_domain()
        if self.report_type == 'refunds':
            domain += [('is_refund', '=', True)]
        elif self.report_type == 'ticket_status':
            pass  # status already filtered

        return {
            'type': 'ir.actions.act_window',
            'name': _('Ticket Records'),
            'res_model': 'aviation.ticket',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {'search_default_group_by_%s' % self.group_by: 1},
        }
