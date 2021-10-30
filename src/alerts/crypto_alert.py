from time import sleep

from clients.coinbase_client import CoinbaseClient


class InputValueNotSupportedException(ValueError):
    pass


class MarketTypeNotAvailableException(Exception):
    pass


class CryptoNotAvailableException(Exception):
    pass


class CurrencyNotAvailableException(Exception):
    pass


class CryptoDuplicateException(Exception):
    pass


class CurrencyDuplicateException(Exception):
    pass


class CryptoAlert:
    """
    This is the core class to generate a script for a specific user to monitor a certain currency-crypto pair,
    and to send alert emails to that user if the up/down rate in a defined amount of time has surpassed the threshold.
    """
    DEFAULT_CACHE_SIZE = 720

    def __init__(self, username: str, crypto: str, currency: str, market_type: str, time_window: int, threshold: float):
        """
        :param int time_window: The specific amount of time (minute) the user wants to monitor. We only support time
        window <= 720 mins (12 h)

        :param int threshold: The up/down percentage (100 * actual percentage) threshold of a currency-crypto pair in
        the time window that the user wants to get alarmed.
        """
        self.username = username
        self.crypto = crypto
        self.currency = currency
        self.market_type = market_type
        self.time_window = time_window
        self.threshold = threshold
        self.client = CoinbaseClient(self.username)
        self._validate_input()

        # I/O is too slow for storing server time and the corresponding crypto price when the accuracy
        # is of the time window is set to around 1 min (60s), thus using memory cache instead.
        self.cache = {}
        for i in range(CryptoAlert.DEFAULT_CACHE_SIZE):
            self.cache[i] = {}

    def __str__(self) -> str:
        return "This is the crypto alert system configured for user: {}".format(self.username)

    def __call__(self, *args, **kwargs):
        self._core_algorithm()

    def _validate_input(self) -> None:
        if self.market_type not in self.client.market_type_list:
            self.client.email_client.reconstruct_email(
                subject="The market type you chose is not in the available type list! Service failed to start!",
                content="Please choose a market type among: {} \n".format(CoinbaseClient.MARKET_TYPE_LIST)
            )
            self.client.email_client.send_email()
            raise MarketTypeNotAvailableException(
                "The market type you chose is not in the available type list!"
            )

        # According to the response body from Coinbase API: https://developers.coinbase.com/api/v2#prices
        # the order of the currency pair should only be crypto-currency.
        # Setting Currency-crypto pair, currency-currency pair, crypto-crypto pair
        # in the request URL will get a non 200 response.
        is_crypto_in_currency_list = False
        if self.crypto not in self.client.crypto_list:
            if self.crypto not in self.client.currency_list:
                self.client.email_client.reconstruct_email(
                    subject="The crypto you chose is not in the available crypto list! Service failed to start!",
                    content="Please choose a crypto among: {} \n".format(self.client.crypto_list)
                )
                self.client.email_client.send_email()
                raise CryptoNotAvailableException(
                    "The crypto you chose is not in the available crypto list!"
                )
            else:
                # The crypto has been falsely regarded as a currency.
                is_crypto_in_currency_list = True

        is_currency_in_crypto_list = False
        if self.currency not in self.client.currency_list:
            if self.currency not in self.client.crypto_list:
                self.client.email_client.reconstruct_email(
                    subject="The currency you chose is not in the available currency list! Service failed to start!",
                    content="Please choose a currency among: {} \n".format(self.client.currency_list)
                )
                self.client.email_client.send_email()
                raise CurrencyNotAvailableException(
                    "The currency you chose is not in the available currency list!"
                )
            else:
                # The currency has been falsely regarded as a crypto.
                is_currency_in_crypto_list = True

        # Both crypto and currency inputs are both in supported crypto list.
        if self.crypto in self.client.crypto_list and self.currency in self.client.crypto_list:
            self.client.email_client.reconstruct_email(
                subject="The currency and crypto you chose are both in the available crypto list! " +
                        "Service failed to start!",
                content="Please choose a currency among: {} \n".format(self.client.currency_list) +
                        "And a crypto among: {} \n".format(self.client.crypto_list)
            )
            self.client.email_client.send_email()
            raise CryptoDuplicateException(
                "The currency and crypto you chose are both in the available crypto list!"
            )

        # Both crypto and currency inputs are both in supported currency list.
        if self.crypto in self.client.currency_list and self.currency in self.client.currency_list:
            self.client.email_client.reconstruct_email(
                subject="The currency and crypto you chose are both in the available currency list! " +
                        "Service failed to start!",
                content="Please choose a currency among: {} \n".format(self.client.currency_list) +
                        "And a crypto among: {} \n".format(self.client.crypto_list)
            )
            self.client.email_client.send_email()
            raise CurrencyDuplicateException(
                "The currency and crypto you chose are both in the available currency list!"
            )

        # Time window value check
        if self.time_window > CryptoAlert.DEFAULT_CACHE_SIZE or self.time_window < 1:
            self.client.email_client.reconstruct_email(
                subject="Invalid time window value!",
                content="This time window {} min is currently not supported. Please choose a value between 1 min and "
                        "720 min.".format(self.time_window)
            )
            self.client.email_client.send_email()
            raise InputValueNotSupportedException(
                "Invalid time window value!"
            )

        # Threshold value check
        if self.threshold <= 0:
            self.client.email_client.reconstruct_email(
                subject="Invalid threshold value!",
                content="This threshold {} percent cannot be less or equal to 0".format(self.threshold)
            )
            self.client.email_client.send_email()
            raise InputValueNotSupportedException(
                "Invalid threshold value!"
            )

        if is_crypto_in_currency_list and is_currency_in_crypto_list:
            self.crypto, self.currency = self.currency, self.crypto

    def _core_algorithm(self):
        while True:
            for i in range(CryptoAlert.DEFAULT_CACHE_SIZE):
                price = self.client.get_crypto_price(self.crypto, self.currency, self.market_type)
                time = self.client.get_server_time_in_local_timezone()

                target_index = i - self.time_window
                if target_index < 0:
                    target_index = i + CryptoAlert.DEFAULT_CACHE_SIZE - self.time_window
                last_data = self.cache[target_index]
                self.cache[i] = {"price": price, "time": time}

                # Cache is not full (first 720 min after the alert system starts)
                if not last_data:
                    print(self.cache)
                    sleep(60)
                    continue
                else:
                    # If the price of the chosen crypto is up in the defined time window.
                    price_diff = price - last_data["price"]
                    is_up = False if price_diff <= 0 else True
                    percentage = abs(price_diff) / last_data["price"] * 100
                    if percentage >= self.threshold:
                        self.client.email_client.reconstruct_email(
                            subject="{}!!! {} price in {} was going {} in the last {} minutes".format(
                                "Great News" if is_up else "Bad News",
                                self.crypto,
                                self.currency,
                                "up" if is_up else "down",
                                self.time_window
                            ),
                            content="Attention! {} price was going {} {} percent from {} {} to {} {},".format(
                                self.crypto,
                                "up" if is_up else "down",
                                percentage,
                                last_data["price"],
                                self.currency,
                                price,
                                self.currency
                            ) + "from {} to {}, breaking the threshold percentage of {}".format(
                                last_data["time"],
                                time,
                                self.threshold
                            )
                        )
                        self.client.email_client.send_email()

                print(self.cache)
                sleep(60)


if __name__ == "__main__":
    alert_system = CryptoAlert(
        username="mtgtsunami@yahoo.com",
        crypto="BTC",
        currency="USD",
        market_type="spot",
        time_window=15,
        threshold=0.2
    )
    alert_system()
