# -*- coding: utf-8 -*-
# from odoo import http


# class AchmitechHrRecruitment(http.Controller):
#     @http.route('/achmitech_hr_recruitment/achmitech_hr_recruitment', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/achmitech_hr_recruitment/achmitech_hr_recruitment/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('achmitech_hr_recruitment.listing', {
#             'root': '/achmitech_hr_recruitment/achmitech_hr_recruitment',
#             'objects': http.request.env['achmitech_hr_recruitment.achmitech_hr_recruitment'].search([]),
#         })

#     @http.route('/achmitech_hr_recruitment/achmitech_hr_recruitment/objects/<model("achmitech_hr_recruitment.achmitech_hr_recruitment"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('achmitech_hr_recruitment.object', {
#             'object': obj
#         })

