# -*- coding: utf-8 -*-
# from odoo import http


# class AchmitechOkr(http.Controller):
#     @http.route('/achmitech_okr/achmitech_okr', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/achmitech_okr/achmitech_okr/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('achmitech_okr.listing', {
#             'root': '/achmitech_okr/achmitech_okr',
#             'objects': http.request.env['achmitech_okr.achmitech_okr'].search([]),
#         })

#     @http.route('/achmitech_okr/achmitech_okr/objects/<model("achmitech_okr.achmitech_okr"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('achmitech_okr.object', {
#             'object': obj
#         })

