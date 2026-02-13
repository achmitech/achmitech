/** @odoo-module **/

import { CORE_PLUGINS } from "@html_editor/plugin_sets";
import { ListPlugin } from "@html_editor/main/list/list_plugin";
import { TabulationPlugin } from "@html_editor/main/tabulation_plugin";
import { HintPlugin } from "@html_editor/main/hint_plugin";
import { ColorPlugin } from "@html_editor/main/font/color_plugin";
import { PowerboxPlugin } from "@html_editor/main/powerbox/powerbox_plugin";
import { SearchPowerboxPlugin } from "@html_editor/main/powerbox/search_powerbox_plugin";
import { ToolbarPlugin } from "@html_editor/main/toolbar/toolbar_plugin";
import { ShortCutPlugin } from "@html_editor/core/shortcut_plugin";

// Optional: keep basic formatting like bold/italic (FormatPlugin is already in CORE_PLUGINS)
export const DOSSIER_PLUGINS = [
    ...CORE_PLUGINS,
    ColorPlugin,
    ListPlugin,
    TabulationPlugin,
    ToolbarPlugin,
    ShortCutPlugin,
    HintPlugin,
    PowerboxPlugin,
    SearchPowerboxPlugin
];
