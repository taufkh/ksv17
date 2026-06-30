{
    "name": "TH Consulting Document Attachment",
    "summary": "Image attachments for quotations and invoices",
    "version": "17.0.1.0.0",
    "category": "Sales/Accounting",
    "author": "Codex",
    "license": "LGPL-3",
    "depends": ["sale_management", "account"],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
        "report/document_attachment_report.xml",
    ],
    "installable": True,
    "application": False,
}
