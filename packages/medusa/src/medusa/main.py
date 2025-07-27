"""
Medusa CLI main entry point.

Provides command-line interface for Medusa media upload and social automation.
"""

import click

from .cli.commands import upload_command


@click.group()
@click.version_option()
def main():
    """Medusa - Media Upload & Social Automation.

    Upload videos to YouTube and other platforms with automated social media publishing.
    """
    pass


# Add the upload command to the main group
main.add_command(upload_command, name="upload")


if __name__ == "__main__":
    main()
