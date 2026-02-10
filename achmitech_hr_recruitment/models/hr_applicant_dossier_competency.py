# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

class HrApplicantDossierCompetency(models.Model):
    _name = "hr.applicant.dossier.competency"
    _description = "Dossier - Compétence"
    _order = "experience_id, sequence, id"

    experience_id = fields.Many2one(
        "hr.applicant.dossier.experience",
        string="Expérience",
        required=True,
        ondelete="cascade",
        index=True,
    )

    applicant_id = fields.Many2one(
        related="experience_id.applicant_id",
        store=True,
        index=True,
        readonly=True,
    )

    sequence = fields.Integer(default=10)

    # Section/category in your UI (Logiciels, Langues, Méthodes, etc.)
    skill_type_id = fields.Many2one(
        "hr.skill.type",
        string="Type de compétence",
        required=True,
        index=True,
    )

    skill_id = fields.Many2one(
        "hr.skill",
        string="Compétence",
        required=True,
        index=True,
    )

    skill_level_id = fields.Many2one(
        "hr.skill.level",
        string="Niveau",
        index=True,
    )

    @api.constrains("skill_id", "skill_type_id")
    def _check_skill_matches_type(self):
        for rec in self:
            if rec.skill_id and rec.skill_type_id:
                # Standard HR skills: hr.skill has skill_type_id
                if rec.skill_id.skill_type_id != rec.skill_type_id:
                    raise ValidationError(
                        "La compétence choisie ne correspond pas au type sélectionné."
                    )

    @api.constrains("skill_level_id", "skill_type_id")
    def _check_level_matches_type(self):
        for rec in self:
            if rec.skill_level_id and rec.skill_type_id:
                # Standard: hr.skill.type has skill_level_ids
                if rec.skill_level_id not in rec.skill_type_id.skill_level_ids:
                    raise ValidationError(
                        "Le niveau choisi n'est pas valide pour ce type de compétence."
                    )
