# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AviationSyncLog(models.Model):
    _name = 'aviation.sync.log'
    _description = 'Aviation Sync Log'
    _order = 'start_time desc'

    config_id = fields.Many2one('aviation.sync.config', string='Sync Config',
                                 ondelete='cascade')
    start_time = fields.Datetime(string='Started At')
    end_time = fields.Datetime(string='Ended At')
    duration = fields.Float(string='Duration (s)', compute='_compute_duration')
    status = fields.Selection([
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], string='Status', default='running')
    records_created = fields.Integer(string='Created')
    records_updated = fields.Integer(string='Updated')
    records_failed = fields.Integer(string='Errors')
    message = fields.Text(string='Message / Error')

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for rec in self:
            if rec.start_time and rec.end_time:
                delta = rec.end_time - rec.start_time
                rec.duration = delta.total_seconds()
            else:
                rec.duration = 0.0
