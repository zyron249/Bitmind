from ..core import models


def compute_consensus_for_task(task_id: str):
    # Gather submissions
    submissions = [s for s in models.InMemoryDB.submissions.values() if s.assignment.task_id == task_id]
    if not submissions:
        return {"consensus_score": 0.0, "consensus_pass": False, "count": 0}
    # count verdict ok
    ok_subs = [s for s in submissions if s.verdict == "ok"]
    # consensus_score: average final_score across submissions
    avg_score = sum(s.final_score for s in submissions) / len(submissions)
    # consensus_pass: majority of submissions are ok (>=50%)
    consensus_pass = len(ok_subs) / len(submissions) >= 0.5
    return {"consensus_score": avg_score, "consensus_pass": consensus_pass, "count": len(submissions)}
