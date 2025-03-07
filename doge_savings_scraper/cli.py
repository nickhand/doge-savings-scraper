from datetime import datetime

import click

from . import HOME_FOLDER
from .scrape import WebScraper


@click.group()
def cli():
    """CLI for scraping doge.gov/savings website"""
    pass


@cli.command()
@click.option(
    "--browser",
    type=click.Choice(["firefox", "chrome"]),
    default="firefox",
    help="The browser to use.",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Turn on additional logging for debugging purposes.",
)
@click.option(
    "--log-freq", default=10, type=int, help="How often to log while scraping."
)
@click.option(
    "--max-results",
    default=None,
    type=int,
    help="Only scrape this many results (testing purposes).",
)
def run(debug=False, browser="firefox", log_freq=10, max_results=None):
    """Run scraper."""

    # Initialize the scraper
    scraper = WebScraper(debug=debug, browser=browser)

    # Run the scraper
    data = scraper.scrape_data(log_freq=log_freq, max_results=max_results)

    # Make sure output folder exists
    output_folder = HOME_FOLDER / ".." / "data"
    output_folder.mkdir(exist_ok=True)

    # Tag the file
    tag = datetime.now().strftime("%Y-%m-%d__%H-%M-%S")
    output_file = output_folder / f"doge_savings_cfpb_{tag}.csv"
    data.to_csv(output_file, index=False)
