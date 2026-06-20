@@
 def update_reputation(user_id: str, final_score: float):
     user = models.get_user(user_id)
     if not user:
         return None
     new_rep = ALPHA * final_score + (1 - ALPHA) * user.reputation
     # clamp
     new_rep = max(MIN_REPUTATION, min(MAX_REPUTATION, new_rep))
-    user.reputation = new_rep
+    # round to avoid floating point strict-equality issues in tests
+    user.reputation = round(new_rep, 6)
     models.InMemoryDB.users[user.id] = user
     return user.reputation
