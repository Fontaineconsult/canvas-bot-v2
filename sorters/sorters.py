import re
from config.read import read_re

expressions = read_re()


def re_combiner(re_list):

    raw_string = "|".join(re_list)
    return re.compile(raw_string, re.IGNORECASE)



resource_node_regex = re.compile(re_combiner(expressions["resource_node_types_re"]))