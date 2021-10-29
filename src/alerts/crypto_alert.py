from clients.coinbase_client import CoinbaseClient


class TimeWindowNotSupportedException(ValueError):
    pass


class CryptoAlert:
    """
    This is the core class to generate a script for a specific user to monitor a certain currency-crypto pair,
    and to send alert emails to that user if the up/drop rate in a defined amount of time has surpassed the threshold.
    """
    def __init__(self, username: str, crypto: str, currency: str, time_window: int, threshold: int) -> None:
        """
        :param int time_window: The specific amount of time (minute) the user wants to monitor. We only support time
        window <= 720 mins (12 h)

        :param int threshold: The up/drop percentage threshold of a currency-crypto pair in the time window that the
        user wants to get alarmed.
        """
        self.username = username
        self.crypto = crypto
        self.currency = currency
        self.client = CoinbaseClient(self.username)

        if time_window > 720 or time_window < 1:
            self.client.email_client.reconstruct_email(
                subject="Invalid time window value!",
                content="This time window is currently not supported. Please choose a value between 1 min and 720 min."
            )
            raise TimeWindowNotSupportedException(
                "Invalid time window value"
            )
        else:
            self.time_window = time_window

        self.threshold = threshold
        self.cache = {}

    def __str__(self) -> str:
        return "This is the crypto alert system configured for user: {}".format(self.username)

    def __call__(self, *args, **kwargs):
        pass

    def _core_algorithm(self):
        pass


if __name__ == "__main__":
    alert_system = CryptoAlert(
        username="mtgtsunami@yahoo.com",
        crypto="BTC",
        currency="USD",
        time_window=10,
        threshold=1
    )
    alert_system()
