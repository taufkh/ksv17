from odoo import http
from odoo.http import request


class ErpConsultantWebsite(http.Controller):

    # ──────────────────────────────────────────────
    # Home page
    # ──────────────────────────────────────────────
    @http.route('/home', type='http', auth='public', website=True)
    def home(self, **kwargs):
        services = [
            {
                'icon': 'fa-cogs',
                'title': 'Odoo Implementation',
                'description': (
                    'End-to-end Odoo deployment tailored to your business processes. '
                    'From requirements gathering to go-live, we handle it all.'
                ),
                'url': '/services#implementation',
            },
            {
                'icon': 'fa-code',
                'title': 'Odoo Customization',
                'description': (
                    'Custom modules, integrations, and workflow automation built '
                    'specifically for your unique business needs.'
                ),
                'url': '/services#customization',
            },
            {
                'icon': 'fa-graduation-cap',
                'title': 'ERP Training',
                'description': (
                    'Hands-on training programs that get your team confident '
                    'and productive in Odoo quickly.'
                ),
                'url': '/services#training',
            },
            {
                'icon': 'fa-life-ring',
                'title': 'Support & Maintenance',
                'description': (
                    'Reliable post-go-live support, upgrades, and ongoing '
                    'maintenance so your system always runs at its best.'
                ),
                'url': '/services#support',
            },
        ]
        return request.render('website_erp_consultant.page_home', {
            'services': services,
        })

    # ──────────────────────────────────────────────
    # Services page
    # ──────────────────────────────────────────────
    @http.route('/services', type='http', auth='public', website=True)
    def services(self, **kwargs):
        services = [
            {
                'id': 'implementation',
                'icon': 'fa-cogs',
                'title': 'Odoo Implementation',
                'description': (
                    'We guide you through every phase of your Odoo journey — '
                    'from discovery and gap analysis to data migration, configuration, '
                    'and go-live. Our structured methodology minimises risk and '
                    'maximises adoption across your team.'
                ),
                'features': [
                    'Business process analysis & gap mapping',
                    'System configuration & master data setup',
                    'Data migration from legacy systems',
                    'User acceptance testing (UAT)',
                    'Go-live support & hypercare',
                ],
            },
            {
                'id': 'customization',
                'icon': 'fa-code',
                'title': 'Odoo Customization',
                'description': (
                    'Off-the-shelf ERP rarely fits perfectly. We build custom modules, '
                    'extend existing ones, and integrate third-party systems so Odoo '
                    'works exactly the way your business does.'
                ),
                'features': [
                    'Custom module development',
                    'Workflow automation & approval flows',
                    'Third-party API integrations',
                    'Custom QWeb reports & dashboards',
                    'Performance optimisation',
                ],
            },
            {
                'id': 'training',
                'icon': 'fa-graduation-cap',
                'title': 'ERP Training',
                'description': (
                    'A great ERP system is only as good as the people using it. '
                    'Our role-based training programs get every team member — from '
                    'warehouse staff to senior management — confident and productive fast.'
                ),
                'features': [
                    'Role-based training sessions',
                    'Hands-on workshop exercises',
                    'Training manuals & video guides',
                    'Admin & super-user training',
                    'Refresher sessions post go-live',
                ],
            },
            {
                'id': 'support',
                'icon': 'fa-life-ring',
                'title': 'Support & Maintenance',
                'description': (
                    'Your ERP needs to evolve as your business grows. We provide '
                    'responsive helpdesk support, version upgrades, bug fixes, and '
                    'proactive monitoring to keep your system healthy.'
                ),
                'features': [
                    'Helpdesk ticketing & SLA-backed response',
                    'Odoo version upgrades',
                    'Bug fixes & patches',
                    'Server & performance monitoring',
                    'Monthly health-check reports',
                ],
            },
        ]
        return request.render('website_erp_consultant.page_services', {
            'services': services,
        })

    # ──────────────────────────────────────────────
    # About page
    # ──────────────────────────────────────────────
    @http.route('/about', type='http', auth='public', website=True)
    def about(self, **kwargs):
        values = [
            {
                'icon': 'fa-handshake-o',
                'title': 'Client-First',
                'description': 'Every decision we make is guided by what is best for our clients.',
            },
            {
                'icon': 'fa-shield',
                'title': 'Integrity',
                'description': 'Transparent pricing, honest timelines, and no hidden surprises.',
            },
            {
                'icon': 'fa-lightbulb-o',
                'title': 'Innovation',
                'description': 'We stay current with Odoo releases and best practices.',
            },
            {
                'icon': 'fa-users',
                'title': 'Partnership',
                'description': 'We become an extension of your team, not just a vendor.',
            },
        ]
        return request.render('website_erp_consultant.page_about', {
            'values': values,
        })

    # ──────────────────────────────────────────────
    # Contact page (GET)
    # ──────────────────────────────────────────────
    @http.route('/contact-us', type='http', auth='public', website=True)
    def contact(self, **kwargs):
        success = kwargs.get('success', False)
        error = kwargs.get('error', False)
        return request.render('website_erp_consultant.page_contact', {
            'success': success,
            'error': error,
        })

    # ──────────────────────────────────────────────
    # Contact form submission (POST → CRM lead)
    # ──────────────────────────────────────────────
    @http.route('/contact-us/submit', type='http', auth='public',
                methods=['POST'], website=True, csrf=True)
    def contact_submit(self, name='', email='', phone='',
                       company='', service='', message='', **kwargs):
        # Basic validation
        if not name.strip() or not email.strip():
            return request.redirect('/contact-us?error=missing_fields')

        # Map service label to a lead description prefix
        service_labels = {
            'implementation': 'Odoo Implementation',
            'customization': 'Odoo Customization',
            'training': 'ERP Training',
            'support': 'Support & Maintenance',
            'general': 'General Enquiry',
        }
        service_label = service_labels.get(service, 'General Enquiry')

        # Build description
        description_parts = []
        if company:
            description_parts.append(f'Company: {company}')
        if service_label:
            description_parts.append(f'Service of interest: {service_label}')
        if message:
            description_parts.append(f'\nMessage:\n{message}')
        description = '\n'.join(description_parts)

        # Create CRM lead — sudo() is required because the visitor is public
        request.env['crm.lead'].sudo().create({
            'name': f'[Website] {service_label} enquiry from {name}',
            'contact_name': name,
            'email_from': email,
            'phone': phone or False,
            'partner_name': company or False,
            'description': description,
            'type': 'lead',
        })

        return request.redirect('/contact-us?success=1')
