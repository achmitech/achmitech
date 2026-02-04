# -*- coding: utf-8 -*-
from odoo import api, fields, models


class OkrNode(models.Model):
    _name = "okr.node"
    _description = "OKR Node"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _parent_name = "parent_id"
    _parent_store = True
    _order = "year desc, quarter asc, id desc"

    # Core
    name = fields.Char(string="Title", required=True, tracking=True)
    description = fields.Text(string="Description")
    active = fields.Boolean(default=True)

    okr_success_points_threshold = fields.Float(
        string="OKR success point threshold",
        default=lambda self: float(
            self.env["ir.config_parameter"].sudo().get_param(
                "achmitech_okr.okr_success_points_threshold", "0.70"
            )
        ),
    )
    # Hierarchy: Objective (parent) -> Key Results (children)
    parent_id = fields.Many2one(
        "okr.node",
        string="Objective",
        ondelete="restrict",
        index=True,
    )
    child_ids = fields.One2many(
        "okr.node",
        "parent_id",
        string="Key Results",
    )
    parent_path = fields.Char(index=True)

    # (Optional) a convenience Many2many. In real life you'd compute descendants.
    recursive_child_ids = fields.Many2many(
        "okr.node",
        "okr_node_recursive_rel",
        "parent_id",
        "child_id",
        string="Recursive Children",
        compute="_compute_recursive_child_ids",
        store=False,
    )

    key_results_count = fields.Integer(
        string="Key Results Count",
        compute="_compute_key_results_count",
        store=False,
    )

    # Target / assignment
    mode = fields.Selection(
        [
            ("company", "Company"),
            ("department", "Department"),
            ("employee", "Employee"),
        ],
        string="Target",
        default="company",
        tracking=True,
    )

    company_id = fields.Many2one("res.company", string="Company", ondelete="set null")
    department_id = fields.Many2one("hr.department", string="Department", ondelete="set null")
    employee_id = fields.Many2one("hr.employee", string="Employee", ondelete="set null")

    user_id = fields.Many2one("res.users", string="User", ondelete="set null")
    owner = fields.Char(string="Owner")

    # Time framing
    year = fields.Char(string="Year")
    quarter = fields.Selection(
        [("0", "Q1"), ("1", "Q2"), ("2", "Q3"), ("3", "Q4")],
        string="Quarter",
    )
    quarter_full_name = fields.Char(string="Quarter Full Name", compute="_compute_quarter_full_name", store=False)
    time_frame = fields.Char(string="Time Frame")

    # OKR classification
    type = fields.Selection(
        [("committed", "Committed"), ("aspirational", "Aspirational")],
        string="Type",
        tracking=True,
    )
    weight = fields.Float(string="Weight")
    points = fields.Float(string="Points")
    progress = fields.Float(string="Progress", tracking=True)
    okr_success_points_threshold = fields.Float(string="OKR success point threshold")

    # Status/result
    state = fields.Selection(
        [("draft", "Draft"), ("confirmed", "Confirmed"), ("cancelled", "Cancelled")],
        string="Status",
        default="draft",
        tracking=True,
    )
    result = fields.Selection(
        [("new", "New"), ("inprogress", "In Progress"), ("successful", "Successful"), ("failed", "Failed")],
        string="Result",
        default="new",
        tracking=True,
    )

    # UI / access flag (as in your model list)
    allow_access_hierarchy_node = fields.Boolean(string="Allow Access To Hierarchy Node")

    # Avatars (in your PDF)
    user_avatar_1024 = fields.Binary(string="Avatar 1024", related="user_id.image_1024", readonly=True)
    user_avatar_128 = fields.Binary(string="Avatar 128", related="user_id.image_128", readonly=True)

    @api.depends("child_ids")
    def _compute_key_results_count(self):
        for rec in self:
            rec.key_results_count = len(rec.child_ids)

    @api.depends("quarter", "year")
    def _compute_quarter_full_name(self):
        mapping = {"0": "Q1", "1": "Q2", "2": "Q3", "3": "Q4"}
        for rec in self:
            q = mapping.get(rec.quarter) if rec.quarter else ""
            y = rec.year or ""
            rec.quarter_full_name = f"{q} {y}".strip()

    def _compute_recursive_child_ids(self):
        # Simple DFS (non-stored). Good enough for UI helpers.
        for rec in self:
            seen = set()
            stack = list(rec.child_ids)
            while stack:
                node = stack.pop()
                if node.id in seen:
                    continue
                seen.add(node.id)
                stack.extend(node.child_ids)
            rec.recursive_child_ids = [(6, 0, list(seen))]
