# Scraping doge.gov/savings

## Install

```
https://github.com/nickhand/doge-savings-scraper.git
cd doge-savings-scraper
poetry install
```

## Run

```
poetry run doge-savings-scraper run --browser firefox --log-freq 10
```

This saves the scraping results to a CSV file in the `data` directory called "doge_savings_cfpb.csv". The `--log-freq` flag specifies how often to log the scraping progress. You can choose "firefox" or "chrome" for the `--browser` flag.