class ProofOfIntelligence:

    def score(
        self,
        answer,
        expected
    ):

        if len(answer) < 20:
            return 0.0

        if answer == expected:
            return 1.0

        return 0.75
