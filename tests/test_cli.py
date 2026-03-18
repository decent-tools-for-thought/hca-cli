from io import StringIO
from contextlib import redirect_stdout

from hca_cli.cli import main


def test_api_describe_smoke() -> None:
    stdout = StringIO()
    with redirect_stdout(stdout):
        exit_code = main(["api", "describe", "GET", "/index/catalogs"])
    assert exit_code == 0
    output = stdout.getvalue()
    assert '"operation": "GET /index/catalogs"' in output
