class RewardEngine:

    def calculate(
        self,
        score,
        reputation,
        difficulty
    ):

        reward = (
            score
            * reputation
            * difficulty
            * 10
        )

        return round(
            reward,
            4
        )
