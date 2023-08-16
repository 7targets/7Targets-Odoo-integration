{
    "name": "Seven Targets Integration",
    "version": "15.0.1.0.0",
    "summary": "Integrate Odoo with 7Targets to Automate Followups",
    "description": "Automate Followups using 7Targets & Odoo Integration",
    "category": "Sales",
    "author": "7Targets",
    "maintainer": "7Targets",
    "website": "www.7targets.ai",
    "license": "LGPL-3",
    "depends": ["crm","mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/auth.xml",
        "views/lead_connection_status.xml"
        "views/menu.xml",
        "views/lead.xml",
    ],
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": True,
    "auto_install": False,
}