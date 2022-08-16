import os
import sys
from glob import glob
import yaml
from yaml import Loader
from slo import build_slo_from_yaml
from validator import Validator
from rules import generate_rules

import click


class Slider:
    def __init__(self):
        self.config = {}
        self.verbose = False
        self.validator = Validator()
        self.slos = {}

    def set_config(self, key, value):
        self.config[key] = value
        if self.verbose:
            click.echo(f"  config[{key}] = {value}", file=sys.stderr)


pass_slider = click.make_pass_decorator(Slider)


@click.group()
@click.option(
    "--config",
    nargs=2,
    multiple=True,
    metavar="KEY VALUE",
    help="Overrides a config key/value pair.",
)
@click.option("--verbose", "-v", is_flag=True, help="Enables verbose mode.")
@click.version_option("1.0")
@click.pass_context
def cli(ctx, config, verbose):
    """Slider is a command line tool that creates
    Prometheus rules on the given OpenSLO specification.
    """
    ctx.obj = Slider()
    ctx.obj.verbose = verbose
    for key, value in config:
        ctx.obj.set_config(key, value)


@cli.command()
@click.argument("src", required=True)
@pass_slider
def generate(slider, src):
    """Generates Prometheus rules on the given
    OpenSLO spec files.

    SRC is the directory containing OpenSLO specs.
    """
    # Load all files and perform validation against OpenSLO schema
    files = glob(f"{src}/*")
    if src[-5:] == '.yaml':
        files.append(src)
    for f in files:
        print(f)
        if os.path.isdir(f):
            files.extend(glob(f"{f}/*"))
    for spec in files:
        if spec[-5:] != ".yaml":
            click.echo((f'File {spec} is skipped',
                        'because only .yaml type is supported'))
            continue
        with open(spec) as f2:
            docs = yaml.load_all(f2, Loader)
            for doc in docs:
                valid = True
                try:
                    slider.validator.validate_spec(
                        doc, "slo-spec.schema.json")
                except Exception as e:
                    # This is a temporary allowance, should break
                    # everytime there is something wrong with specs
                    click.echo(e)
                    valid = False
                if not valid:
                    click.echo((f'File {spec} is not',
                               'a valid Open SLO specification'))
                    continue
                slo_parsed = build_slo_from_yaml(doc)
                slo_name = slo_parsed.metadata.name
                if slo_name in slider.slos:
                    raise ValueError(
                        f'Found a duplicate SLO name {slo_name}, aborting')
                slider.slos[slo_name] = slo_parsed
    # Generate rules
    for slo in slider.slos:
        # Perform our custom validation
        slider.validator.validate_slo(slider.slos[slo])
        generate_rules(slider.slos[slo])
