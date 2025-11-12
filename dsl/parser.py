import yaml
from typing import List, Union
from dsl.schema import DSLAction


def load_dsl_from_yaml(path: str) -> List[DSLAction]:
    """Load DSL plan from a YAML file."""
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    return [DSLAction(**step) for step in data]


def load_dsl_from_dict(data: Union[list, DSLAction]) -> List[DSLAction]:
    """
    Load DSL plan directly from a Python list of dicts or DSLAction objects.
    Ensures robustness when the planner already returns DSLAction instances.
    """
    actions = []
    for step in data:
        if isinstance(step, DSLAction):
            # Already parsed
            actions.append(step)
        elif isinstance(step, dict):
            actions.append(DSLAction(**step))
        else:
            raise TypeError(f"Unexpected step type in DSL plan: {type(step)}")
    return actions
