# dsl/parser.py
import yaml
from typing import List
from dsl.schema import DSLAction

def load_dsl_from_yaml(path: str) -> List[DSLAction]:
    """Load DSL plan from a YAML file."""
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    return [DSLAction(**step) for step in data]

def load_dsl_from_dict(data: list) -> List[DSLAction]:
    """Load DSL plan directly from a Python list of dicts."""
    return [DSLAction(**step) for step in data]
