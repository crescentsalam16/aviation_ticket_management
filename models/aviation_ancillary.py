# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AviationAncillary(models.Model):
    _name = 'aviation.ancillary'
    _description = 'Ancillary Revenue (Baggage, Cargo, Charter, etc.)'
    _order = 'ticket_id, service_type'

    ticket_id = fields.Many2one('aviation.ticket', string='Ticket',
                                 ondelete='cascade', required=True)
    service_type = fields.Selection([
        ('baggage', 'Excess Baggage'),
        ('cargo', 'Cargo'),
        ('mail', 'Mail / Parcel'),
        ('charter', 'Charter Flight'),
        ('seat', 'Seat Selection'),
        ('meal', 'Meal'),
        ('lounge', 'Lounge Access'),
        ('other', 'Other'),
    ], string='Service Type', required=True)
    description = fields.Char(string='Description', size=200)
    amount = fields.Float(string='Amount', digits=(15, 2))
    currency = fields.Char(string='Currency', size=5)
    pos_channel = fields.Selection([
        ('paystack', 'Paystack'),
        ('airvend', 'Airvend'),
        ('bank', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('agent', 'Agent'),
        ('other', 'Other'),
    ], string='Payment Channel')
    route = fields.Char(string='Route', size=50)
    weight_kg = fields.Float(string='Weight (kg)', digits=(10, 2))
    flight_no = fields.Char(string='Flight No', size=20)
    service_date = fields.Date(string='Service Date')
    notes = fields.Text(string='Notes')
