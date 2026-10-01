from engine.graph import topological_sort
import time
from engine.db import SessionLocal, Run, StepRun

def run_with_retry(func, inputs, config, max_attempts=3, base_delay=1):
    attempt = 1
    while attempt <= max_attempts:
        try:
            return func(inputs, config)
        except Exception as e:
            if attempt == max_attempts:
                raise
            wait = base_delay * (2 ** (attempt - 1))  # 1, 2, 4, ...
            print(f"Attempt {attempt} failed ({e}), retrying in {wait}s")
            time.sleep(wait)
            attempt += 1


def run_workflow(steps: dict, registry: dict) -> dict:
    deps_only = {step_id: info["deps"] for step_id, info in steps.items()}
    order = topological_sort(deps_only)

    session = SessionLocal()
    run = Run(status="running")
    session.add(run)
    session.commit()  # saves the row, and fills in run.id



    outputs = {}
    try:
        for step_id in order:
            step_info = steps[step_id]
            step_type = step_info["type"]
            func = registry[step_type]

            inputs = {dep: outputs[dep] for dep in step_info["deps"]}

            try:
                result = run_with_retry(func, inputs, step_info.get("config", {}))
                outputs[step_id] = result
                session.add(StepRun(run_id=run.id, step_id=step_id, status="success", output=str(result)))
            except Exception as e:
                session.add(StepRun(run_id=run.id, step_id=step_id, status="failed", output=str(e)))
                session.commit()
                run.status = "failed"
                session.commit()
                raise

        run.status = "success"
        session.commit()
    finally:
        session.close()

    
    
    return outputs