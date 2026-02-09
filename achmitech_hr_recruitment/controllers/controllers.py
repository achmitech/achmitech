# -*- coding: utf-8 -*-
from collections import defaultdict
import json
import re
import unicodedata
from odoo.http import request, Response
from odoo import fields, http

import logging

_logger = logging.getLogger(__name__)

SKILL_RE = re.compile(r"^experiences_(\d+)_([a-z0-9_]+)_skill_id_(\d+)$")
LEVEL_RE = re.compile(r"^experiences_(\d+)_([a-z0-9_]+)_skill_level_(\d+)$")

def _slugify(value):
        """
        'Logiciels bureautiques' → 'logiciels_bureautiques'
        'C++ / Python'           → 'c_python'
        'Équipements spéciaux'   → 'equipements_speciaux'
        """
        if not value:
            return ""

        # remove accents
        value = unicodedata.normalize("NFKD", value)
        value = value.encode("ascii", "ignore").decode("ascii")

        value = value.lower()
        value = re.sub(r"[^a-z0-9]+", "_", value)
        value = value.strip("_")
        return value

class AchmitechHrRecruitment(http.Controller):
    @http.route(
    "/dossier/<string:token>",
    type="http",
    auth="public",
    website=True
    )
    def dossier_form(self, token, **kw):
        candidate = request.env["hr.applicant"].sudo().search(
            [("dca_access_token", "=", token)],
            limit=1
        )
        if not candidate:
            return request.not_found()

        if candidate.dca_submitted:
            return request.render("achmitech_hr_recruitment.dossier_already")

        return request.render("achmitech_hr_recruitment.dossier_form", {
            "candidate": candidate,
            "skill_types": self._get_competencies(),
        })
    
    def _get_competencies(self):
        SkillType = request.env["hr.skill.type"].sudo()

        skill_types = SkillType.search([], order="name")

        return {
            "skill_types": [
                {
                    "id": st.id,
                    "name": st.name,
                    "code": _slugify(st.name),
                }
                for st in skill_types
            ]
        }

    

    @http.route(
    "/dossier/submit",
    type="http",
    auth="public",
    website=True,
    methods=["POST"]
    )
    def dossier_submit(self, token=None, **post):
        candidate = request.env["hr.applicant"].sudo().search(
            [("dca_access_token", "=", token)],
            limit=1
        )
        if not candidate:
            return request.not_found()

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
        
        if candidate.dca_submitted:
            return request.render("achmitech_hr_recruitment.dossier_already")

        # 1) Snapshot for audit/debug
        candidate.write({
            "dca_payload_json": json.dumps(post, ensure_ascii=False),
        })

        # 2) Build skill_type map: slug(name) -> id
        SkillType = request.env["hr.skill.type"].sudo()
        st_map = { _slugify(st.name): st.id for st in SkillType.search([]) }

        # 3) Parse payload
        # Structure:
        # parsed[exp_idx] = {
        #   "fields": {...},
        #   "competencies": { scope: { line_idx: {"skill_id":.., "skill_level_id":..} } }
        # }
        parsed = defaultdict(lambda: {"fields": {}, "competencies": defaultdict(lambda: defaultdict(dict))})

        for k, v in post.items():
            if v in (None, "", False):
                continue

            m = SKILL_RE.match(k)
            if m:
                exp, scope, line = m.groups()
                parsed[int(exp)]["competencies"][scope][int(line)]["skill_id"] = int(v)
                continue

            m = LEVEL_RE.match(k)
            if m:
                exp, scope, line = m.groups()
                parsed[int(exp)]["competencies"][scope][int(line)]["skill_level_id"] = int(v)
                continue

            # Experience-level fields: accept a few common patterns
            # - experiences_<idx>_name
            # - experiences_name_<idx>
            # - experiences_<idx>_name_<idx>
            if k.startswith("experiences_"):
                parts = k.split("_")
                # try to detect exp index
                if len(parts) >= 2 and parts[1].isdigit():
                    exp_idx = int(parts[1])
                    parsed[exp_idx]["fields"][k] = v
                else:
                    # maybe experiences_name_0 style
                    tail = parts[-1]
                    if tail.isdigit():
                        exp_idx = int(tail)
                        parsed[exp_idx]["fields"][k] = v

        # 4) Clear previous draft lines (important to avoid duplicates)
        candidate.dossier_experience_ids.unlink()

        Experience = request.env["hr.applicant.dossier.experience"].sudo()
        Competency = request.env["hr.applicant.dossier.competency"].sudo()

        def _get_field(fields_dict, exp_idx, base):
            """
            Try multiple naming conventions and return first match:
              experiences_<idx>_<base>
              experiences_<idx>_<base>_<idx>
              experiences_<base>_<idx>
            """
            candidates = [
                f"experiences_{exp_idx}_{base}",
                f"experiences_{exp_idx}_{base}_{exp_idx}",
                f"experiences_{base}_{exp_idx}",
            ]
            for c in candidates:
                if c in fields_dict:
                    return fields_dict[c]
            return None

        created_any = False

        for exp_idx in sorted(parsed.keys()):
            exp_data = parsed[exp_idx]

            # Extract experience fields (optional)
            name = f"Projet {exp_idx + 1}"
            company = post.get(f"experiences_company_{exp_idx}", "")
            start = post.get(f"experiences_start_{exp_idx}") or False
            end = post.get(f"experiences_end_{exp_idx}") or False
            poste = post.get(f"experiences_poste_{exp_idx}", "")
            role = post.get(f"experiences_role_{exp_idx}", "")

            contexte = post.get(f"experiences_contexte_{exp_idx}", "")
            sujet = post.get(f"experiences_sujet_{exp_idx}", "")
            travail = post.get(f"experiences_travail_{exp_idx}", "")
            resultats = post.get(f"experiences_resultats_{exp_idx}", "")


            # Normalize dates if they come as strings YYYY-MM-DD (Odoo can accept it)
            # We'll just pass through.

            # Build competency create vals (skip empty lines)
            comp_vals = []
            for scope, lines in exp_data["competencies"].items():
                skill_type_id = st_map.get(scope)  # scope = slugified skill type name
                if not skill_type_id:
                    # If scope doesn't match (maybe renamed), skip safely
                    continue

                for line_idx in sorted(lines.keys()):
                    skill_id = lines[line_idx].get("skill_id")
                    level_id = lines[line_idx].get("skill_level_id")

                    if not skill_id:
                        continue  # ✅ ignore empty line

                    comp_vals.append((0, 0, {
                        "sequence": (line_idx + 1) * 10,
                        "skill_type_id": skill_type_id,
                        "skill_id": skill_id,
                        "skill_level_id": level_id or False,
                    }))

            # Skip fully empty experience (no fields + no skills)
            has_any_field = any([
                company,
                poste,
                role,
                start,
                end,
                contexte,
                sujet,
                travail,
                resultats,
            ])

            if not has_any_field and not comp_vals:
                continue

            # If user didn't fill a name but has competencies, generate one
            if not name:
                name = f"Projet {exp_idx + 1}"

            exp = Experience.create({
                "applicant_id": candidate.id,
                "name": name,
                "sequence": (exp_idx + 1) * 10,
                "company": company,
                "start": start,
                "end": end,
                "poste": poste,
                "role": role,
                "contexte": contexte,
                "sujet": sujet,
                "travail": travail,
                "resultats": resultats,
                "competency_line_ids": comp_vals,
            })


            created_any = True

        candidate.write({
            "dca_submitted": True,
            "dca_submitted_date": fields.Datetime.now(),
        })

        # If nothing created, you may want to not submit:
        # (choose behavior)
        # if not created_any:
        #     applicant.write({"dca_submitted": False, "dca_submitted_date": False})
        #     return request.render("achmitech_hr_recruitment.dossier_form", {...})

        return request.make_json_response({
            "redirect": f"/dossier/thank-you/{candidate.dca_access_token}"
        })

                
    @http.route("/dossier/thank-you/<string:token>", type="http", auth="public", website=True)
    def dossier_thankyou(self, token, **kw):
        applicant = request.env["hr.applicant"].sudo().search([("dca_access_token", "=", token)], limit=1)
        if not applicant:
            return request.not_found()

        return request.render("achmitech_hr_recruitment.dossier_thankyou", {
            "candidate": applicant,
            "job_sudo": applicant.job_id.sudo() if applicant.job_id else False,
        })
    

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
        candidate = request.env["hr.applicant"].sudo().search(
            [("dca_access_token", "=", token)],
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