# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AviationRefundWizard(models.TransientModel):
    _name = 'aviation.refund.wizard'
    _description = 'Process Ticket Refund'

    ticket_id = fields.Many2one('aviation.ticket', string='Ticket',
                                 required=True, ondelete='cascade')
    ticket_no = fields.Char(related='ticket_id.ticket_no', string='Ticket No')
    face_value = fields.Float(related='ticket_id.face_value', string='Face Value')
    refund_amount = fields.Float(string='Refund Amount', required=True, digits=(15, 2))
    refund_date = fields.Date(string='Refund Date', required=True,
                               default=fields.Date.today)
    refund_channel = fields.Selection([
        ('paystack', 'Paystack'),
        ('airvend', 'Airvend'),
        ('bank', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('agent', 'Through Agent'),
        ('other', 'Other'),
    ], string='Refund Channel', required=True)
    reason = fields.Text(string='Reason for Refund', required=True)
    penalty_amount = fields.Float(string='Cancellation Penalty', digits=(15, 2))
    net_refund = fields.Float(string='Net Refund Amount',
                               compute='_compute_net_refund', digits=(15, 2))

    @api.depends('refund_amount', 'penalty_amount')
    def _compute_net_refund(self):
        for rec in self:
            rec.net_refund = rec.refund_amount - rec.penalty_amount

    def action_confirm_refund(self):
        self.ensure_one()
        if self.refund_amount > self.face_value:
            raise ValidationError(
                _('Refund amount cannot exceed the face value of the ticket.'))
        self.ticket_id.write({
            'status': 'refunded',
            'is_refund': True,
            'refund_date': self.refund_date,
            'refund_amount': self.net_refund,
            'refund_channel': self.refund_channel,
            'refund_reason': self.reason,
        })
        self.ticket_id.message_post(
            body=_('Refund processed: %s %s via %s. Reason: %s') % (
                self.ticket_id.fare_curr, self.net_refund,
                dict(self._fields['refund_channel'].selection).get(
                    self.refund_channel),
                self.reason
            )
        )
        return {'type': 'ir.actions.act_window_close'}


class AviationReissueWizard(models.TransientModel):
    _name = 'aviation.reissue.wizard'
    _description = 'Reissue Ticket'

    original_ticket_id = fields.Many2one('aviation.ticket',
                                          string='Original Ticket',
                                          required=True)
    new_ticket_no = fields.Char(string='New Ticket Number', required=True)
    new_flight_no = fields.Char(string='New Flight Number')
    new_flight_date = fields.Char(string='New Flight Date')
    new_route = fields.Char(string='New Route', size=20)
    reissue_date = fields.Date(string='Reissue Date', default=fields.Date.today)
    fare_difference = fields.Float(string='Fare Difference', digits=(15, 2))
    reason = fields.Text(string='Reason for Reissue')

    def action_confirm_reissue(self):
        self.ensure_one()
        original = self.original_ticket_id
        # Mark original as reissued
        original.write({'status': 'reissued', 'is_reissue': True})

        # Create new ticket record
        vals = {
            'ticket_no': self.new_ticket_no,
            'passenger_name': original.passenger_name,
            'rloc': original.rloc,
            'ticket_class': original.ticket_class,
            'fare_basis': original.fare_basis,
            'flight_no': self.new_flight_no or original.flight_no,
            'flight_date': self.new_flight_date or original.flight_date,
            'route': self.new_route or original.route,
            'fare_curr': original.fare_curr,
            'face_value': original.face_value + self.fare_difference,
            'pos_channel': original.pos_channel,
            'sale_type': original.sale_type,
            'status': 'unutilised',
            'is_reissue': True,
            'original_ticket_id': original.id,
            'refund_date': self.reissue_date,
            'refund_reason': self.reason,
            'issue_agent_id': original.issue_agent_id,
            'issue_office': original.issue_office,
        }
        new_ticket = self.env['aviation.ticket'].create(vals)
        original.message_post(
            body=_('Reissued as ticket %s') % self.new_ticket_no
        )
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'aviation.ticket',
            'res_id': new_ticket.id,
            'view_mode': 'form',
        }
