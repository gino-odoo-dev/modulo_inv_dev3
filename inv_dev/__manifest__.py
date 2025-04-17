{
    'name': 'Etiquetas ZPL',
    'version': '1.0',
    'summary': 'Modulo para generar etiquetas ZPL',
    'description': ' etiquetas ZPL.',
    'author': 'MarcoAG',
    'depends': ['product', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/inv_model_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'inv_dev/static/src/css/style.css',
        ],
    },
    'installable': True,
    'application': True,
}