# -*- coding: utf-8 -*-
{
    'name': 'Aviation Ticket Management',
    'version': '17.0.1.0.0',
    'category': 'Aviation/Transport',
    'summary': 'Airline ticket sales, revenue tracking, commissions, refunds, and regulatory reporting',
    'description': """
        Aviation Ticket Management System for Odoo 17

        Features:
        - Ticket sales tracking (Direct & Indirect via Paystack, Airvend, GDS, Agents)
        - Point-of-Sale identification (Paystack, Airvend, Bank, Cash, Agents)
        - Ancillary revenue: Baggage fees, Cargo, Mail/Parcel, Charter
        - Agency commission tracking (gross vs net, automated calculations)
        - Refunds & Reissues workflow
        - Tax & regulatory fee mapping (PSC, VAT, aviation levies)
        - Flown, Unutilised, and Expired ticket tracking
        - Sync from external integration service
        - Comprehensive revenue reporting
    """,
    'author': 'Aviation IT',
    'depends': ['base', 'mail', 'account'],
    'data': [
        # security
        'security/aviation_security.xml',
        'security/ir.model.access.csv',

        # data
        'data/aviation_data.xml',

        # core views
        'views/ticket_views.xml',
        'views/sync_views.xml',

        # reports + dashboards
        'views/report_views.xml',

        # wizards (THIS defines your action)
        'wizards/report_wizard_views.xml',

        # reports (QWeb, etc.)
        'reports/ticket_sales_report.xml',
        'reports/commission_report.xml',
        'reports/refund_report.xml',
        'reports/tax_report.xml',
        'reports/ticket_status_report.xml',

        # MENUS
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'images': ['static/description/icon.png'],
}
