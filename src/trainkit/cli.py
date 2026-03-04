import click
from trainkit.validate import validate_jsonl


@click.group()
def cli():
    """TrainKit CLI."""
    pass


@cli.command()
@click.argument("file", type=click.Path())
def validate(file):
    """Validate a JSONL evaluation set against the TrainKit schema."""
    exit_code = validate_jsonl(file)
    raise SystemExit(exit_code)
