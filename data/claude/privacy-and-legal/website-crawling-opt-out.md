---
title: "How to opt out of Claude/Anthropic crawling your website"
product_area: "data_privacy"
---
# Opting Out of Anthropic Website Crawling

Anthropic uses web crawlers to collect publicly available data for AI training purposes.

## How to opt out
To prevent Anthropic's crawler from accessing your website:
1. Add a `robots.txt` directive to your website's root directory:
   ```
   User-agent: ClaudeBot
   Disallow: /
   ```
2. This instructs Anthropic's crawler (ClaudeBot) to not crawl your site.

## More information
For questions about data use and privacy, visit Anthropic's privacy policy at anthropic.com/privacy or contact Anthropic's privacy team directly.
