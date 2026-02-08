# -*- coding: utf-8 -*-
from collections import defaultdict
import json
from odoo.http import request, Response
from odoo import fields, http

import logging

_logger = logging.getLogger(__name__)

class AchmitechHrRecruitment(http.Controller):
    @http.route(
    "/dossier/<string:token>",
    type="http",
    auth="public",
    website=True
    )
    def dossier_form(self, token, **kw):
        candidate = request.env["hr.candidate"].sudo().search(
            [("access_token", "=", token)],
            limit=1
        )
        if not candidate:
            return request.not_found()

        if candidate.dossier_state == "submitted":
            return request.render("achmitech_hr_recruitment.dossier_already")

        return request.render("achmitech_hr_recruitment.dossier_form", {
            "candidate": candidate
        })

    @http.route(
    "/dossier/submit",
    type="http",
    auth="public",
    website=True,
    methods=["POST"]
    )
    def dossier_submit(self, token=None, **post):
        candidate = request.env["hr.candidate"].sudo().search(
            [("access_token", "=", token)],
            limit=1
        )
        if not candidate:
            return request.not_found()

        _logger.info(
            "POST DATA:\n%s",
            json.dumps(post, indent=2, ensure_ascii=False, sort_keys=True)
        )
        grouped = defaultdict(dict)

        for k, v in post.items():
            if k.startswith("experiences_"):
                parts = k.split("_")
                exp_idx = parts[1]
                grouped[f"experience_{exp_idx}"][k] = v
            else:
                grouped["other"][k] = v

        _logger.info(
            "POST DATA (grouped):\n%s",
            json.dumps(grouped, indent=2, ensure_ascii=False)
        )
        return
        
    
    @http.route("/dossier/skills/search", type="json2", auth="public", csrf=False)
    def dossier_skills_search(self, **kwargs):
        payload = request.get_json_data() or {}

        q = (payload.get("q") or kwargs.get("q") or "").strip()
        limit = int(payload.get("limit") or kwargs.get("limit") or 40)

        # optional filters coming from JS
        scope = (payload.get("scope") or kwargs.get("scope") or "").strip()
        skill_type_id = payload.get("skill_type_id") or kwargs.get("skill_type_id")

        if not q:
            return []

        domain = [("name", "ilike", q)]

        # If you want to filter by skill type (recommended once you map categories)
        if skill_type_id:
            domain.append(("skill_type_id", "=", int(skill_type_id)))

        # Optional: if you want to exclude language skills from "logiciels" etc
        # You can implement your mapping based on scope here later.

        skills = request.env["hr.skill"].sudo().search_read(domain, ["name"], limit=limit)

        # Return in user's lang (important for French)
        lang = getattr(request, "lang", False) and request.lang.code or request.env.lang
        res = []
        for s in skills:
            rec = request.env["hr.skill"].sudo().browse(s["id"]).with_context(lang=lang)
            res.append({"id": s["id"], "name": rec.name})

        return res
    
    @http.route("/dossier/get-levels", type="http", auth="public", methods=['POST'], website=True, csrf=False)
    def dossier_get_levels(self, token=None, skill_id=None, **kw):
        candidate = request.env["hr.candidate"].sudo().search(
            [("access_token", "=", token)],
            limit=1
        )
        if not candidate:
            _logger.info("not candidate")
            return Response(
                json.dumps({"levels": []}),
                content_type='application/json'
            )

        if not skill_id:
            _logger.info("not skill_id")
            return Response(
                json.dumps({"levels": []}),
                content_type='application/json'
            )

        skill = request.env["hr.skill"].sudo().browse(int(skill_id))
        _logger.info("DDDDDDDDDDDDDDD %s", skill)
        if not skill.exists() or not skill.skill_type_id:
            return Response(
                json.dumps({"levels": []}),
                content_type='application/json'
            )

        levels = request.env["hr.skill.level"].with_context(lang="fr_FR").sudo().search(
            [("skill_type_id", "=", skill.skill_type_id.id)],
            order="id"
        )

        _logger.info("XXXXXXXXXXXXXXXXXXXXXXXXXXXXX %s", levels)

        return Response(
            json.dumps({"levels": [{"id": l.id, "name": l.name} for l in levels]}),
            content_type='application/json'
        )