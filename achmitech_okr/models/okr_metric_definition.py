# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class OkrMetricDefinition(models.Model):
    _name = "okr.metric.definition"
    _description = "Définition d'Indicateur OKR (Generic)"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    definition_type = fields.Selection([
        ("domain", "Domain (Generic)"),
        ("predefined", "Predefined KPI"),
        ("code", "Custom Python Code"),
    ], default="domain", required=True)
    
    predefined_kpi = fields.Selection([
        ("recruitment.need_covered_under_5d_rate", "Besoins couverts sous 5 jours (%)"),
        ("recruitment.ec_pass_rate", "Taux EC terminé / présentés (%)"),
        ("recruitment.nok_treated_period_rate", "NOK traités durant la période (%)"),
        ("recruitment.pool_recontacted_rate", "Taux recontact vivier (%)"),
        ("recruitment.pool_active_count", "Vivier actif — snapshot total (nb profils)"),
        ("recruitment.hires_count", "Consultants démarrés (nb)"),
    ], string="Predefined KPI")

    python_code = fields.Text("Python Code")

    model_id = fields.Many2one("ir.model", string="Modèle", ondelete="cascade")
    model_name = fields.Char(string="Nom technique du modèle", related="model_id.model", store=True, readonly=True)

    # Domaines stored as strings, ex: "[('stage_id','=', 3)]"
    domain = fields.Char("Domaine")

    # For SUM aggregation: choose numeric field from the selected model
    value_field_id = fields.Many2one(
        "ir.model.fields",
        string="Value Field",
        domain="[('model_id','=',model_id), ('ttype','in',('integer','float','monetary'))]",
        ondelete="cascade",
    )

    aggregation = fields.Selection([
        ("count", "Count"),
        ("sum", "Sum"),
    ], default="count")

    @api.constrains("aggregation", "value_field_id", "definition_type")
    def _check_value_field(self):
        for rec in self:
            if rec.definition_type != "domain":
                continue
            if rec.aggregation == "sum" and not rec.value_field_id:
                raise ValueError("Value Field is required when aggregation is Sum.")
            
    def _safe_domain_eval(self, domain_str, eval_ctx=None):
        """Evaluate a domain string safely."""
        domain_str = (domain_str or "").strip() or "[]"
        ctx = dict(eval_ctx or {})
        try:
            dom = safe_eval(domain_str, ctx)
        except Exception:
            dom = []
        return dom if isinstance(dom, (list, tuple)) else []
