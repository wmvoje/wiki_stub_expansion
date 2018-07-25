# Finding main factors that contribute to wikipedia page popularity
## Summary
This project studies the characteristics of a Wikipedia page (number of words, number of Wikipedia links, number of images it contains, etc...) to identify characteristics that correlate with a page popularity.

Here I find relationships using data from ~8000 wikiedia pages. The pool of Wikipedia pages were populated by enumerating all Wikipedia pages that are listed by a seed population of 20 pages (snowball sampling).

## Questions Explored:
- Which factor(s) most strongly coorlate with a page popularity?

## Techniques used:
- OLS regression
- VIF
- Ridge Regression
- LASSO Regression

## Key Findings:
- The number of images in a page, the number of external links in a page, and the number of Wikipedia articles that reference a page correlate strongly with a pages popularity

## Data sources:
- en.wikipedia


