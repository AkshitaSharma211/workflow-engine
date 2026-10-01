def topological_sort(steps: dict) -> list:
    """
    steps: a dict like {"fetch": [], "filter": ["fetch"], "notify": ["filter"]}
    where each key is a step id, and the value is the list of step ids
    it depends on.

    Returns a list of step ids in an order where every step appears
    after everything it depends on.
    """
    order = []
    done = set()

    while len(order) < len(steps):
        progressed = False
        for step_id, deps in steps.items():
            if step_id in done:
                continue
            if all(dep in done for dep in deps):
                order.append(step_id)
                done.add(step_id)
                progressed = True
        if not progressed:
            raise ValueError("Cycle detected — no valid order exists")

    return order