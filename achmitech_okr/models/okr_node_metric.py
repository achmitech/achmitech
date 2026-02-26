# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import MissingError

import logging

from odoo.addons.achmitech_okr.models.okr_kpi_provider import KPI_REGISTRY

_logger = logging.getLogger(__name__)


class OkrNodeMetric(models.Model):
    _name = "okr.node.metric"
    _description = "OKR Node Metric"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    node_id = fields.Many2one("okr.node", required=True, ondelete="cascade")
    definition_id = fields.Many2one("okr.metric.definition", required=True, ondelete="cascade")

    target = fields.Float(required=True)

    current = fields.Float(compute="_compute_current", store=True, readonly=True)
    progress = fields.Float(compute="_compute_current", store=True, readonly=True)


    def _build_eval_ctx(self):
        self.ensure_one()
        n = self.node_id
        return {
            "uid": self.env.uid,
            "user": self.env.user,
            "env": self.env,
            "context": dict(self.env.context or {}),
            # node identity
            "node_id": n.id,
            "okr_user_id": n.user_id.id if n.user_id else False,
            # scope helpers (for domains)
            "company_id": n.company_id.id if n.company_id else False,
            # period helpers
            "date_start": n.date_start,
            "date_end": n.date_end,
        }

    @api.depends(
    "definition_id", "definition_id.domain", "definition_id.aggregation", "definition_id.value_field_id",
    "definition_id.definition_type", "definition_id.predefined_kpi",
    "target",
    "node_id.company_id", "node_id.date_start", "node_id.date_end", "node_id.user_id",
    )
    def _compute_current(self):
        for line in self:
            current = 0.0

            d = line.definition_id
            if not d:
                line.current = 0.0
                line.progress = 0.0
                continue

            eval_ctx = line._build_eval_ctx()
            node = line.node_id
            env = line.env

            try:
                if d.definition_type == "predefined":
                    fn = KPI_REGISTRY.get(d.predefined_kpi)
                    if not fn:
                        raise ValueError(f"Unknown predefined KPI: {d.predefined_kpi}")

                    current = float(fn(env, node))
                    _logger.error("KPI returned current=%s for line=%s", current, line.id)

                elif d.definition_type == "code":
                    current = 0.0

                else:
                    # DOMAIN branch ONLY
                    if not d.model_name:
                        current = 0.0
                    else:
                        Model = env[d.model_name].sudo()
                        domain = d._safe_domain_eval(d.domain, eval_ctx)

                        # (optional) owner scope ONLY if model supports it
                        okr_uid = eval_ctx.get("okr_user_id")
                        if okr_uid and "assigned_to" in Model._fields:
                            domain = fields.Domain.AND([domain, [("assigned_to", "=", okr_uid)]])

                        if d.aggregation == "count":
                            current = float(Model.search_count(domain))
                        else:
                            field = d.value_field_id.name
                            agg = f"{field}:sum"
                            res = Model._read_group(domain, aggregates=[agg])
                            current = float(res[0][0]) if res and res[0] and res[0][0] is not None else 0.0

            except Exception:
                _logger.exception("OKR metric compute failed: node=%s, line=%s, def=%s", node.id, line.id, d.name)
                current = 0.0

            target = line.target or 0.0
            progress = (current / target * 100.0) if target > 0 else 0.0
            progress = max(0.0, progress)

            _logger.error(
                "FINAL current for line=%s def=%s => current=%s target=%s progress=%s",
                line.id, d.name, current, target, progress
            )

            line.current = round(current, 4)
            line.progress = round(progress, 2)