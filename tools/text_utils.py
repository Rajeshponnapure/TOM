"""Small text helpers shared by the routers."""
import re

_ADDRESS_OR_URL = re.compile(r"https?://\S+|[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def without_addresses(text: str) -> str:
    """`text` with email addresses and URLs blanked out.

    Routers match keywords anywhere in a request, so "boss@slack.com" used to read as "Slack" and
    "gnaneshwari@gmail.com" as "Gmail". Detection must look at the words the user wrote, not at the
    address; anything that needs the address itself reads it from the original text.
    """
    return _ADDRESS_OR_URL.sub(" ", text or "")
