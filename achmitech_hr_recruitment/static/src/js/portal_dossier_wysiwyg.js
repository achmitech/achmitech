/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { DossierWysiwyg } from "./dossier_wysiwyg";

function ensureWrapper(textareaEl) {
    let wrapper = textareaEl.closest(".o_wysiwyg_textarea_wrapper");
    if (wrapper) return wrapper;
    wrapper = document.createElement("div");
    wrapper.className = "position-relative o_wysiwyg_textarea_wrapper";
    textareaEl.parentNode.insertBefore(wrapper, textareaEl);
    wrapper.appendChild(textareaEl);
    return wrapper;
}

export class PortalDossierWysiwyg extends Interaction {
    static selector = ".portal_dossier";
    

    setup() {
        this.el
            .querySelectorAll("textarea.o_wysiwyg_loader")
            .forEach((textareaEl) => {

                // ✅ ALWAYS ensure wrapper (no forum dependency)
                const wysiwygWrapper = ensureWrapper(textareaEl);

                // Move textarea back after wrapper (same as forum logic)
                textareaEl.style.display = "none";
                wysiwygWrapper.after(textareaEl);
                wysiwygWrapper.replaceChildren();

                const props = {
                    textareaEl,
                    fullEdit: true,
                    getRecordInfo: () => ({
                        context: this.services.website_page?.context || {},
                        resModel: "hr.applicant", // or your real model
                        resId: 0,
                    }),
                };

                // ✅ Mount YOUR restricted editor
                this.mountComponent(wysiwygWrapper, DossierWysiwyg, props);
            });
    }
}

registry
  .category("public.interactions")
  .add("achmitech_hr_recruitment.portal_dossier_wysiwyg", PortalDossierWysiwyg);