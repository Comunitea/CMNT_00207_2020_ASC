# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Asterisk Phonecall Info",
    "version": "12.0.1.0.0",
    "summary": "",
    "category": "custom",
    "author": "Comunitea",
    "maintainer": "Comunitea",
    "website": "www.comunitea.com",
    "license": "AGPL-3",
    "depends": [
        "base_phone",
        "crm_phone",
        "crm_phonecall_planner",
        "crm_phonecall",
        "asterisk_click2dial",
        "base_phone_popup",
    ],
    "data": [
        'views/crm_phonecall_view.xml',
        'views/assets.xml',
        'wizard/phonecall_notes_wzd.xml',
        'data/cdr_import_cron.xml',
    ],
    'qweb': ['static/src/xml/note.xml'],
}
