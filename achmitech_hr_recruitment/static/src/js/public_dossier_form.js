/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";
import { loadJS, loadCSS } from "@web/core/assets";

publicWidget.registry.WebsiteCustomerContactRequestForm = publicWidget.Widget.extend({
    selector: "#dossier_form",

    start: function () {
        return this._super(...arguments).then(() => {
            this._loadChoices();
            this._bindEvents();
        });
    },

    _loadChoices: async function () {
        try {
            await loadCSS("https://cdn.jsdelivr.net/npm/choices.js/public/assets/styles/choices.min.css");
            await loadJS("https://cdn.jsdelivr.net/npm/choices.js/public/assets/scripts/choices.min.js");
            this._initChoicesAll();
        } catch (error) {
            console.error("Erreur lors du chargement de Choices.js :", error);
        }
    },

    _attachSkillRemoteSearch: function (select, instance) {
        const minChars = 2;
        const endpoint = '/dossier/skills/search';
        const skillTypeId = parseInt(select.dataset.category); // We get the category of skills from the select attribute 'data-category'
        const token = this.el.querySelector('input[name="token"]')?.value || "";


        // Start with empty choices for product select
        instance.clearChoices();

        const inputEl = instance.input && instance.input.element;
        if (!inputEl) {
            console.warn('No search input found for product select', select);
            return;
        }

        let searchTimeout = null;

        inputEl.addEventListener('input', function () {
            const term = this.value.trim();

            if (term.length < minChars) {
                instance.clearChoices();
                return;
            }

            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(function () {
                $.ajax({
                    url: endpoint,
                    type: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({ token, q: term, limit: 40, skill_type_id: skillTypeId }),
                    success: function (response) {
                        const data = response.result || response;

                        if (!Array.isArray(data)) {
                            console.error('Unexpected response format:', data);
                            instance.clearChoices();
                            return;
                        }

                        instance.clearChoices();
                        const choices = data.map(p => ({
                            value: String(p.id),
                            label: p.name,
                            selected: false,
                        }));
                        instance.setChoices(choices, 'value', 'label', true);
                    },
                    error: function (xhr) {
                        console.error('Erreur skills:', xhr.responseText || xhr.statusText);
                        instance.clearChoices();
                    },
                });
            }, 250);
        });

        select.addEventListener('showDropdown', function () {
            const term = (inputEl.value || '').trim();
            if (term.length < minChars) {
                instance.clearChoices();
            }
        });
    },

    _initChoicesAll: function (rootEl = this.el) {
        rootEl.querySelectorAll('select:not(.choices-initialized)').forEach(select => {
            const isSkillSelect = select.classList.contains('skill-select');

            const instance = new Choices(select, {
                searchEnabled: true,
                itemSelectText: '',
                shouldSort: false,
                searchResultLimit: -1,
                renderChoiceLimit: -1,
                fuseOptions: { threshold: 0.3 , ignoreDiacritics: true },
                noResultsText: 'Chercher...',
                noChoicesText: 'Aucun choix disponible',
                placeholderValue: select.getAttribute("placeholder") || 'Sélectionner...',
            });

            // Only skill selects get the remote min-chars search
            if (isSkillSelect) {
                this._attachSkillRemoteSearch(select, instance);
            }
            select.choicesInstance = instance;
            select.classList.add("choices-initialized");
        });
        
    },

    _destroyChoicesAll: function (rootEl) {
        rootEl.querySelectorAll('select.choices-initialized').forEach(select => {
            if (select.choicesInstance) {
                select.choicesInstance.destroy();
                delete select.choicesInstance;
            }
            select.classList.remove("choices-initialized");
        });
    },


    _reindexCompetencyLines: function (sectionEl, scope) {
        const lines = sectionEl.querySelectorAll(".competency_line");

        lines.forEach((row, idx) => {
            const skillSelect = row.querySelector(".skill-select");
            const levelSelect = row.querySelector(".level-select");

            if (skillSelect) {
                skillSelect.name = `${scope}_skill_id_${idx}`;
                skillSelect.dataset.index = idx;
            }
            if (levelSelect) {
                levelSelect.name = `${scope}_skill_level_${idx}`;
                levelSelect.dataset.index = idx;
            }

            row.dataset.index = idx;
        });

        // keep add-index consistent
        sectionEl.dataset.nextIndex = String(lines.length);
    },


    _reindexRepeatLines: function (sectionEl) {
        const lines = sectionEl.querySelectorAll(".repeat-line");

        lines.forEach((row, newIndex) => {
            row.querySelectorAll("input, select, textarea").forEach((el) => {
                if (!el.name) return;
                el.name = el.name.replace(/_\d+$/, "_" + newIndex); // not just _0
                el.dataset.index = newIndex;
            });
            row.dataset.index = newIndex;
        });
    },

    _reindexExperiences: function (sectionEl) {
        const blocks = sectionEl.querySelectorAll(".experience-block");

        blocks.forEach((block, expIndex) => {
            block.dataset.index = expIndex;

            // rename fields ending with _<digits> => _expIndex
            block.querySelectorAll("[name]").forEach((el) => {
                if (!el.name) return;

                if (/^experiences_[a-z_]+_\d+$/.test(el.name)) {
                    el.name = el.name.replace(/_\d+$/, "_" + expIndex);
                }
            });

            // update nested competency scopes + ALSO rename their input names
            block.querySelectorAll(".competency-section").forEach((sec) => {
                const newScope = (sec.dataset.scope || "").replace(/^experiences_\d+_/, `experiences_${expIndex}_`);
                sec.dataset.scope = newScope;

                // rename skill + level names inside this competency section based on newScope
                const lines = sec.querySelectorAll(".competency_line");
                lines.forEach((line, lineIdx) => {
                    const skill = line.querySelector(".skill-select");
                    const level = line.querySelector(".level-select");

                    if (skill) skill.name = `${newScope}_skill_id_${lineIdx}`;
                    if (level) level.name = `${newScope}_skill_level_${lineIdx}`;
                });

                // keep section counter consistent
                sec.dataset.nextIndex = String(lines.length);
            });

        });

        // keep nextIndex aligned with count
        sectionEl.dataset.nextIndex = String(blocks.length);
    },

    _updateExperienceTitles: function(sectionEl) {
        sectionEl.querySelectorAll(".experience-block").forEach((block, i) => {
            const title = block.querySelector(".experience-title");
            if (title) title.textContent = `Projet ${i + 1}`;
        });
    },


    _bindEvents: function () {
        // ----------------------------
        // A) COMPETENCY: Add line
        // ----------------------------
        this.el.addEventListener("click", (e) => {
            const addBtn = e.target.closest(".add-competency-line");
            if (!addBtn) return;

            const sectionEl = addBtn.closest(".competency-section");
            if (!sectionEl) return;

            const scope = sectionEl.dataset.scope;
            const linesContainer = sectionEl.querySelector(".competency-lines");
            const firstLine = linesContainer?.querySelector(".competency_line");
            if (!linesContainer || !firstLine) return;
            
            let nextIndex = parseInt(sectionEl.dataset.nextIndex || "1", 10);
            
            // 1) Destroy Choices temporarily on the template line
            this._destroyChoicesAll(firstLine);
            
            // 2) Clone
            const newLine = firstLine.cloneNode(true);

            // 3) Restore Choices on original line
            this._initChoicesAll(firstLine);

            // 4) Remove old Choices DOM in clone
            newLine.querySelectorAll(".choices").forEach(el => el.remove());

            // 5) Reset + rename fields in clone
            const skillSelect = newLine.querySelector(".skill-select");
            const levelSelect = newLine.querySelector(".level-select");
            if (!skillSelect || !levelSelect) return;

            // Skill
            skillSelect.name = `${scope}_skill_id_${nextIndex}`;
            skillSelect.dataset.index = nextIndex;
            skillSelect.value = "";
            skillSelect.innerHTML = '<option value="" disabled="true" selected="true">Choisir une compétence</option>';
            skillSelect.classList.remove("choices-initialized");
            delete skillSelect.choicesInstance;

            // Level
            levelSelect.name = `${scope}_skill_level_${nextIndex}`;
            levelSelect.dataset.index = nextIndex;
            levelSelect.innerHTML = '<option value="" disabled="true" selected="true">Choisir un niveau</option>';
            levelSelect.setAttribute("disabled", "disabled");
            levelSelect.classList.remove("choices-initialized");
            delete levelSelect.choicesInstance;

            // 6) Append inside this competency section only
            linesContainer.appendChild(newLine);

            // 7) Init Choices in cloned line
            this._initChoicesAll(newLine);
            
            // 8) Increment section counter
            sectionEl.dataset.nextIndex = String(nextIndex + 1);
        });

        // ----------------------------
        // B) COMPETENCY: Remove line (scoped) + REINDEX
        // ----------------------------
        this.el.addEventListener("click", (e) => {
            const rmBtn = e.target.closest(".competency-section .remove-line");
            if (!rmBtn) return;

            const sectionEl = rmBtn.closest(".competency-section");
            const lineEl = rmBtn.closest(".competency_line");
            if (!sectionEl || !lineEl) return;

            const lines = sectionEl.querySelectorAll(".competency_line");
            const scope = sectionEl.dataset.scope; // e.g. "materials" or "experiences_0_logiciels"

            // ✅ DEBUG: confirm we're catching the right section
            console.log("REMOVE clicked scope=", scope);

            if (lines.length <= 1) {
                alert("Vous devez avoir au moins une compétence.");
                return;
            }

            // destroy Choices on this line to avoid leaks
            this._destroyChoicesAll(lineEl);

            lineEl.remove();

            // ✅ reindex remaining lines so you don't get _0 _2 _3
            this._reindexCompetencyLines(sectionEl, scope);
        });

        // ----------------------------
        // C) COMPETENCY: Skill change => fetch levels (scoped to the same line)
        // ----------------------------
        this.el.addEventListener("change", (e) => {
            const skillSelect = e.target.closest(".competency-section .skill-select");
            if (!skillSelect) return;

            const skillId = skillSelect.value;
            const lineEl = skillSelect.closest(".competency_line");
            if (!lineEl) return;

            const levelEl = lineEl.querySelector(".level-select");
            if (!levelEl || !levelEl.choicesInstance) return;

            const instance = levelEl.choicesInstance;

            // Reset + disable while loading
            instance.clearStore();
            instance.setChoices(
                [{ value: "", label: "Choisir un niveau", disabled: true, selected: true }],
                "value",
                "label",
                true
            );
            levelEl.setAttribute("disabled", "disabled");
            if (instance.disable) instance.disable();

            // If empty: make level not required, clear + disable
            if (!skillId) {
                levelEl.required = false;
                if (levelEl.choicesInstance) {
                    const inst = levelEl.choicesInstance;
                    inst.clearStore();
                    inst.setChoices(
                        [{ value: "", label: "Choisir un niveau", disabled: true, selected: true }],
                        "value",
                        "label",
                        true
                    );
                    if (inst.disable) inst.disable();
                }
                return;
            }

            // If skill selected: require level (after levels are loaded)
            levelEl.required = true;

            const token = this.el.querySelector('input[name="token"]')?.value || "";

            $.ajax({
                url: "/dossier/get-levels",
                type: "POST",
                contentType: "application/json",
                dataType: "json",
                data: JSON.stringify({
                    token: token,
                    skill_id: skillId,
                }),
                success: function (response) {
                    const levels = response?.levels || [];
                    if (!levels.length) return;

                    const choices = levels.map(l => ({ value: l.id, label: l.name }));
                    instance.setChoices(choices, "value", "label", true);

                    // Enable
                    levelEl.removeAttribute("disabled");
                    if (instance.enable) instance.enable();
                },
                error: function (xhr) {
                    console.error("get-levels failed:", xhr.status, xhr.responseText);
                    alert("Erreur lors du chargement des niveaux.");
                }
            });
        });

        // ============================
        // REPEAT SECTIONS (formations / habilitations / langues)
        // ============================

        // ----------------------------
        // D) REPEAT: Add line (generic)
        // ----------------------------
        this.el.addEventListener("click", (e) => {
            const addBtn = e.target.closest(".add-repeat-line");
            if (!addBtn) return;

            const sectionEl = addBtn.closest(".repeat-section");
            if (!sectionEl) return;

            const container = sectionEl.querySelector(".repeat-lines");
            const firstLine = container?.querySelector(".repeat-line");
            if (!container || !firstLine) return;

            let nextIndex = parseInt(sectionEl.dataset.nextIndex || "0", 10);

            const newLine = firstLine.cloneNode(true);
            
            // ✅ set line index
            newLine.dataset.index = String(nextIndex);
            
            // Update names + reset values in cloned line
            newLine.querySelectorAll("input, select, textarea").forEach((el) => {
                if (el.name) {
                    // replace trailing _0 with _{nextIndex}
                    el.name = el.name.replace(/_\d+$/, "_" + nextIndex);
                }
                el.dataset.index = nextIndex;

                if (el.tagName === "SELECT") {
                    el.selectedIndex = 0;
                } else {
                    el.value = "";
                }
            });

            container.appendChild(newLine);
            sectionEl.dataset.nextIndex = String(nextIndex + 1);
        });

        // ----------------------------
        // E) REPEAT: Remove line (scoped) + REINDEX
        // ----------------------------
        this.el.addEventListener("click", (e) => {
            const rmBtn = e.target.closest(".repeat-section .remove-line");
            if (!rmBtn) return;

            const sectionEl = rmBtn.closest(".repeat-section");
            const lineEl = rmBtn.closest(".repeat-line");
            if (!sectionEl || !lineEl) return;

            const lines = sectionEl.querySelectorAll(".repeat-line");
            if (lines.length <= 1) {
                alert("Vous devez garder au moins une ligne.");
                return;
            }

            lineEl.remove();

            // ✅ reindex remaining repeat lines (_0,_1,_2,...)
            this._reindexRepeatLines(sectionEl);

            // ✅ keep nextIndex in sync
            sectionEl.dataset.nextIndex = String(sectionEl.querySelectorAll(".repeat-line").length);
        });


        // ----------------------------
        // X) EXPERIENCES: Add experience
        // ----------------------------
        this.el.addEventListener("click", (e) => {
            const addBtn = e.target.closest(".add-experience-line");
            if (!addBtn) return;

            const sectionEl = addBtn.closest(".experiences-section");
            if (!sectionEl) return;

            const container = sectionEl.querySelector(".repeat-lines");
            const firstBlock = container?.querySelector(".experience-block");
            if (!container || !firstBlock) return;

            let nextIndex = parseInt(sectionEl.dataset.nextIndex || "1", 10);

            // destroy choices in template before clone (avoid cloning Choices DOM)
            this._destroyChoicesAll(firstBlock);

            const newBlock = firstBlock.cloneNode(true);

            // restore choices in template
            this._initChoicesAll(firstBlock);

            // remove any leftover Choices DOM in clone
            newBlock.querySelectorAll(".choices").forEach(el => el.remove());
            newBlock.querySelectorAll("select").forEach(sel => {
                sel.classList.remove("choices-initialized");
                delete sel.choicesInstance;
            });

            // 1) rename all names ending with _<digits> inside the block
            newBlock.querySelectorAll("[name]").forEach((el) => {
                if (!el.name) return;

                // Rename only experience-level fields: experiences_xxx_<n>
                // Excludes env-tech skills because they are experiences_<n>_<cat>_skill_..._<line>
                if (/^experiences_[a-z_]+_\d+$/.test(el.name)) {
                    el.name = el.name.replace(/_\d+$/, "_" + nextIndex);
                }
            });
            newBlock.querySelectorAll("[id]").forEach((el) => {
                if (!el.id) return;

                if (/^experiences_[a-z_]+_\d+$/.test(el.id)) {
                    el.id = el.id.replace(/_\d+$/, "_" + nextIndex);
                }
            });
            // rename data-target="experiences_xxx_<n>" (needed for contenteditable sync)
            newBlock.querySelectorAll("[data-target]").forEach((el) => {
                const t = el.getAttribute("data-target");
                if (!t) return;

                if (/^experiences_[a-z_]+_\d+$/.test(t)) {
                    el.setAttribute("data-target", t.replace(/_\d+$/, "_" + nextIndex));
                }
            });
            // rename label for="experiences_xxx_<n>"
            newBlock.querySelectorAll("label[for]").forEach((lb) => {
                const f = lb.getAttribute("for");
                if (!f) return;

                if (/^experiences_[a-z_]+_\d+$/.test(f)) {
                    lb.setAttribute("for", f.replace(/_\d+$/, "_" + nextIndex));
                }
            });

            // 2) update experience index in nested competency scopes: experiences_0_* -> experiences_<nextIndex>_*
            newBlock.querySelectorAll(".competency-section").forEach((sec) => {
                const scope = sec.dataset.scope || "";
                sec.dataset.scope = scope.replace(/^experiences_\d+_/, `experiences_${nextIndex}_`);

                sec.dataset.nextIndex = "1";
            });

            // 3) reset values
            newBlock.querySelectorAll("input, textarea, select, option, [contenteditable]").forEach((el) => {
                if (el.tagName === "SELECT") {
                    el.selectedIndex = 0;
                }else if (el.hasAttribute("contenteditable")) {
                    el.innerHTML = "";
                } else {
                    el.value = "";
                }
                el.dataset.index = nextIndex;
            });

            // 4) reset competency-lines to ONLY ONE line per section (optional but recommended)
            newBlock.querySelectorAll(".competency-section").forEach((sec) => {
                const scope = sec.dataset.scope; // experiences_<nextIndex>_<category>

                const linesContainer = sec.querySelector(".competency-lines");
                if (!linesContainer) return;

                const firstLine = linesContainer.querySelector(".competency_line");
                if (!firstLine) return;

                // Keep only the first line
                linesContainer.querySelectorAll(".competency_line").forEach((l, i) => {
                    if (i > 0) l.remove();
                });

                const skillSelect = firstLine.querySelector(".skill-select");
                const levelSelect = firstLine.querySelector(".level-select");

                // Force correct names for line index 0
                if (skillSelect) {
                    skillSelect.name = `${scope}_skill_id_0`;
                    skillSelect.innerHTML = '<option value="" disabled="true" selected="true">Choisir une compétence</option>'
                    skillSelect.value = "";
                    skillSelect.classList.remove("choices-initialized");
                    delete skillSelect.choicesInstance;
                }

                if (levelSelect) {
                    levelSelect.name = `${scope}_skill_level_0`;
                    levelSelect.innerHTML = '<option value="" disabled="true" selected="true">Choisir un niveau</option>';
                    levelSelect.setAttribute("disabled", "disabled");
                    levelSelect.classList.remove("choices-initialized");
                    delete levelSelect.choicesInstance;
                }

                // Remove any .choices UI inside the line (just in case)
                firstLine.querySelectorAll(".choices").forEach(el => el.remove());
            });

            // set block index
            newBlock.dataset.index = nextIndex;

            container.appendChild(newBlock);
            // init choices in the new block
            this._initChoicesAll(newBlock);
            this._updateExperienceTitles(sectionEl);

            // bump nextIndex
            sectionEl.dataset.nextIndex = String(nextIndex + 1);
            
        });

        // ----------------------------
        // Y) EXPERIENCES: Remove experience + reindex
        // ----------------------------
        this.el.addEventListener("click", (e) => {
            const rmBtn = e.target.closest(".remove-experience");
            if (!rmBtn) return;

            const sectionEl = rmBtn.closest(".experiences-section");
            const blockEl = rmBtn.closest(".experience-block");
            if (!sectionEl || !blockEl) return;

            const blocks = sectionEl.querySelectorAll(".experience-block");
            if (blocks.length <= 1) {
                alert("Vous devez garder au moins une expérience.");
                return;
            }

            this._destroyChoicesAll(blockEl);
            blockEl.remove();

            this._reindexExperiences(sectionEl);
            this._updateExperienceTitles(sectionEl);
        });


    }
});

