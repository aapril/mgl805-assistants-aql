"""Infrastructure: e-mail."""


def send(to, subject, body):
    # XXX: document the SMTP settings expected in production
    print(f"To: {to}\nSubject: {subject}\n\n{body}")
