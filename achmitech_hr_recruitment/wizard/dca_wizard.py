import base64
import io
import json
import logging
import os
import re
import unicodedata
from datetime import date

from odoo import _, fields, models
from odoo.exceptions import UserError

try:
    from docx import Document
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
except ImportError:
    Document = None
    OxmlElement = None
    qn = None

_logger = logging.getLogger(__name__)


class DcaWizard(models.TransientModel) :

    _name = 'dca.wizard'
    _description = 'DCA Report Generation Wizard'
    report_models = fields.Selection([('alten', 'Alten'), ('simplified', 'Achmitech')], 'Modèle  de Dossier',  required=True, default='simplified')
    applicant_id = fields.Many2one('hr.applicant', 'candidate')
    code_job = fields.Char('Reference de poste')
    report_type = fields.Selection([('PDF', 'PDF'), ('WORD', 'Word')], 'Type de Fichier', required=True, default='WORD')
    dca_ready = fields.Boolean(related='applicant_id.dca_ready')
    dca_review_notes = fields.Text(related='applicant_id.dca_review_notes')
    _DCA_CATEGORY_ORDER = [
        'Soft Skills',
        'Langues',
        'Logiciels',
        'Langages de programmation',
        'Matériels',
        'Méthodes',
        'Normes et protocoles',
        'Systèmes',
        'Technologies',
        'Marketing',
    ]
    _LANGUAGE_LEVELS = {'A1', 'A2', 'B1', 'B2', 'C1', 'C2'}
    _LANGUAGE_LEVEL_RE = re.compile(r'\b(A1|A2|B1|B2|C1|C2)\b', re.IGNORECASE)
    _EMPTY = 'A Compléter'
    # "[À valider]", "[IA - À valider]", "(À valider)"...
    _AI_MARKER_RE = re.compile(r'\s*[\[(]\s*(?:IA\s*[-–:]?\s*)?[ÀAà]\s+valider\s*[\])]', re.IGNORECASE)
    _LANGUAGE_NAMES = {
        'francais': 'Français', 'french': 'Français',
        'anglais': 'Anglais', 'english': 'Anglais',
        'arabe': 'Arabe', 'arabic': 'Arabe',
        'espagnol': 'Espagnol', 'spanish': 'Espagnol',
        'allemand': 'Allemand', 'german': 'Allemand',
        'italien': 'Italien', 'italian': 'Italien',
        'portugais': 'Portugais', 'portuguese': 'Portugais',
    }
    _NARRATIVE_FIELDS = ('general_context', 'project_topic', 'responsibilities', 'work_done', 'results_obtained')
    _NARRATIVE_ALIASES = {
        'general_context': ('general_context', 'contexte_general', 'generalContext', 'context', 'contexte'),
        'project_topic': ('project_topic', 'sujet_du_projet', 'projectTopic', 'project_subject', 'topic'),
        'responsibilities': ('responsibilities', 'responsabilites_occupees', 'responsibility', 'role', 'missions'),
        'work_done': ('work_done', 'travail_realise', 'workDone', 'realisations'),
        'results_obtained': ('results_obtained', 'resultats_obtenus', 'resultsObtained', 'results'),
    }
    _NARRATIVE_LABELS = {
        'general_context': 'contexte général',
        'project_topic': 'sujet du projet',
        'responsibilities': 'responsabilités',
        'work_done': 'travail réalisé',
        'results_obtained': 'résultats obtenus',
    }
    # libellé normalisé d'une ligne de tableau Word -> catégorie du JSON.
    _DCA_TABLE_CATEGORIES = {
        'logiciels': 'Logiciels',
        'langages': 'Langages de programmation',
        'technologies': 'Technologies',
        'methodes': 'Méthodes',
        'systemes': 'Systèmes',
        'normes et protocoles': 'Normes et protocoles',
        'materiels': 'Matériels',
    }


    def get_applicant_extracted_payload(self) :
        raw_payload = self.applicant_id.applicant_extracted_json or '{}'
        if isinstance(raw_payload, dict) :
            return raw_payload
        
        try:
            payload = json.loads(raw_payload)
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    # conversion robuste vers chaîne nettoyée.
    def _to_text(self, value):
        return str(value or '').strip()

    # initiales du nom : première lettre du prénom + premières consonnes groupées du nom.
    # ex: "Ayoub Jbili" → "AJB" (J et B sont deux consonnes initiales de "Jbili")
    def _compute_initials(self, name):
        vowels = set('aeiouyàâäéèêëïîôöùûüÿæœ')
        words = self._to_text(name).split()
        initials = []
        for word in words:
            letters = [c for c in word if c.isalpha()]
            if not letters:
                continue
            result = letters[0].upper()
            if (len(letters) > 1
                    and letters[0].lower() not in vowels
                    and letters[1].lower() not in vowels):
                result += letters[1].upper()
            initials.append(result)
        return ''.join(initials)

    # remplit les placeholders de l'en-tête simplifié (table[0], cellule 0).
    # Remplace {{INITIALES}}, {{TITRE_POSTE}}, {{DISPONIBILITE}} run par run
    # (document.paragraphs ignore les cellules de tableau).
    def _fill_simplified_header_table(self, document, applicant_name, job_title, availability_date):
        if not document.tables:
            return
        initials = self._compute_initials(applicant_name)
        avail_str = availability_date.strftime('%d/%m/%Y') if availability_date else self._EMPTY
        placeholder_map = {
            '{{INITIALES}}': initials,
            '{{TITRE_POSTE}}': self._to_text(job_title),
            '{{DISPONIBILITE}}': avail_str,
        }
        for row in document.tables[0].rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    for run in para.runs:
                        for placeholder, value in placeholder_map.items():
                            if placeholder in run.text:
                                run.text = run.text.replace(placeholder, value)

    # normalise un label (minuscules, suppression accents/punctuation) pour matcher des titres Word.
    def _normalize_label(self, text):
        raw_text = self._to_text(text).lower()
        normalized = ''.join(
            ch for ch in unicodedata.normalize('NFD', raw_text)
            if unicodedata.category(ch) != 'Mn'
        )
        normalized = re.sub(r'[^a-z0-9]+', ' ', normalized)
        return re.sub(r'\s+', ' ', normalized).strip()

    # écrit proprement dans un paragraphe (gestion des runs).
    def _set_paragraph_text(self, paragraph, text):
        value = self._to_text(text)
        if paragraph.runs:
            paragraph.runs[0].text = value
            for run in paragraph.runs[1:]:
                run.text = ''
            return
        paragraph.text = value

    # écrit proprement dans une cellule de table.
    def _set_cell_text(self, cell, text):
        value = self._to_text(text)
        if cell.paragraphs:
            self._set_paragraph_text(cell.paragraphs[0], value)
            for paragraph in cell.paragraphs[1:]:
                self._set_paragraph_text(paragraph, '')
            return
        cell.text = value

    # détecte les lignes de points (.... ou ...) utilisées comme zones de saisie visuelle.
    def _is_dotted_placeholder(self, text):
        raw_text = self._to_text(text)
        if not raw_text:
            return False
        compact = re.sub(r'\s+', '', raw_text)
        return bool(re.fullmatch(r'[\.\u2026]{2,}', compact))

    #  remplit le bloc pointillé suivant un label narratif et retourne un booléen (True/False).
    def _fill_following_dotted_block(self, paragraphs, start_index, value):
        dotted_indexes = []
        label_markers = (
            'contexte general',
            'sujet du projet',
            'responsabilites occupees',
            'travail realise',
            'resultats obtenus',
        )

        for idx in range(start_index, len(paragraphs)):
            paragraph_text = self._to_text(paragraphs[idx].text)
            normalized = self._normalize_label(paragraph_text)
            if any(marker in normalized for marker in label_markers):
                break
            if self._is_dotted_placeholder(paragraph_text):
                dotted_indexes.append(idx)
                continue
            if dotted_indexes and paragraph_text:
                break

        if not dotted_indexes:
            return False

        raw_lines = [line.strip() for line in str(value or '').split('\n') if line.strip()]
        if not raw_lines:
            raw_lines = [self._EMPTY]

        for pos, paragraph_idx in enumerate(dotted_indexes):
            if pos < len(raw_lines):
                self._set_paragraph_text(paragraphs[paragraph_idx], raw_lines[pos])
            else:
                # Remove unused placeholder rows to avoid rendering empty icon/bullet lines.
                self._remove_paragraph(paragraphs[paragraph_idx])

        # Keep remaining content if list has more items than template lines.
        if len(raw_lines) > len(dotted_indexes):
            overflow = '\n'.join(raw_lines[len(dotted_indexes):])
            last_idx = dotted_indexes[-1]
            base_text = self._to_text(paragraphs[last_idx].text)
            self._set_paragraph_text(paragraphs[last_idx], '%s\n%s' % (base_text, overflow))
        return True

    #  fallback ajouté pour écrire directement sur la ligne du label si aucun bloc pointillé n’est détecté.
    def _fill_label_inline(self, paragraph, value):
        clean_value = self._to_text(value)
        if not clean_value:
            return

        current = self._to_text(paragraph.text)
        if not current:
            self._set_paragraph_text(paragraph, clean_value)
            return

        if ':' in current:
            label = current.split(':', 1)[0].strip()
            self._set_paragraph_text(paragraph, '%s: %s' % (label, clean_value))
            return

        self._set_paragraph_text(paragraph, '%s %s' % (current, clean_value))

    def _remove_table(self, table):
        table_element = table._element
        parent_element = table_element.getparent()
        if parent_element is not None:
            parent_element.remove(table_element)

    def _remove_paragraph(self, paragraph):
        paragraph_element = paragraph._element
        parent_element = paragraph_element.getparent()
        if parent_element is not None:
            parent_element.remove(paragraph_element)

    def _table_has_immediate_page_break_before(self, table):
        table_element = table._element
        previous = table_element.getprevious()
        if previous is None:
            return False

        # A page break can be represented either as paragraph property
        # (pageBreakBefore) or as a run break of type "page".
        if previous.tag == qn('w:p'):
            if previous.find('.//w:pageBreakBefore', namespaces=previous.nsmap) is not None:
                return True
            for break_node in previous.findall('.//w:br', namespaces=previous.nsmap):
                if break_node.get(qn('w:type')) == 'page':
                    return True
        return False

    def _insert_page_break_before_table(self, table):
        if OxmlElement is None or qn is None:
            return

        if self._table_has_immediate_page_break_before(table):
            return

        paragraph_break = OxmlElement('w:p')
        run = OxmlElement('w:r')
        break_node = OxmlElement('w:br')
        break_node.set(qn('w:type'), 'page')
        run.append(break_node)
        paragraph_break.append(run)

        table._element.addprevious(paragraph_break)

    def _clear_paragraph_numbering(self, paragraph):
        paragraph_properties = paragraph._element.pPr
        if paragraph_properties is not None and paragraph_properties.numPr is not None:
            paragraph_properties.remove(paragraph_properties.numPr)

    def _clear_paragraph_page_breaks(self, paragraph):
        paragraph_properties = paragraph._element.pPr
        if paragraph_properties is not None and paragraph_properties.pageBreakBefore is not None:
            paragraph_properties.remove(paragraph_properties.pageBreakBefore)

        for run in paragraph.runs:
            run_element = run._element
            for break_element in list(run_element.findall('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}br')):
                run_element.remove(break_element)

    def _prune_unused_project_sections(self, document, experiences_count, project_start_table_idx=3):
        project_pair_step = 2

        max_experiences = max(0, int(experiences_count or 0))
        first_table_to_remove = project_start_table_idx + (max_experiences * project_pair_step)
        if first_table_to_remove < len(document.tables):
            for table in reversed(document.tables[first_table_to_remove:]):
                self._remove_table(table)

        paragraphs = document.paragraphs
        current_experience_idx = -1
        in_pruned_experience_block = False
        paragraphs_to_remove = []

        for idx, paragraph in enumerate(paragraphs):
            normalized = self._normalize_label(paragraph.text)
            if 'contexte general' in normalized:
                current_experience_idx += 1
                in_pruned_experience_block = current_experience_idx >= max_experiences

            if not in_pruned_experience_block:
                continue

            self._set_paragraph_text(paragraph, '')
            self._clear_paragraph_numbering(paragraph)
            self._clear_paragraph_page_breaks(paragraph)
            paragraphs_to_remove.append(paragraph)

            # Remove dotted placeholders immediately after pruned labels.
            if any(marker in normalized for marker in (
                'contexte general',
                'sujet du projet',
                'responsabilites occupees',
                'travail realise',
                'resultats obtenus',
            )):
                self._fill_following_dotted_block(paragraphs, idx + 1, '')

        # Physically remove pruned paragraphs so Word no longer reserves blank pages.
        for paragraph in reversed(paragraphs_to_remove):
            self._remove_paragraph(paragraph)

    # nettoie et déduplique les tâches
    def _normalize_task_list(self, tasks):
        if isinstance(tasks, str):
            return [self._to_text(tasks)] if self._to_text(tasks) else []
        if not isinstance(tasks, list):
            return []

        normalized = []
        seen = set()
        for raw_task in tasks:
            task_text = self._to_text(raw_task)
            if not task_text:
                continue
            fingerprint = task_text.lower()
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            normalized.append(task_text)
        return normalized

    # ------------------------------------------------------------------
    # Marqueurs IA
    # ------------------------------------------------------------------
    # supprime les marqueurs "[À valider]" / "[IA - À valider]" qui ne doivent jamais apparaître chez le client.
    def _strip_ai_markers(self, value):
        if isinstance(value, str):
            cleaned = self._AI_MARKER_RE.sub('', value)
            cleaned = re.sub(r'[ \t]+\n', '\n', cleaned)
            return re.sub(r'[ \t]{2,}', ' ', cleaned).strip()
        if isinstance(value, list):
            return [self._strip_ai_markers(item) for item in value]
        if isinstance(value, dict):
            return {key: self._strip_ai_markers(item) for key, item in value.items()}
        return value

    def _has_ai_marker(self, value):
        if isinstance(value, str):
            return bool(self._AI_MARKER_RE.search(value))
        if isinstance(value, list):
            return any(self._has_ai_marker(item) for item in value)
        if isinstance(value, dict):
            return any(self._has_ai_marker(item) for item in value.values())
        return False

    # ------------------------------------------------------------------
    # Normalisation du JSON extrait (ancien et nouveau format)
    # ------------------------------------------------------------------
    def _dedup_texts(self, items):
        result = []
        seen = set()
        for raw_item in (items or []):
            text = self._to_text(raw_item)
            if not text or text.lower() in seen:
                continue
            seen.add(text.lower())
            result.append(text)
        return result

    def _normalize_skill_categories(self, raw_categories):
        raw_categories = raw_categories if isinstance(raw_categories, dict) else {}
        return {
            category_name: self._dedup_texts(raw_categories.get(category_name))
            for category_name in self._DCA_CATEGORY_ORDER
        }

    def _normalize_education(self, payload):
        raw_education = payload.get('education')
        if isinstance(raw_education, dict):
            raw_education = [raw_education]
        educations = []
        for item in (raw_education if isinstance(raw_education, list) else []):
            if not isinstance(item, dict):
                continue
            entry = {
                'degree': self._to_text(item.get('degree')),
                'field': self._to_text(item.get('field')),
                'university': self._to_text(item.get('university')),
                'date': self._to_text(item.get('date')),
            }
            if any(entry.values()):
                educations.append(entry)
        return educations

    def _format_language_name(self, name):
        label = self._LANGUAGE_NAMES.get(self._normalize_label(name))
        if label:
            return label
        name = self._to_text(name)
        return name[:1].upper() + name[1:]

    def _format_language_level(self, level):
        level = self._to_text(level)
        match = self._LANGUAGE_LEVEL_RE.search(level)
        if match:
            return match.group(1).upper()
        if self._normalize_label(level) in ('natif', 'native', 'langue maternelle', 'maternelle', 'bilingue'):
            return 'Natif' if self._normalize_label(level) != 'bilingue' else 'Bilingue'
        return level

    # retourne [{'name': 'Anglais', 'level': 'C1', 'inferred': False}, ...]
    def _normalize_languages(self, payload):
        entries = []
        raw_languages = payload.get('languages')
        if isinstance(raw_languages, list) and raw_languages:
            for item in raw_languages:
                if isinstance(item, dict):
                    entries.append((item.get('name'), item.get('level'), bool(item.get('inferred'))))
                else:
                    entries.append((item, '', False))
        else:
            # ancien format : langues dans "skills" (niveau A1-C2) ou sous une clé "langues".
            skills_raw = payload.get('skills') if isinstance(payload.get('skills'), dict) else {}
            for skill_name, level in skills_raw.items():
                if isinstance(level, dict):
                    if self._normalize_label(skill_name) == 'langues':
                        entries.extend((name, lvl, False) for name, lvl in level.items())
                elif self._LANGUAGE_LEVEL_RE.search(self._to_text(level)):
                    entries.append((skill_name, level, False))

        languages = []
        seen = set()
        for name, level, inferred in entries:
            if not self._to_text(name):
                continue
            label = self._format_language_name(name)
            if label.lower() in seen:
                continue
            seen.add(label.lower())
            languages.append({'name': label, 'level': self._format_language_level(level), 'inferred': inferred})
        return languages

    def _format_language(self, language):
        if language.get('level'):
            return '%s (%s)' % (language['name'], language['level'])
        return language['name']

    def _normalize_applicant_payload_for_word(self, applicant_data):
        payload = applicant_data if isinstance(applicant_data, dict) else {}

        skills_raw = payload.get('skills') if isinstance(payload.get('skills'), dict) else {}
        skills = {}
        for raw_name, raw_level in skills_raw.items():
            name = self._to_text(raw_name)
            if not name:
                continue
            if isinstance(raw_level, dict):
                nested = {self._to_text(n): self._to_text(l) for n, l in raw_level.items() if self._to_text(n) and self._to_text(l)}
                if nested:
                    skills[name] = nested
            else:
                level = self._to_text(raw_level)
                if level:
                    skills[name] = level

        normalized_experiences = []
        for raw_experience in (payload.get('experiences') or []):
            if not isinstance(raw_experience, dict):
                continue

            # champs déduits : liste explicite (nouveau prompt) + marqueurs dans le texte (ancien prompt).
            inferred = {self._to_text(name) for name in (raw_experience.get('inferred_fields') or []) if self._to_text(name)}
            for field_name in self._NARRATIVE_FIELDS:
                if self._has_ai_marker(self._raw_experience_field(raw_experience, field_name)):
                    inferred.add(field_name)
            if self._has_ai_marker(raw_experience.get('skills_pertinents')):
                inferred.add('skills_pertinents')

            experience = self._strip_ai_markers(raw_experience)
            duration = self._to_text(experience.get('duration'))
            start = self._to_text(experience.get('start_date'))
            if not duration and start and start.lower() != 'unknown':
                end = self._to_text(experience.get('end_date'))
                end = 'présent' if not end or end.lower() == 'present' else end
                duration = '%s - %s' % (start, end)

            normalized_experiences.append({
                'company': self._to_text(experience.get('company')),
                'title': self._to_text(experience.get('title')),
                'duration': duration,
                'general_context': self._pick_experience_field_text(experience, 'general_context'),
                'project_topic': self._pick_experience_field_text(experience, 'project_topic'),
                'responsibilities': self._pick_experience_field_text(experience, 'responsibilities'),
                'work_done': self._pick_experience_field_text(experience, 'work_done'),
                'results_obtained': self._pick_experience_field_text(experience, 'results_obtained'),
                'tasks': self._normalize_task_list(experience.get('tasks')),
                'skills_pertinents': self._normalize_skill_categories(experience.get('skills_pertinents')),
                'inferred_fields': sorted(inferred),
                'inferred_skills': self._dedup_texts(experience.get('inferred_skills')),
            })

        clean_payload = self._strip_ai_markers(payload)
        return {
            'name': self._to_text(clean_payload.get('name')),
            'education': self._normalize_education(clean_payload),
            'languages': self._normalize_languages(clean_payload),
            'skills': skills,
            'skills_by_category': self._normalize_skill_categories(clean_payload.get('skills_by_category')),
            'inferred_skills': self._dedup_texts(clean_payload.get('inferred_skills')),
            'extraction_warnings': self._dedup_texts(clean_payload.get('extraction_warnings')),
            'experiences': normalized_experiences,
            'certification': self._dedup_texts(clean_payload.get('certification')),
            'experience_years': self._to_text(clean_payload.get('experience_years')),
        }

    # valeur brute d'un champ narratif (premier alias renseigné), sans transformation.
    def _raw_experience_field(self, experience, field_name):
        for key_name in self._NARRATIVE_ALIASES.get(field_name, (field_name,)):
            raw_value = experience.get(key_name)
            if raw_value:
                return raw_value
        return None

    # récupère un champ narratif avec aliases (general_context, contexte_general, etc.).
    # Seul "travail réalisé" peut se rabattre sur la liste des tâches : les autres champs restent vides
    # plutôt que de recopier les tâches dans plusieurs rubriques.
    def _pick_experience_field_text(self, experience, field_name):
        if not isinstance(experience, dict):
            return ''

        def _list_to_lines(items):
            cleaned_items = [self._to_text(item) for item in (items or []) if self._to_text(item)]
            return '\n'.join(cleaned_items)

        raw_value = self._raw_experience_field(experience, field_name)
        if isinstance(raw_value, list):
            if field_name in ('work_done', 'results_obtained'):
                value = _list_to_lines(raw_value)
            else:
                value = '; '.join(self._to_text(item) for item in raw_value if self._to_text(item))
        else:
            value = self._to_text(raw_value)
        if value:
            return value

        if field_name == 'work_done':
            return _list_to_lines(self._normalize_task_list(experience.get('tasks')))
        return ''

    # ------------------------------------------------------------------
    # Contrôle "prêt à envoyer"
    # ------------------------------------------------------------------
    # retourne (bloquants, à relire) : listes de messages en français.
    def _get_dca_review(self, applicant):
        raw_payload = applicant.applicant_extracted_json or ''
        try:
            payload = json.loads(raw_payload) if raw_payload else {}
        except Exception:
            payload = {}
        if not isinstance(payload, dict) or not payload:
            return [_("Aucune donnée extraite : lancez le scoring IA.")], []

        data = self._normalize_applicant_payload_for_word(payload)
        # alertes du contrôle automatique n8n (textes ou compétences recopiés, dates illisibles...).
        blocking = [_("Alerte extraction : %s") % warning for warning in data['extraction_warnings']]
        to_review = []

        if not applicant.availability:
            blocking.append(_("Date de disponibilité non renseignée sur la fiche candidat."))
        if not data['education']:
            blocking.append(_("Formation absente."))
        if not data['languages']:
            blocking.append(_("Langues absentes."))
        inferred_languages = [lang['name'] for lang in data['languages'] if lang.get('inferred')]
        if inferred_languages:
            to_review.append(_("Langues déduites : %s.") % ', '.join(inferred_languages))
        if data['inferred_skills']:
            to_review.append(_("Compétences globales déduites : %s.") % ', '.join(data['inferred_skills']))
        if not data['experiences']:
            blocking.append(_("Aucune expérience extraite."))

        for index, experience in enumerate(data['experiences'], start=1):
            label = _("Expérience %(index)s (%(company)s)", index=index, company=experience['company'] or '?')
            missing = []
            if not experience['company']:
                missing.append(_("client"))
            if not experience['duration']:
                missing.append(_("dates"))
            missing += [self._NARRATIVE_LABELS[name] for name in self._NARRATIVE_FIELDS if not experience[name]]
            if not any(experience['skills_pertinents'].get(cat) for cat in self._DCA_TABLE_CATEGORIES.values()):
                missing.append(_("environnement technique"))
            if missing:
                blocking.append(_("%(label)s : manque %(fields)s.", label=label, fields=', '.join(missing)))

            inferred = [
                self._NARRATIVE_LABELS.get(name, _("environnement technique") if name == 'skills_pertinents' else name)
                for name in experience['inferred_fields']
            ]
            if inferred:
                to_review.append(_("%(label)s : déduit par l'IA - %(fields)s.", label=label, fields=', '.join(inferred)))
            if experience['inferred_skills']:
                to_review.append(_("%(label)s : compétences déduites - %(skills)s.",
                                   label=label, skills=', '.join(experience['inferred_skills'])))

        return blocking, to_review

    # ------------------------------------------------------------------
    # Remplissage du Word
    # ------------------------------------------------------------------
    # supprime des lignes de tableau en conservant la fusion verticale de la 1re colonne.
    def _remove_table_rows(self, table, rows):
        rows_to_remove = [row for row in rows if row is not None]
        if not rows_to_remove or len(rows_to_remove) >= len(table.rows):
            return
        removed_restart = False
        for row in rows_to_remove:
            first_tc = row._tr.tc_lst[0] if row._tr.tc_lst else None
            if first_tc is not None and first_tc.tcPr is not None and first_tc.tcPr.vMerge is not None \
                    and first_tc.tcPr.vMerge.val == 'restart':
                removed_restart = True
            row._tr.getparent().remove(row._tr)
        if removed_restart and table.rows:
            first_tc = table.rows[0]._tr.tc_lst[0]
            if first_tc.tcPr is not None and first_tc.tcPr.vMerge is not None:
                first_tc.tcPr.vMerge.val = 'restart'

    # remplit un tableau "catégorie -> valeurs" et retire les lignes vides
    # (si tout est vide, on garde les lignes avec "A Compléter").
    def _fill_category_table(self, table, values_by_category, label_cell_idx, value_cell_idx):
        filled_rows = []
        empty_rows = []
        for row in table.rows:
            if len(row.cells) <= value_cell_idx:
                continue
            category_name = self._DCA_TABLE_CATEGORIES.get(self._normalize_label(row.cells[label_cell_idx].text))
            if not category_name:
                continue
            values = values_by_category.get(category_name) or []
            (filled_rows if values else empty_rows).append((row, values))

        for row, values in filled_rows:
            self._set_cell_text(row.cells[value_cell_idx], ', '.join(values))
        if filled_rows:
            self._remove_table_rows(table, [row for row, _values in empty_rows])
        else:
            for row, _values in empty_rows:
                self._set_cell_text(row.cells[value_cell_idx], self._EMPTY)

    # remplit le docx (alten/simplified) par structure.
    # Les deux modèles ont la même disposition : table 1 = compétences, table 2 = formation,
    # puis une paire de tables (en-tête, environnement technique) par expérience.
    def _fill_dca_template_by_layout(self, document, applicant_data, table_offset=0):
        educations = applicant_data.get('education') or []
        experiences = applicant_data.get('experiences') if isinstance(applicant_data.get('experiences'), list) else []
        certifications = applicant_data.get('certification') or []
        languages = applicant_data.get('languages') or []

        # compétences globales = compétences des expériences + section compétences du CV.
        category_values = {}
        global_skills = applicant_data.get('skills_by_category') or {}
        for category_name in self._DCA_CATEGORY_ORDER:
            bucket = []
            for experience in experiences:
                bucket.extend((experience.get('skills_pertinents') or {}).get(category_name) or [])
            bucket.extend(global_skills.get(category_name) or [])
            category_values[category_name] = self._dedup_texts(bucket)

        competencies_idx = 1 + table_offset
        formation_idx = 2 + table_offset
        project_start_table_idx = 3 + table_offset

        if len(document.tables) > competencies_idx:
            self._fill_category_table(document.tables[competencies_idx], category_values, 0, 1)

        if len(document.tables) > formation_idx:
            formation_table = document.tables[formation_idx]
            education_lines = []
            education_dates = []
            for education in educations:
                parts = [education.get('degree'), education.get('field'), education.get('university')]
                education_lines.append(' - '.join(part for part in parts if part))
                education_dates.append(education.get('date') or '')
            rows_to_remove = []
            for row in formation_table.rows:
                if len(row.cells) < 2:
                    continue
                row_label = self._normalize_label(row.cells[0].text)
                if row_label == 'formation':
                    self._set_cell_text(row.cells[1], '\n'.join(education_lines) if education_lines else self._EMPTY)
                    if len(row.cells) > 2:
                        dates = '\n'.join(education_dates) if any(education_dates) else ''
                        self._set_cell_text(row.cells[2], dates or (self._EMPTY if not education_lines else ''))
                elif row_label == 'habilitations':
                    if certifications:
                        self._set_cell_text(row.cells[1], ', '.join(certifications))
                    else:
                        rows_to_remove.append(row)
                elif row_label == 'langues':
                    value = ', '.join(self._format_language(language) for language in languages)
                    self._set_cell_text(row.cells[1], value or self._EMPTY)
            self._remove_table_rows(formation_table, rows_to_remove)

        self._prune_unused_project_sections(document, len(experiences), project_start_table_idx)

        project_pair_step = 2
        project_slots = max(0, (len(document.tables) - project_start_table_idx) // project_pair_step)

        for project_idx in range(min(project_slots, len(experiences))):
            experience = experiences[project_idx]

            header_table_idx = project_start_table_idx + (project_idx * project_pair_step)
            env_table_idx = header_table_idx + 1

            if header_table_idx < len(document.tables):
                header_table = document.tables[header_table_idx]
                if project_idx > 0:
                    self._insert_page_break_before_table(header_table)
                if header_table.rows and len(header_table.rows[0].cells) >= 2:
                    self._set_cell_text(header_table.rows[0].cells[0], experience.get('company') or self._EMPTY)
                    self._set_cell_text(header_table.rows[0].cells[1], experience.get('duration') or self._EMPTY)

            if env_table_idx < len(document.tables):
                self._fill_category_table(
                    document.tables[env_table_idx], experience.get('skills_pertinents') or {}, 1, 2,
                )

        paragraphs = document.paragraphs
        current_experience_idx = -1
        label_to_field = {
            'contexte general': 'general_context',
            'sujet du projet': 'project_topic',
            'responsabilites occupees': 'responsibilities',
            'travail realise': 'work_done',
            'resultats obtenus': 'results_obtained',
        }

        for idx, paragraph in enumerate(paragraphs):
            normalized = self._normalize_label(paragraph.text)
            if 'contexte general' in normalized:
                current_experience_idx += 1

            field_name = None
            for label, mapped_field in label_to_field.items():
                if label in normalized:
                    field_name = mapped_field
                    break

            if field_name is None or current_experience_idx < 0:
                continue

            if current_experience_idx >= len(experiences):
                self._fill_following_dotted_block(paragraphs, idx + 1, '')
                continue

            resolved_value = experiences[current_experience_idx].get(field_name) or self._EMPTY
            filled = self._fill_following_dotted_block(
                paragraphs,
                idx + 1,
                resolved_value,
            )
            if not filled:
                self._fill_label_inline(paragraph, resolved_value)

    # résout le chemin du template selon report_models.
    def _get_template_path(self):
        module_root = os.path.dirname(os.path.dirname(__file__))
        template_by_model = {
            'alten': 'dca_alten_template.docx',
            'simplified': 'dca_simplified_template.docx',
        }
        template_name = template_by_model.get(self.report_models)
        if not template_name:
            raise UserError(_('Modèle de rapport non pris en charge pour l\'export Word.'))

        template_path = os.path.join(module_root, 'static', 'src', 'docx', template_name)
        if not os.path.exists(template_path):
            raise UserError(_('Template Word introuvable : %s') % template_name)
        return template_path

    # code job add function.
    def _fill_alten_footer_code_job(self, document, code_job_value):
        footer_value = self._to_text(code_job_value)
        if not footer_value:
            return

        for section in document.sections:
            for table in section.footer.tables:
                for row in table.rows:
                    if len(row.cells) < 1:
                        continue
                    self._set_cell_text(row.cells[0], footer_value)
                    return

    # pipeline.
    def _render_word_report(self, applicant_data, code_job_value=''):
        if Document is None:
            raise UserError(_('La librairie python-docx n\'est pas installée. Veuillez installer la dépendance : docx'))

        normalized_applicant_data = self._normalize_applicant_payload_for_word(applicant_data)
        template_path = self._get_template_path()

        document = Document(template_path)
        if self.report_models == 'simplified':
            self._fill_simplified_header_table(
                document,
                self.applicant_id.partner_name or '',
                self.applicant_id.job_id.name or '',
                self.applicant_id.availability,
            )
        if self.report_models in ('alten', 'simplified'):
            self._fill_dca_template_by_layout(document, normalized_applicant_data)
        if self.report_models == 'alten':
            self._fill_alten_footer_code_job(document, code_job_value)

        output_stream = io.BytesIO()
        document.save(output_stream)
        output_stream.seek(0)

        full_name = self._to_text(self.applicant_id.partner_name) or 'candidate'
        initials = self._compute_initials(full_name)
        date_str = date.today().strftime('%y.%m.%d')
        client = 'ALTEN' if self.report_models == 'alten' else 'ACHMITECH'
        filename = '%s_DC %s_%s.docx' % (date_str, client, initials)

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(output_stream.read()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'res_model': self._name,
            'res_id': self.id,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }

    def _get_or_extract_applicant_payload(self):
        applicant_data = self.get_applicant_extracted_payload()
        if not applicant_data:
            raise UserError(_('Aucune donnée extraite trouvée pour ce candidat. Veuillez d\'abord lancer l\'analyse IA.'))
        return applicant_data
    
    def print_report(self) :
        self.ensure_one()
        if not self.applicant_id:
            raise UserError(_('Veuillez sélectionner un candidat avant de générer le rapport.'))

        applicant_data = self._get_or_extract_applicant_payload()
        code_job_value = (self.code_job or '').strip()

        if self.report_type == 'PDF':
            raise UserError(_('L\'export PDF n\'est pas encore pris en charge. Veuillez utiliser le format Word.'))

        return self._render_word_report(applicant_data, code_job_value)
        
        return True