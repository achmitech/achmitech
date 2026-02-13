/** @odoo-module **/

import { WebsiteForumWysiwyg } from "@website_forum/components/website_forum_wysiwyg/website_forum_wysiwyg";
import { DOSSIER_PLUGINS } from "./dossier_plugin_set";

export class DossierWysiwyg extends WebsiteForumWysiwyg {
    getEditorConfig() {
        const cfg = super.getEditorConfig();
        cfg.Plugins = DOSSIER_PLUGINS;

        // Extra safety: forbid image dropping even if something slips in
        // cfg.dropImageAsAttachment = false;
        // cfg.allowImageResize = false;
        // cfg.allowImageTransform = false;

        return cfg;
    }
}