function syncContenteditablesToTextareas(root) {
    const scope = root || document;

    scope.querySelectorAll(".exp-html-editor[contenteditable]").forEach((ed) => {
        const target = ed.dataset.target;
        console.log("[SYNC] editor target=", target, "text=", ed.textContent);

        const ta = scope.querySelector(`textarea[name="${CSS.escape(target || '')}"]`);
        if (!ta) {
            console.warn("[SYNC] missing textarea for", target, ed);
            return;
        }

        ta.value = (ed.textContent || "").replace(/\u00A0/g, " ").trim();
    });
}


$(document).ready(function () {
    $('#dossier_form').on('submit', function (e) {
        e.preventDefault();

        const form = this;

        // sync editors immediately
        syncContenteditablesToTextareas(form);

        console.log('Waiting 30 seconds before submitting…');

        setTimeout(function () {
            let $form = $(form);
            let url = $form.attr('action');
            let data = $form.serialize();

            $.ajax({
                url: url,
                type: 'POST',
                data: data,
                success: function (response) {
                    if (response && response.redirect) {
                        window.location.href = response.redirect;
                        return;
                    }
                    $('#controle-message')
                        .removeClass('d-none')
                        .text('Formulaire soumis avec succès.');
                },
                error: function () {
                    alert("Une erreur s'est produite : ");
                }
            });

        }, 30000); // ⏱ 30 seconds
    });
});

