class AntiCheat:

    def check(
        self,
        answer,
        reputation
    ):

        risk = 0.1

        if len(answer) < 15:
            risk += 0.6

        if reputation < 0.3:
            risk += 0.2

        return min(
            1.0,
            risk
        )
