# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import fields
import logging
_logger = logging.getLogger(__name__)

# Registry: code -> function(env, node) -> float
KPI_REGISTRY = {}


def kpi(code):
    def _decorator(fn):
        KPI_REGISTRY[code] = fn
        return fn
    return _decorator



@kpi("recruitment.need_covered_under_5d_rate")
def kpi_need_covered_under_5d_rate(env, node):
    if not node.date_start or not node.date_end or not node.user_id:
        return 0.0

    Need = env["staffing.need"].sudo()

    need_domain = [
        ("company_id", "=", node.company_id.id),
        ("assigned_to", "=", node.user_id.id),
        ("assigned_date", ">=", node.date_start),
        ("assigned_date", "<", node.date_end),  # end exclusive
        ("state", "!=", "draft"),
    ]

    needs = Need.search(need_domain)

    total_positions = 0
    covered_positions = 0

    for need in needs:
        required = int(need.number_of_positions or 0)
        if required <= 0 or not need.assigned_date:
            continue

        total_positions += required

        assigned_dt = fields.Datetime.to_datetime(need.assigned_date)
        deadline_date = (assigned_dt + timedelta(days=5)).date()

        apps = need.applicant_ids

        # primary: applicant responsible
        apps_scoped = apps.filtered(lambda a: a.user_id and a.user_id.id == node.user_id.id)

        # fallback: if user_id not set, consider all applicants of the need (or keep empty)
        if not apps_scoped:
            apps_scoped = apps

        # count how many were presented within 5 days
        presented_within_5d = 0
        for d in apps_scoped.mapped("presented_to_client_date"):
            if not d:
                continue
            # normalize to date
            dd = fields.Date.from_string(d) if isinstance(d, str) else (d.date() if hasattr(d, "date") else d)
            if dd and dd <= deadline_date:
                presented_within_5d += 1

        covered_positions += min(required, presented_within_5d)

    return (covered_positions / total_positions) if total_positions else 0.0


@kpi("recruitment.ec_pass_rate")
def kpi_ec_pass_rate(env, node):
    if not node.date_start or not node.date_end or not node.user_id:
        return 0.0

    Applicant = env["hr.applicant"].sudo()

    base_domain = [
        ("company_id", "=", node.company_id.id),
        ("staffing_need_id", "!=", False),
        ("staffing_need_id.assigned_to", "=", node.user_id.id),
        ("presented_to_client_date", ">=", node.date_start),
        ("presented_to_client_date", "<", node.date_end),
    ]

    applicants = Applicant.search(base_domain)
    denom = len(applicants)
    if not denom:
        return 0.0

    num = len(applicants.filtered(lambda a: a.client_interview_status == "passed"))
    return num / denom



@kpi("recruitment.nok_treated_period_rate")
def kpi_nok_treated_period_rate(env, node):
    """
    KR: 100% des retours candidats NOK traités durant la période.

    Denominator: Applicants refused during the node period (active=False, refuse_reason_id set).
    Numerator:   Among them, those where retour_done = True.

    Governance rule: if no NOK in period → returns 1.0 (nothing to treat = achieved).
    """
    if not node.date_start or not node.date_end or not node.user_id or not node.company_id:
        return 0.0

    Applicant = env["hr.applicant"].sudo()

    base_domain = [
        ("company_id", "=", node.company_id.id),
        ("user_id", "=", node.user_id.id),
        ("active", "=", False),
        ("refuse_reason_id", "!=", False),
        ("refuse_date", ">=", node.date_start),
        ("refuse_date", "<=", node.date_end),
    ]

    denom = Applicant.search_count(base_domain)
    if not denom:
        return 1.0

    num = Applicant.search_count(base_domain + [("retour_done", "=", True)])
    return num / denom

@kpi("recruitment.pool_active_count")
def kpi_pool_active_count(env, node):
    """
    KR: Maintenir un vivier actif de N profils.

    Snapshot of the recruiter's TOTAL active pool at any point in time.
    Use target = minimum floor (e.g. 100). Once the recruiter maintains
    at least 100 pool members, this KR stays successful.

    Do NOT add a date filter — the goal is to maintain a standing pool,
    not to accumulate N additions per period.
    """
    if not node.user_id:
        return 0.0

    pool_domain = [
        ('talent_pool_ids', '!=', False),
        ("user_id", "=", node.user_id.id),
    ]
    if node.company_id:
        pool_domain.append(("company_id", "=", node.company_id.id))

    return float(env["hr.applicant"].sudo().search_count(pool_domain))


@kpi("recruitment.pool_recontacted_rate")
def kpi_pool_recontacted_rate(env, node):
    """
    KR: Recontacter N% du vivier par période.

    Returns recontacted / pool_size (0.0 → 1.0).
    Both numerator and denominator are scoped to the recruiter (node.user_id)
    so that each recruiter is measured against their own pool.
    """
    if not node.date_start or not node.date_end or not node.user_id:
        return 0.0

    pool_domain = [
        ("talent_pool_ids", "!=", False),
        ("user_id", "=", node.user_id.id),
    ]
    if node.company_id:
        pool_domain.append(("company_id", "=", node.company_id.id))

    pool_size = env["hr.applicant"].sudo().search_count(pool_domain)
    if not pool_size:
        return 0.0

    log_domain = [
        ("date", ">=", node.date_start),
        ("date", "<", node.date_end),
        ("applicant_id.talent_pool_ids", "!=", False),
        ("applicant_id.user_id", "=", node.user_id.id),
        ("user_id", "=", node.user_id.id),
    ]

    logs = env["okr.recontact.log"].sudo().search(log_domain)
    recontacted = len(logs.mapped("applicant_id"))

    return recontacted / pool_size


@kpi("recruitment.hires_count")
def kpi_hires_count(env, node):
    """
    KR: N nouveaux consultants démarrés par période.

    Counts ALL applicants who reached the hired stage (stage_id.hired_stage=True)
    within the node period, scoped to the recruiter. No seniority filter —
    "En stage" vs "Confirmé+" refers to the RECRUITER's own experience level,
    not the job position being filled. Set the target on the metric record:

      - En stage recruiter     → target = 2/month  (1 every 2 weeks)
      - Confirmé+ recruiter    → target = 4/month  (1 per week)
    """
    if not node.user_id or not node.date_start or not node.date_end:
        return 0.0

    domain = [
        ("user_id", "=", node.user_id.id),
        ("stage_id.hired_stage", "=", True),
        ("date_closed", ">=", node.date_start),
        ("date_closed", "<", node.date_end),
        ("active", "=", True),
    ]
    if node.company_id:
        domain.append(("company_id", "=", node.company_id.id))

    return float(env["hr.applicant"].sudo().search_count(domain))
