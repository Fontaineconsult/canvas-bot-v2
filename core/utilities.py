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
