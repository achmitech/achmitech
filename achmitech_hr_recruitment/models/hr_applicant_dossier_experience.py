# -*- coding: utf-8 -*-
from odoo import fields, models

class HrApplicantDossierExperience(models.Model):
    _name = "hr.applicant.dossier.experience"
    _description = "Dossier - Expérience"
    _order = "sequence, id"

    applicant_id = fields.Many2one(
        "hr.applicant",
        string="Candidature",
        required=True,
        ondelete="cascade",
        index=True,
    )

    sequence = fields.Integer(default=10)
    name = fields.Char(string="Projet")
    company = fields.Char(string="Entreprise / Client")
    poste = fields.Char(string="Poste occupé")
    role = fields.Char(string="Rôle")

    start = fields.Date(string="Date début")
    end = fields.Date(string="Date fin")

    contexte = fields.Html(string="Contexte général", sanitize=True)
    sujet = fields.Html(string="Sujet du projet", sanitize=True)
    responsabilites = fields.Html(string="Responsabilités occupées", sanitize=True)
    travail = fields.Html(string="Travail réalisé", sanitize=True)
    resultats = fields.Html(string="Résultats obtenus", sanitize=True)

    competency_line_ids = fields.One2many(
        "hr.applicant.dossier.competency",
        "experience_id",
        string="Compétences",
        copy=False,
    )
