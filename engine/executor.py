from engine.graph import topological_sort


def run_workflow(steps: dict, registry: dict) -> dict:
    """
    steps: {"a": {"deps": [], "type": "add_one"}, "b": {"deps": ["a"], "type": "add_one"}}
    registry: maps a step's "type" to a function(inputs, config) -> output
    Returns a dict of step_id -> output
    """
    deps_only = {step_id: info["deps"] for step_id, info in steps.items()}
    order = topological_sort(deps_only)

    outputs = {}
    for step_id in order:
        step_info = steps[step_id]
        step_type = step_info["type"]
        func = registry[step_type]

        inputs = {dep: outputs[dep] for dep in step_info["deps"]}
        outputs[step_id] = func(inputs, step_info.get("config", {}))

    return outputs