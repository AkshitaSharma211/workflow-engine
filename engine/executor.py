from engine.graph import topological_sort
import time
from engine.db import SessionLocal, Run, StepRun
import datetime

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

def _log_step(run_id, step_id, status, output):
    with SessionLocal() as s:
        s.add(StepRun(run_id=run_id, step_id=step_id, status=status, output=output[:2000]))
        s.commit()


def _set_run_status(run_id, status):
    with SessionLocal() as s:
        run = s.get(Run, run_id)
        run.status = status
        run.finished_at = datetime.datetime.utcnow()
        s.commit()


def run_workflow(steps: dict, registry: dict) -> dict:
    deps_only = {step_id: info["deps"] for step_id, info in steps.items()}
    order = topological_sort(deps_only)

    with SessionLocal() as s:
        run = Run(status="running")
        s.add(run)
        s.commit()
        run_id = run.id  # a plain number, safe to use after the session closes

    outputs = {}
    for step_id in order:
        step_info = steps[step_id]
        func = registry[step_info["type"]]
        inputs = {dep: outputs[dep] for dep in step_info["deps"]}

        try:
            result = run_with_retry(func, inputs, step_info.get("config", {}))
        except Exception as e:
            _log_step(run_id, step_id, "failed", str(e))
            _set_run_status(run_id, "failed")
            raise

        outputs[step_id] = result
        _log_step(run_id, step_id, "success", str(result))

    _set_run_status(run_id, "success")
    return outputs