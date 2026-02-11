# -*- coding: utf-8 -*-
from collections import defaultdict
import json
import re
import unicodedata
from odoo.http import request, Response
from odoo import fields, http

import logging

_logger = logging.getLogger(__name__)

FORMATION_RE = re.compile(r"^formations_(title|start|end)_(\d+)$")
HABILITATION_RE = re.compile(r"^habilitations_title_(\d+)$")

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

        skill_types = self._get_competencies()

        dossier = self._build_dossier_prefill(candidate, skill_types)

        return request.render("achmitech_hr_recruitment.dossier_form", {
            "candidate": candidate,
            "skill_types": skill_types,
            "dossier": dossier
        })
    
    def _build_dossier_prefill(self, candidate, skill_types):
        """
        Returns:
        {
        "experiences": [
            {
            "company": "...",
            "start": "YYYY-MM-DD",
            "end": "YYYY-MM-DD",
            "poste": "...",
            "role": "...",
            "contexte": "...",
            "sujet": "...",
            "travail": "...",
            "resultats": "...",
            "competencies": {
                "<type_code>": [ {"skill_id": 12, "skill_level_id": 3}, ...]
            }
            }, ...
        ]
        }
        """
        # map id->code so we can group competencies by your scope code
        # assuming your _get_competencies returns list of {id,name,code}
        id2code = {t["id"]: t["code"] for t in (skill_types.get("skill_types") or [])}

        # ------------------------------------------------------
        # Formations
        # ------------------------------------------------------
        formations = []
        for f in candidate.dossier_formation_ids.sorted("sequence"):
            formations.append({
                "title": f.title or "",
                "start": f.start.isoformat() if f.start else "",
                "end": f.end.isoformat() if f.end else "",
            })

        # ------------------------------------------------------
        # Habilitations
        # ------------------------------------------------------
        habilitations = []
        for h in candidate.dossier_habilitation_ids.sorted("sequence"):
            habilitations.append({
                "title": h.title or "",
            })
        
        # ------------------------------------------------------
        # Experiences
        # ------------------------------------------------------
        experiences = []
        for exp in candidate.dossier_experience_ids.sorted("sequence"):
            comp_by_code = {}
            for line in exp.competency_line_ids.sorted("sequence"):
                code = id2code.get(line.skill_type_id.id)
                if not code:
                    continue
                comp_by_code.setdefault(code, []).append({
                    "skill_id": line.skill_id.id,
                    "skill_name": line.skill_id.name,          # useful for Choices initial label
                    "skill_level_id": line.skill_level_id.id if line.skill_level_id else False,
                    "skill_level_name": line.skill_level_id.name if line.skill_level_id else "",
                })

            experiences.append({
                "company": exp.company or "",
                "start": exp.start.isoformat() if exp.start else "",
                "end": exp.end.isoformat() if exp.end else "",
                "poste": exp.poste or "",
                "role": exp.role or "",
                "contexte": exp.contexte or "",
                "sujet": exp.sujet or "",
                "travail": exp.travail or "",
                "resultats": exp.resultats or "",
                "competencies": comp_by_code,
            })

        return {
                "experiences": experiences,
                "formations": formations or [{}],
                "habilitations": habilitations or [{}]
        }

    
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

        if candidate.dca_submitted:
            return request.render("achmitech_hr_recruitment.dossier_already")

        # 1) Snapshot for audit/debug
        candidate.write({
            "dca_payload_json": json.dumps(post, ensure_ascii=False),
        })

        # ----------------------------
        # A) Parse FORMATIONS + HABILITATIONS from POST
        # ----------------------------
        formations = defaultdict(dict)      # idx -> {"title":..., "start":..., "end":...}
        habilitations = defaultdict(dict)   # idx -> {"title":...}

        for k, v in post.items():
            if v in (None, "", False):
                continue

            # formations_title_0, formations_start_0, formations_end_0
            m = re.match(r"^formations_(title|start|end)_(\d+)$", k)
            if m:
                field_name, idx = m.groups()
                formations[int(idx)][field_name] = v
                continue

            # habilitations_title_0
            m = re.match(r"^habilitations_title_(\d+)$", k)
            if m:
                idx = int(m.group(1))
                habilitations[idx]["title"] = v
                continue

        # ----------------------------
        # B) Clear previous draft lines (avoid duplicates)
        # ----------------------------
        # Replace these O2M names if yours differ
        if hasattr(candidate, "dossier_formation_ids"):
            candidate.dossier_formation_ids.unlink()
        if hasattr(candidate, "dossier_habilitation_ids"):
            candidate.dossier_habilitation_ids.unlink()

        Formation = request.env["hr.applicant.dossier.formation"].sudo()
        Habilitation = request.env["hr.applicant.dossier.habilitation"].sudo()

        # Create formations (skip empty title)
        for idx in sorted(formations.keys()):
            data = formations[idx]
            title = (data.get("title") or "").strip()
            if not title:
                continue

            Formation.create({
                "applicant_id": candidate.id,
                "sequence": (idx + 1) * 10,
                "title": title,
                "start": data.get("start") or False,  # "YYYY-MM-DD" ok for Date
                "end": data.get("end") or False,
            })

        # Create habilitations (skip empty title)
        for idx in sorted(habilitations.keys()):
            title = (habilitations[idx].get("title") or "").strip()
            if not title:
                continue

            Habilitation.create({
                "applicant_id": candidate.id,
                "sequence": (idx + 1) * 10,
                "title": title,
            })



        # 2) Build skill_type map: slug(name) -> id
        SkillType = request.env["hr.skill.type"].sudo()
        st_map = {_slugify(st.name): st.id for st in SkillType.search([])}

        # 3) Parse only competencies (skills + levels) by experience/scope/line
        # parsed[exp_idx]["competencies"][scope][line] = {"skill_id":.., "skill_level_id":..}
        parsed = defaultdict(lambda: {"competencies": defaultdict(lambda: defaultdict(dict))})

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

        # 4) Clear previous draft lines (avoid duplicates)
        candidate.dossier_experience_ids.unlink()

        Experience = request.env["hr.applicant.dossier.experience"].sudo()

        created_any = False

        # We need to iterate on experiences that have either competencies OR fields in post
        # So we detect exp indexes from post keys as well.
        exp_indexes = set(parsed.keys())
        for k in post.keys():
            if k.startswith("experiences_"):
                parts = k.split("_")
                if len(parts) >= 3 and parts[-1].isdigit():
                    exp_indexes.add(int(parts[-1]))

        for exp_idx in sorted(exp_indexes):
            # ---- fields
            company = post.get(f"experiences_company_{exp_idx}", "")
            start = post.get(f"experiences_start_{exp_idx}") or False
            end = post.get(f"experiences_end_{exp_idx}") or False
            poste = post.get(f"experiences_poste_{exp_idx}", "")
            role = post.get(f"experiences_role_{exp_idx}", "")
            contexte = post.get(f"experiences_contexte_{exp_idx}", "")
            sujet = post.get(f"experiences_sujet_{exp_idx}", "")
            travail = post.get(f"experiences_travail_{exp_idx}", "")
            resultats = post.get(f"experiences_resultats_{exp_idx}", "")

            name = post.get(f"experiences_name_{exp_idx}") or f"Projet {exp_idx + 1}"

            # ---- competencies
            comp_vals = []
            exp_data = parsed.get(exp_idx) or {"competencies": {}}

            for scope, lines in exp_data["competencies"].items():
                skill_type_id = st_map.get(scope)
                if not skill_type_id:
                    continue

                for line_idx in sorted(lines.keys()):
                    skill_id = lines[line_idx].get("skill_id")
                    if not skill_id:
                        continue

                    level_id = lines[line_idx].get("skill_level_id")
                    comp_vals.append((0, 0, {
                        "sequence": (line_idx + 1) * 10,
                        "skill_type_id": skill_type_id,
                        "skill_id": skill_id,
                        "skill_level_id": level_id or False,
                    }))

            has_any_field = any([
                company, poste, role, start, end, contexte, sujet, travail, resultats
            ])

            if not has_any_field and not comp_vals:
                continue

            Experience.create({
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

        if created_any:
            candidate.write({
                "dca_submitted": True,
                "dca_submitted_date": fields.Datetime.now(),
            })

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
        skill_type_id = payload.get("skill_type_id") or kwargs.get("skill_type_id")

        if not q or len(q) < 2:
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
    
    @http.route("/dossier/get-levels", type="json2", auth="public", methods=['POST'], website=True, csrf=False)
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
        if not skill.exists() or not skill.skill_type_id:
            return Response(
                json.dumps({"levels": []}),
                content_type='application/json'
            )

        levels = request.env["hr.skill.level"].with_context(lang="fr_FR").sudo().search(
            [("skill_type_id", "=", skill.skill_type_id.id)],
            order="id"
        )

        return Response(
            json.dumps({"levels": [{"id": l.id, "name": l.name} for l in levels]}),
            content_type='application/json'
        )