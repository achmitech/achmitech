# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class OKRNode(models.Model):
    _name = "okr.node"
    _description = "OKR Node"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _parent_store = True
    _order = "id desc"

    name = fields.Char(string="Titre", required=True, tracking=True)
    description = fields.Text(string="Description")

    company_id = fields.Many2one("res.company",
        default=lambda self: self.env.company,
        required=True,
        index=True)
    
    user_id = fields.Many2one("res.users", "Utilisateur assigné", required=False)
    
    state = fields.Selection([("draft", "Brouillon"), ("confirmed", "Confirmé"), ("cancelled", "Annulé")],
                             string="Statut", default="draft", tracking=True)

    success_threshold = fields.Float(
        string="Seuil de réussite",
        default=lambda self: self.env.company.okr_success_points_threshold or 0.7,
        help="Progression minimale pour considérer ce nœud comme réussi (ex: 0.70 = 70%). "
             "Laissez vide pour utiliser le seuil de la société.",
    )

    result = fields.Selection(
        [("new", "Nouveau"), ("inprogress", "En Cours"), ("successful", "Réussi"), ("failed", "Échoué")],
        string="Result",
        compute="_compute_result",
        store=True,
        tracking=True,
    )

    year = fields.Integer(string="Year")
    quarter = fields.Selection([("0", "Q1"), ("1", "Q2"), ("2", "Q3"), ("3", "Q4")], string="Trimestre")

    parent_id = fields.Many2one("okr.node", string="Objetif Parent", ondelete="cascade", index=True)
    child_ids = fields.One2many("okr.node", "parent_id", string="Résultats Clés")
    parent_path = fields.Char(index=True)

    weight = fields.Float(string="Poids", default=1.0)

    # -------- Progression engine (clean) --------
    progress_source = fields.Selection([
        ("children", "À partir des Résultats Clés"),
        ("metric", "À partir d'un Indicateur"),
        ("manual", "Manuel"),
    ], default="children", required=True)

    progress_manual = fields.Float(string="Progression Manuel")

    metric_ids = fields.One2many("okr.node.metric", "node_id", string="Indicateurs")

    progress = fields.Float(string="Progression", compute="_compute_progress", store=True, recursive=True)

    # -------- Période engine (weekly/monthly/quarterly/custom) --------
    period_type = fields.Selection([
        ("none", "None"),
        ("week", "Hebdomadaire"),
        ("month", "Mensuel"),
        ("quarter", "Trimestriel"),
        ("custom", "Période Personnalisée"),
    ], string="Période", default="none", required=True)

    date_start = fields.Date(string="Date Début", compute="_compute_period_dates", store=True)
    date_end = fields.Date(string="Date Fin", compute="_compute_period_dates", store=True)

    custom_date_start = fields.Date(string="Date Début Personnalisée")
    custom_date_end = fields.Date(string="Date Fin Personnalisée")

    @api.onchange("progress_source")
    def _onchange_progress_source(self):
        if self.progress_source != "manual":
            self.progress_manual = 0.0
    
    @api.depends("period_type", "year", "quarter", "custom_date_start", "custom_date_end")
    def _compute_period_dates(self):
        """date_end is exclusive (recommended for domains: >= start and < end)."""
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.period_type == "none":
                rec.date_start = False
                rec.date_end = False

            elif rec.period_type == "week":
                # week starting Monday
                start = today - relativedelta(days=today.weekday())
                rec.date_start = start
                rec.date_end = start + relativedelta(days=7)

            elif rec.period_type == "month":
                start = today.replace(day=1)
                rec.date_start = start
                rec.date_end = start + relativedelta(months=1)

            elif rec.period_type == "quarter":
                # Use year + quarter if provided, else current quarter
                y = rec.year or today.year
                q = int(rec.quarter) if rec.quarter in ("0", "1", "2", "3") else ((today.month - 1) // 3)
                start_month = 1 + q * 3
                start = today.replace(year=y, month=start_month, day=1)
                rec.date_start = start
                rec.date_end = start + relativedelta(months=3)

            else:  # custom
                rec.date_start = rec.custom_date_start
                rec.date_end = rec.custom_date_end

    @api.depends(
        "child_ids.progress", "child_ids.weight",
        "progress_source", "progress_manual",
        "metric_ids.progress",
    )
    def _compute_progress(self):
        for rec in self:
            # 1) If has children => always rollup (OKR philosophy)
            if rec.child_ids:
                total_w = 0.0
                total = 0.0
                for ch in rec.child_ids:
                    w = ch.weight or 0.0
                    if w <= 0:
                        continue
                    total_w += w
                    total += (ch.progress or 0.0) * w
                rec.progress = round(total / total_w, 2) if total_w else 0.0
                continue

            # 2) Leaf nodes: metric/manual
            if rec.progress_source == "metric":
                # if multiple metrics, take average (or we can add weights later)
                lines = rec.metric_ids
                if lines:
                    rec.progress = round(sum(lines.mapped("progress")) / len(lines), 2)
                else:
                    rec.progress = 0.0
                continue

            if rec.progress_source == "manual":
                rec.progress = max(0.0, min(100.0, rec.progress_manual or 0.0))
                continue

            # leaf + children mode (no children) => 0
            rec.progress = 0.0

    @api.depends("progress", "date_end", "state", "success_threshold", "company_id.okr_success_points_threshold")
    def _compute_result(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.state == "cancelled":
                rec.result = "failed"
                continue
            p = rec.progress or 0.0
            t = rec.success_threshold or rec.company_id.okr_success_points_threshold or 1.0
            threshold = t * 100.0
            expired = bool(rec.date_end and rec.date_end < today)
            if p >= threshold:
                rec.result = "successful"
            elif expired:
                rec.result = "failed"
            elif p > 0.0:
                rec.result = "inprogress"
            else:
                rec.result = "new"

    # buttons
    def action_recompute_metrics(self):
        self.mapped("metric_ids")._compute_current()
        self.invalidate_recordset(["progress"])

    # constraints (keep your cycle guard)
    @api.constrains("parent_id")
    def _check_no_cycles(self):
        for rec in self:
            if not rec.parent_id:
                continue
            seen = set()
            cur = rec.parent_id
            while cur:
                if cur.id == rec.id:
                    raise ValidationError("Cycle detected: a node cannot be its own ancestor.")
                if cur.id in seen:
                    break
                seen.add(cur.id)
                cur = cur.parent_id
                
    def action_set_to_draft(self):
        self.state = 'draft'

    def button_confirm(self):
        self.state = 'confirmed'
        self.child_ids.filtered(lambda c: c.state == 'draft').button_confirm()

    def button_cancel(self):
        self.state = 'cancelled'