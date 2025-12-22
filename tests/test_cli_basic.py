from typer.testing import CliRunner
from video2mdnotes.main import app

runner = CliRunner()

def test_cli_hello():
    result = runner.invoke(app, ["hello", "World"])
    assert result.exit_code == 0
    assert "Hello, World!" in result.stdout

def test_cli_process_help():
    result = runner.invoke(app, ["process", "--help"])
    assert result.exit_code == 0
    assert "Downloads, transcribes, and summarizes" in result.stdout
