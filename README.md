# Scraping doge.gov/savings

## Install

```
git clone https://github.com/nickhand/doge-savings-scraper.git
cd doge-savings-scraper
poetry install
```

## Run

```
poetry run doge-savings-scraper run --browser firefox --log-freq 10
```

This saves the scraping results to a CSV file in the `data` directory. The `--log-freq` flag specifies how often to log the scraping progress. You can choose "firefox" or "chrome" for the `--browser` flag.

## Daily scrape

A GitHub action workflow runs once a day to scrape the data and commit the results to this repository. The workflow is defined in `.github/workflows/scrape.yml`. The script saves the results to the `data` directory, tagged with the timestamp of the scrape.