from typing import List, Tuple


def build_path(node, ignore_root=False) -> List:

    """
    Build a list of the path from the node to the root node.
    :param node:
    :param ignore_root:
    :return:
    """

    path_list = list()

    def get_parent(node_):

        if hasattr(node_, "root_node"):

            if not ignore_root:
                pass
            else:
                path_list.append(node_)
        if not hasattr(node_, "root_node"):

            path_list.append(node_)
            get_parent(node_.parent)
    get_parent(node)
    return path_list


def is_hidden(node) -> bool:
    """Check if the node or any ancestor is hidden."""
    for node_ in build_path(node):
        if node_.__dict__.get("hidden_for_user") is True\
                or node_.__dict__.get('published') is False\
                or node_.__dict__.get("hide_from_students") is True \
                or node_.__dict__.get("locked") is True:
            return True
    return False


def get_hidden_reasons(node) -> str:
    """Return a comma-separated string of reasons the node is hidden, or empty string."""
    reasons = []
    for node_ in build_path(node):
        if node_.__dict__.get("hidden_for_user") is True:
            reasons.append("hidden_for_user")
        if node_.__dict__.get("published") is False:
            reasons.append("unpublished")
        if node_.__dict__.get("hide_from_students") is True:
            reasons.append("hidden_from_students")
        if node_.__dict__.get("locked") is True:
            reasons.append("locked")
    return ", ".join(reasons)


def get_visibility(manifest, node):
    """Aggregate is_hidden / hidden_reason across every manifest entry
    for `node.item_id`. Returns (is_hidden_bool, hidden_reason_str).

    Builds on the single-node primitives is_hidden() and
    get_hidden_reasons() above — this helper just walks each manifest
    occurrence and collapses the results.

    Semantics:
      - All refs share the same visibility state: return it as-is.
      - Refs differ: hidden_reason becomes "varies".
          * At least one ref visible: is_hidden=False (item is reachable
            from at least one published page; surface the inconsistency
            but keep the row in the active view).
          * All refs hidden but for different reasons: is_hidden=True.

    Falls back to single-node values when manifest is None or the
    node isn't tracked, so callers that haven't wired the manifest
    through still get a sensible result.
    """
    if manifest is None:
        return is_hidden(node), get_hidden_reasons(node)
    item_id = getattr(node, "item_id", None)
    if item_id is None:
        return is_hidden(node), get_hidden_reasons(node)
    nodes = manifest.manifest.get(item_id, [])
    if not nodes:
        return is_hidden(node), get_hidden_reasons(node)
    states = [(is_hidden(n), get_hidden_reasons(n)) for n in nodes]
    if len(set(states)) == 1:
        return states[0]
    if any(not h for h, _ in states):
        return False, "varies"
    return True, "varies"
