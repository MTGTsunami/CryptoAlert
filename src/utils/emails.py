from email.message import EmailMessage
from smtplib import SMTP, SMTPConnectError, SMTPException

import getpass
import platform


class NoServerInitializedException(Exception):
    pass


class SMTPUnexpectedException(SMTPException):
    pass


class AlertEmail:
    """
    This serves as a helper class to generate/modify email header & contends,
    as well as to initialize Google STMP server and to send alert emails.
    """
    DEFAULT_CONTENT = "This is a test email sent by Python Crypto Alert Script"
    DEFAULT_RECEIVING_ADDRESS = "mtgtsunami@yahoo.com"
    DEFAULT_SENDING_ADDRESS = "youaretheappleofmyeye19@gmail.com"
    DEFAULT_SUBJECT = "Just a Test :)"
    GOOGLE_SMTP_SERVER = "smtp.gmail.com"
    PORT = 587

    def __init__(self, receive_address: str, subject: str, content: str, send_address="") -> None:
        self.msg = EmailMessage()
        self.msg["From"] = send_address if send_address else AlertEmail.DEFAULT_SENDING_ADDRESS
        self.msg["to"] = receive_address
        self.msg["Subject"] = subject
        self.msg.set_content(content)
        self.server = None

        # TODO: The credentials can be fetched through POST request.
        key_file_path = r"C:\Users\\" + \
                        getpass.getuser() + \
                        r"\Documents\crypto_keys\keys.txt" if platform.system() == "Windows" else \
                        "/Users/" + getpass.getuser() + "/Documents/crypto_keys/key"
        with open(key_file_path, "r") as f:
            for i, line in enumerate(f):
                if i == 0:
                    self._username = line
                if i == 1:
                    self._password = line

    @property
    def send_from(self) -> str:
        return self.msg["From"]

    @send_from.setter
    def send_from(self, address: str) -> None:
        del self.msg["From"]
        self.msg["From"] = address

    @property
    def send_to(self) -> str:
        return self.msg["to"]

    @send_to.setter
    def send_to(self, address: str) -> None:
        del self.msg["to"]
        self.msg["to"] = address

    @property
    def subject(self) -> None:
        return self.msg["Subject"]

    @subject.setter
    def subject(self, subject: str) -> None:
        del self.msg["Subject"]
        self.msg["Subject"] = subject

    @property
    def content(self) -> str:
        return self.msg.get_content()

    @content.setter
    def content(self, content: str) -> None:
        self.msg.set_content(content)

    def _initialize_email_server(self) -> None:
        tries = 1
        while tries <= 5:
            try:
                self.server = SMTP(host=AlertEmail.GOOGLE_SMTP_SERVER, port=AlertEmail.PORT)
                break
            except SMTPConnectError as err:
                print("This is #{}th try due to SMTP connection error: {}.".format(tries, err))
                tries += 1
        if not self.server:
            raise SMTPUnexpectedException(
                "Retried 4 times but still unable to connect to the SMTP server. Abort the process!"
            )

    def _quit_email_server(self) -> None:
        if not self.server:
            raise NoServerInitializedException("There is no email server at this moment. Please initialize one.")
        self.server.quit()

    def reconstruct_email(self, send_address="", receive_address="", subject="", content="") -> None:
        if send_address:
            self.send_from = send_address

        if receive_address:
            self.send_to = receive_address

        if subject:
            self.subject = subject

        if content:
            self.content = content

    def send_email(self) -> None:
        self._initialize_email_server()
        self.server.starttls()
        self.server.login(user=self._username, password=self._password)
        self.server.send_message(self.msg)
        self._quit_email_server()

    @staticmethod
    def send_test_email() -> None:
        msg = EmailMessage()
        msg.set_content(AlertEmail.DEFAULT_CONTENT)
        msg["Subject"] = AlertEmail.DEFAULT_SUBJECT
        msg["From"] = AlertEmail.DEFAULT_SENDING_ADDRESS
        msg["to"] = AlertEmail.DEFAULT_RECEIVING_ADDRESS

        key_file_path = r"C:\Users\\" + getpass.getuser() + r"\Documents\crypto_keys\keys.txt"
        with open(key_file_path, "r") as f:
            for i, line in enumerate(f):
                if i == 0:
                    _username = line
                if i == 1:
                    _password = line

        server = SMTP(host=AlertEmail.GOOGLE_SMTP_SERVER, port=AlertEmail.PORT)
        server.starttls()
        server.login(user=_username, password=_password)
        server.send_message(msg)
        server.quit()


if __name__ == "__main__":
    # TODO: Will be replaced by unit tests
    # Tests
    c = AlertEmail(
        receive_address="jw.zhang86@gmail.com",
        subject="hello handsome boy!",
        content="what a beautiful day!"
    )
    c.send_email()
