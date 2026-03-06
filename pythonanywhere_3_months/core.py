#!/usr/local/env python3

import os
import sys
import traceback
import logging
import argparse
from time import time
from pathlib import Path
from typing import Tuple

import yaml
import requests

from . import (
    last_run_at_absolute_path,
    login_page,
)

BASE_URL = "https://www.pythonanywhere.com"


def setup_debug_logging() -> None:
    logging.basicConfig(
        level=logging.DEBUG, format="%(asctime)s %(levelno)s - %(message)s"
    )


def get_options() -> Tuple[str]:
    """Gets options from user"""
    parser = argparse.ArgumentParser(
        description="Extends the PythonAnywhere web app expiry"
    )
    parser.add_argument(
        "-H", "--hidden", help="(kept for backwards compat, ignored)",
        action="store_true"
    )
    parser.add_argument(
        "-c", "--chromedriver-path",
        help="(kept for backwards compat, ignored)",
        default=None,
    )
    parser.add_argument("-d", "--debug", help="Prints debug logs", action="store_true")
    args = parser.parse_args()
    if args.debug:
        setup_debug_logging()
    return args.hidden, args.chromedriver_path


def get_credentials(filepath: str) -> Tuple[str, str]:
    """Gets pythonanywhere credentials from the dotfile"""
    absolute_path = os.path.abspath(os.path.join(Path.home(), filepath))
    logging.debug("Credential File Location: {}".format(absolute_path))
    with open(absolute_path, "r") as cred:
        creds = yaml.load(cred, Loader=yaml.FullLoader)
    return creds["username"], creds["password"]


def run(
    username: str, password: str, chromedriver_path: str = None,
    use_hidden: bool = False
) -> None:
    try:
        session = requests.Session()

        # Get login page for CSRF token
        login_resp = session.get(login_page)
        login_resp.raise_for_status()
        csrf_token = session.cookies["csrftoken"]
        logging.debug("Got CSRF token from login page")

        # Login
        login_data = {
            "csrfmiddlewaretoken": csrf_token,
            "auth-username": username,
            "auth-password": password,
            "login_view-current_step": "auth",
        }
        resp = session.post(
            login_page,
            data=login_data,
            headers={"Referer": login_page},
        )
        resp.raise_for_status()
        if "/login/" in resp.url:
            print("Login failed - still on login page", file=sys.stderr)
            sys.exit(1)

        # Extract actual username from redirect URL (login may use email)
        # e.g. https://www.pythonanywhere.com/user/Avia2292/
        pa_username = resp.url.split("/user/")[1].split("/")[0]
        print("Logged in as {}".format(pa_username), file=sys.stderr)

        # Get webapps page for fresh CSRF token
        webapps_url = "{}/user/{}/webapps/".format(BASE_URL, pa_username)
        resp = session.get(webapps_url)
        resp.raise_for_status()
        csrf_token = session.cookies["csrftoken"]

        # Extend the webapp
        extend_url = "{}/user/{}/webapps/{}.pythonanywhere.com/extend".format(
            BASE_URL, pa_username, pa_username
        )
        resp = session.post(
            extend_url,
            data={"csrfmiddlewaretoken": csrf_token},
            headers={"Referer": webapps_url},
        )
        resp.raise_for_status()
        print("Extend response: {} {}".format(resp.status_code, resp.url),
              file=sys.stderr)

        # save current time to 'last run time file'
        with open(last_run_at_absolute_path, "w") as f:
            f.write(str(time()))

        print("Done!", file=sys.stderr)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
