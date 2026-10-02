"""Check public readiness as well as Docker healthchecks before collecting tests."""

import os
import time

import httpx


def main():
    pending = {
        os.environ["INTEGRATION_API_URL"] + "/",
        os.environ["INTEGRATION_WEB_URL"] + "/login",
    }
    deadline = time.monotonic() + 90
    errors = {}
    with httpx.Client(timeout=5, trust_env=False) as client:
        while pending and time.monotonic() < deadline:
            for url in list(pending):
                try:
                    response = client.get(url)
                    response.raise_for_status()
                except httpx.HTTPError as error:
                    errors[url] = str(error)
                else:
                    pending.remove(url)
            if pending:
                time.sleep(1)
    if pending:
        raise SystemExit(
            f"Integration stack not ready: { {url: errors.get(url) for url in pending} }"
        )


if __name__ == "__main__":
    main()
