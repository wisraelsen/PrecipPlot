# PrecipPlot
**Python AWS Lambda function for plotting personal weather station data and forecast data from Weather Underground.**

**This is a personal data science project, which you can see [here](https://israelsenlab.org/precipplot.html) on my personal webpage (once the updated version goes live).**

This project uses:
- a Weather Underground account 
- a personal weather station sending data to Weather Underground
  - (my personal weather station is from Lacrosse Technology)
- the Amazon API Gateway to call for the plot from AWS Lambda
- lambda_function.py from this respository deployed as an AWS Lambda function, which:
  - retrieves data from the Weather Undergroud API using 'requests'
  - processes it using 'json' and 'pandas'
  - creates the plot using 'matplotlib.pyplot'
  - generates and encodes the png image using 'io.BytesIO' and 'base64' encoding
  - and finally returns the image through the Amazon API

I chose to use AWS Lambda instead of running the script directly in the browser (for example, with PyScript) because I wanted to use AWS Lambda as a "backend" to hide my Weather Underground API Keys.
