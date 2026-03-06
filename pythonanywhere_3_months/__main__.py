from . import credential_file_name
from .core import get_credentials, run


def main():
    username, password = get_credentials(credential_file_name)
    run(username, password)


if __name__ == "__main__":
    main()
