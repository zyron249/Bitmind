from ..core import anti_cheat


def ai_score(content: str, task):
    # Wrapper around anti_cheat.ai_score_submission for future replacement
    return anti_cheat.ai_score_submission(content, task)
