import requests
from requests.exceptions import RequestException

from utils.emails import AlertEmail


class ResponseNoDataException(RequestException):
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


class CoinbaseClient:
    """
    This is the client for requesting data from Coinbase.
    """
    BACKUP_CURRENCY_LIST = {"USD", "EUR", "GBP", "CNY", "JPY", "CAD", "AUD", "RUB"}
    BACKUP_CRYPTO_LIST = {"BTC", "ETH", "USDT", "ADA", "DOGE", "AVAX", "DOT", "SHIB", "XTZ", "SOL", "ICP", "LTC"}
    MARKET_TYPE_LIST = {"buy", "sell", "spot"}

    def __init__(self, user_address="") -> None:
        self.user_address = user_address
        self.currency_list = self.get_available_currency_list()
        self.crypto_list = self.get_available_crypto_list()
        self.market_type_list = CoinbaseClient.MARKET_TYPE_LIST

        self.email_client = AlertEmail(
            receive_address=AlertEmail.DEFAULT_RECEIVING_ADDRESS if not self.user_address else self.user_address,
            subject=AlertEmail.DEFAULT_SUBJECT,
            content=AlertEmail.DEFAULT_CONTENT
        )

    def __str__(self) -> str:
        return "This is the coinbase client for user: {}".format(self.user_address)

    def get_available_currency_list(self) -> set:
        r = requests.get("https://api.coinbase.com/v2/currencies")
        if r.status_code != 200:
            self.email_client.reconstruct_email(
                subject="Failed to acquire the complete currency list from Coinbase!",
                content="We failed to obtain the full version of currency list supported by Coinbase. \n" +
                        "\n" +
                        "Fall back to use back up currency list: {} instead".format(
                            CoinbaseClient.BACKUP_CURRENCY_LIST
                        )
            )
            self.email_client.send_email()
            return CoinbaseClient.BACKUP_CURRENCY_LIST
        if "data" not in r.json() or len(r.json()["data"]) == 0:
            self.email_client.reconstruct_email(
                subject="Failed to acquire the complete currency list from Coinbase!",
                content="Coinbase get_currency_list API returns 200 but there's no data inside the response body. \n" +
                        "\n" +
                        "Fall back to use back up currency list: {} instead".format(
                            CoinbaseClient.BACKUP_CURRENCY_LIST
                        )
            )
            self.email_client.send_email()
            return CoinbaseClient.BACKUP_CURRENCY_LIST

        data = r.json().get("data")
        currency_list = set()
        for info in data:
            currency_list.add(info.get("id"))
        return currency_list

    def get_available_crypto_list(self) -> set:
        r = requests.get("https://api.coinbase.com/v2/exchange-rates")
        if r.status_code != 200:
            self.email_client.reconstruct_email(
                subject="Failed to acquire the complete crypto list from Coinbase!",
                content="We failed to obtain the full version of crypto list supported by Coinbase. \n" +
                        "\n" +
                        "Fall back to use back up crypto list: {} instead".format(
                            CoinbaseClient.BACKUP_CRYPTO_LIST
                        )
            )
            self.email_client.send_email()
            return CoinbaseClient.BACKUP_CRYPTO_LIST
        if "data" not in r.json() or "rates" not in r.json()["data"] or "currency" not in r.json()["data"]:
            self.email_client.reconstruct_email(
                subject="Failed to acquire the complete crypto list from Coinbase!",
                content="Coinbase get_exchange_rate API returns 200 but there's no data inside the response body. \n" +
                        "\n" +
                        "Fall back to use back up crypto list: {} instead".format(
                            CoinbaseClient.BACKUP_CRYPTO_LIST
                        )
            )
            self.email_client.send_email()
            return CoinbaseClient.BACKUP_CRYPTO_LIST

        # It's hard to determine the crypto list from exchange_rates list,
        # if the currency list is not in its full version.
        if self.currency_list == CoinbaseClient.BACKUP_CURRENCY_LIST:
            self.email_client.reconstruct_email(
                subject="Fall back to use back up crypto list due to failure in obtaining full version currency list.",
                content="It's impossible to parse the crypto list from exchange_rates API response, " +
                        "if the currency list is not in its full version. \n" +
                        "\n" +
                        "Fall back to use back up crypto list: {} instead".format(
                            CoinbaseClient.BACKUP_CRYPTO_LIST
                        )
            )
            self.email_client.send_email()
            return CoinbaseClient.BACKUP_CRYPTO_LIST

        data = r.json().get("data")
        crypto_list = set()
        for k in data.get("rates").keys():
            if k not in self.currency_list:
                crypto_list.add(k)
        return crypto_list

    def get_coinbase_server_time(self) -> (str, str):
        r = requests.get("https://api.coinbase.com/v2/time")
        if r.status_code != 200:
            error_body = r.json()
            self.email_client.reconstruct_email(
                subject="Coinbase get_server_time API has crashed! Service is down!",
                content="Error message from Coinbase API server: {} \n".format(error_body) +
                        "\n" +
                        "Please contact mtgtsunami@yahoo.com for further assistance."
            )
            self.email_client.send_email()
            raise RequestException(error_body)
        if "data" not in r.json() or "epoch" not in r.json()["data"]:
            self.email_client.reconstruct_email(
                subject="Coinbase get_server_time API returns null response! Service is down!",
                content="Coinbase get_server_time API returns 200 but there's no data inside the response body. \n" +
                        "\n" +
                        "Please contact mtgtsunami@yahoo.com for further assistance."
            )
            self.email_client.send_email()
            raise ResponseNoDataException(
                "There is no data in the response body."
            )

        data = r.json().get("data")
        return data.get("iso"), data.get("epoch")

    def get_crypto_price(self, crypto: str, currency: str, market_type: str) -> float:
        market_type = market_type.lower()
        need_swap = self.validate_input_for_getting_crypto_price(crypto, currency, market_type)
        if need_swap:
            crypto, currency = currency, crypto

        url = "https://api.coinbase.com/v2/prices/" + crypto + "-" + currency + "/" + market_type
        r = requests.get(url)
        if r.status_code != 200:
            error_body = r.json()
            self.email_client.reconstruct_email(
                subject="Coinbase get_crypto_price API has crashed! Service is down!",
                content="Error message from Coinbase API server: {} \n".format(error_body) +
                        "\n" +
                        "Please contact mtgtsunami@yahoo.com for further assistance."
            )
            self.email_client.send_email()
            raise RequestException(error_body)
        if "data" not in r.json() or "amount" not in r.json()["data"]:
            self.email_client.reconstruct_email(
                subject="Coinbase get_crypto_price API returns null response! Service is down!",
                content="Coinbase get_crypto_price API returns 200 but there's no data inside the response body. \n" +
                        "\n" +
                        "Please contact mtgtsunami@yahoo.com for further assistance."
            )
            self.email_client.send_email()
            raise ResponseNoDataException(
                "There is no data in the json body."
            )

        return float(r.json()["data"]["amount"])

    def validate_input_for_getting_crypto_price(self, crypto: str, currency: str, market_type: str) -> bool:
        if market_type not in CoinbaseClient.MARKET_TYPE_LIST:
            self.email_client.reconstruct_email(
                subject="The market type you chose is not in the available type list! Service failed to start!",
                content="Please choose a market type among: {} \n".format(CoinbaseClient.MARKET_TYPE_LIST)
            )
            self.email_client.send_email()
            raise MarketTypeNotAvailableException(
                "The market type you chose is not in the available type list!"
            )

        # According to the response body from Coinbase API: https://developers.coinbase.com/api/v2#prices
        # the order of the currency pair should only be crypto-currency.
        # Setting Currency-crypto pair, currency-currency pair, crypto-crypto pair
        # in the request URL will get a non 200 response.
        is_crypto_in_currency_list = False
        if crypto not in self.crypto_list:
            if crypto not in self.currency_list:
                self.email_client.reconstruct_email(
                    subject="The crypto you chose is not in the available crypto list! Service failed to start!",
                    content="Please choose a crypto among: {} \n".format(self.crypto_list)
                )
                self.email_client.send_email()
                raise CryptoNotAvailableException(
                    "The crypto you chose is not in the available crypto list!"
                )
            else:
                # The crypto has been falsely regarded as a currency.
                is_crypto_in_currency_list = True

        is_currency_in_crypto_list = False
        if currency not in self.currency_list:
            if currency not in self.crypto_list:
                self.email_client.reconstruct_email(
                    subject="The currency you chose is not in the available currency list! Service failed to start!",
                    content="Please choose a currency among: {} \n".format(self.currency_list)
                )
                self.email_client.send_email()
                raise CurrencyNotAvailableException(
                    "The currency you chose is not in the available currency list!"
                )
            else:
                # The currency has been falsely regarded as a crypto.
                is_currency_in_crypto_list = True

        if crypto in self.crypto_list and currency in self.crypto_list:
            self.email_client.reconstruct_email(
                subject="The currency and crypto you chose are both in the available crypto list! " +
                        "Service failed to start!",
                content="Please choose a currency among: {} \n".format(self.currency_list) +
                        "And a crypto among: {} \n".format(self.crypto_list)
            )
            self.email_client.send_email()
            raise CryptoDuplicateException(
                "The currency and crypto you chose are both in the available crypto list!"
            )

        if crypto in self.currency_list and currency in self.currency_list:
            self.email_client.reconstruct_email(
                subject="The currency and crypto you chose are both in the available currency list! " +
                        "Service failed to start!",
                content="Please choose a currency among: {} \n".format(self.currency_list) +
                        "And a crypto among: {} \n".format(self.crypto_list)
            )
            self.email_client.send_email()
            raise CurrencyDuplicateException(
                "The currency and crypto you chose are both in the available currency list!"
            )

        return True if is_crypto_in_currency_list and is_currency_in_crypto_list else False


if __name__ == "__main__":
    # TODO: Will be replaced by unit tests
    # Tests
    client = CoinbaseClient()
    print(client.get_crypto_price("BTC", "BTC", "spot"))
