import { registry } from "@web/core/registry";

import { hierarchyView } from "@web_hierarchy/hierarchy_view";
import { OkrHierarchyRenderer } from "./okr_node_hierarchy_renderer";

export const okrHierarchyView = {
    ...hierarchyView,
    Renderer: OkrHierarchyRenderer,
};

registry.category("views").add("okr_node_hierarchy", okrHierarchyView);
