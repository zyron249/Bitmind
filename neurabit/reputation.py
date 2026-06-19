class ReputationEngine:

    def __init__(self):

        self.users = {}

    def get(
        self,
        user
    ):

        return self.users.get(
            user,
            0.5
        )

    def increase(
        self,
        user
    ):

        self.users[user] = min(
            1.0,
            self.get(user) + 0.02
        )

    def decrease(
        self,
        user
    ):

        self.users[user] = max(
            0,
            self.get(user) - 0.05
        )
