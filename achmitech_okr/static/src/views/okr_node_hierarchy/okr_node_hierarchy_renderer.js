import { HierarchyRenderer } from "@web_hierarchy/hierarchy_renderer";
import { OkrHierarchyCard } from "./okr_node_hierarchy_card";
export class OkrHierarchyRenderer extends HierarchyRenderer {
    static components = {
        ...HierarchyRenderer.components,
        HierarchyCard: OkrHierarchyCard,
    };
}
