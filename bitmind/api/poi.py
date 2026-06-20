@@
     else:
         # apply reputation weighting
         rep = req.reputation_score if req.reputation_score is not None else user.reputation
-        submission.final_score = submission.auto_score * (0.5 + 0.5 * rep)
+        submission.final_score = submission.auto_score * (0.5 + 0.5 * rep)
+        # Cap final score to 100.0
+        submission.final_score = min(submission.final_score, 100.0)
         submission.verdict = "ok"
         decision_reason = "scored"
@@
 def evaluate_submission(submission_id: str):
@@
-        # weight: final = auto_score * (0.5 + 0.5*rep)
-        submission.final_score = auto_score * (0.5 + 0.5 * rep)
+        # weight: final = auto_score * (0.5 + 0.5*rep)
+        submission.final_score = auto_score * (0.5 + 0.5 * rep)
+        # Cap final score
+        submission.final_score = min(submission.final_score, 100.0)
         submission.verdict = "ok"
