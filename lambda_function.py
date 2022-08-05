import os
os.environ[ 'MPLCONFIGDIR' ] = '/tmp/'
import base64
import requests
import json
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO


def lambda_handler(event, context):
    # request the current weather from my PWS via Wunderground API
    # see here for this documentation: https://docs.google.com/document/d/13HTLgJDpsb39deFzk_YCQ5GoGoZCO_cRYzIxbwvgJLI/edit
    # use your own stationId and postalKey (Zipcode) of interest, and Weather Underground apiKey (mine has been replaced with XXX)

    seven_day_hourly = requests.get('https://api.weather.com/v2/pws/observations/hourly/7day?stationId=KIAAMES93&format=json&units=e&apiKey=XXX')
    seven_day_summary = requests.get('https://api.weather.com/v2/pws/dailysummary/7day?stationId=KIAAMES93&format=json&units=e&apiKey=XXX')
    forecast = requests.get('https://api.weather.com/v3/wx/forecast/daily/5day?postalKey=50010:US&units=e&language=en-US&format=json&apiKey=XXX')

    # convert to dict using json package to load string
    data = json.loads(seven_day_hourly.text)
    daily_data = json.loads(seven_day_summary.text)
    data_forecast = json.loads(forecast.text)

    ## get rainfall and humidity data from hourly records
    # loop thru json/dict and save to list
    water_data = []
    for obs in data["observations"]:
        water_data.append([obs["obsTimeLocal"],obs["imperial"]["tempAvg"],obs["imperial"]["dewptAvg"],obs["imperial"]["precipRate"]])

    # convert to dataframe & name the columns & convert datetime
    df_water = pd.DataFrame(water_data)
    df_water.columns = ["obsTimeLocal","tempAvg","dewptAvg","precipRate"]
    df_water['obsTimeLocal'] = pd.to_datetime(df_water['obsTimeLocal'])

    # loop thru json/dict and save to list
    daily_precip = []
    for obs in daily_data["summaries"]:
        daily_precip.append([obs["obsTimeLocal"],obs["imperial"]["precipTotal"]])

    # convert to dataframe & name the columns & convert datetime
    df_water_daily = pd.DataFrame(daily_precip)
    df_water_daily.columns = ["obsTimeLocal","precipTotal"]
    df_water_daily['obsTimeLocal'] = pd.to_datetime(df_water_daily['obsTimeLocal'])

    # get names of days
    day_names = df_water_daily['obsTimeLocal'].dt.day_name()
    day_names_list = []
    for name in day_names:
        day_names_list.append(name)
    day_names_list[-1] = 'Today'  # change today's name to "today"
    day_names_list[-2] = 'Yesterday' # change yesterday's name to "yesterday"
    day_names_list.append('Tomorrow') # add "tomorrow"

    # cumulative summation of daily total precipitation with exponential decay
    # lambda chosen as 1/2 as guess from previous work
    precip_list = df_water_daily['precipTotal'].to_list()
    sum = 0
    cum_decay_precip = []
    for rain in precip_list:
        sum = sum*2.718**(-1/2) + rain
        cum_decay_precip.append(sum)
    df_water_daily['precipCumDecay'] = cum_decay_precip

    ## get forecast data from json/dict
    daypart_ob = data_forecast['daypart'] # extract relevant part of json which is list with one item
    daypart_ob = daypart_ob[0] # get that item - now we are back to dictionary
    fc_daypartName = daypart_ob['daypartName']
    fc_precipChance = daypart_ob['precipChance']
    fc_qpf = daypart_ob['qpf']
    fc_temp = daypart_ob['temperature']
    fc_data = pd.DataFrame(   # make dataframe by creating list of dictionaris, then convert to df
        {'daypartName': fc_daypartName,
         'precipChance': fc_precipChance,
         'qpf': fc_qpf,
         'temperature': fc_temp
        })
    # if we pull data in the evening, the daypartName = None for today (since it's passed) and the rest of the values are NaNs
    # this breaks the graphing - handle by deleting this row from df
    if fc_data['daypartName'][0] == None:
        fc_data = fc_data.drop(0,0) # drop the first row
    # convert forecasted temps and precip percentages to integers
    fc_data['precipChance'] = fc_data['precipChance'].astype('uint')
    fc_data['temperature'] = fc_data['temperature'].astype('uint')

    ### plot the data

    fig, axes = plt.subplots(figsize=(20, 14))


    ax1 = plt.subplot(3,2,1) # hourly temp & dewpoint

    ax1.plot(df_water['obsTimeLocal'], df_water['tempAvg'], label = 'Temp')
    ax1.plot(df_water['obsTimeLocal'], df_water['dewptAvg'], label = 'Dew Point')
    plt.title(f"Temperature & Dewpoint (F)")
    #plt.xlabel("Date & Time")
    plt.ylabel("Temperature (F)")
    ax1.legend()
    # add ticks with names of days to top x axis
    ax1_top = ax1.twiny()
    top_ticks = ax1.get_xticks()
    ax1_top.set_xticks(top_ticks)
    ax1_top.set_xticklabels(day_names_list[0:len(top_ticks)]) # use this to match lengths of label list to ticks
    # have to set the correct x limits for top axis
    left, right = ax1.get_xlim()
    ax1_top.set_xlim(left,right)
    # add marker and label last data point
    ax1.plot(df_water['obsTimeLocal'].iloc[-1],df_water['tempAvg'].iloc[-1], marker = 's', markersize = 20, markeredgecolor = 'C0', markerfacecolor= 'w')
    ax1.annotate(df_water['tempAvg'].iloc[-1], (df_water['obsTimeLocal'].iloc[-1],df_water['tempAvg'].iloc[-1]),horizontalalignment = 'center', verticalalignment = 'center')


    ax3 = plt.subplot(3,2,3) # hourly precip rate

    ax3.plot(df_water['obsTimeLocal'], df_water['precipRate'])
    plt.title("Precipitation Rate (Active Rainfall)")
    #plt.xlabel("Date & Time")
    plt.ylabel("Inches/Hour")
    # add ticks with names of days to top x axis
    ax3_top = ax3.twiny()
    top_ticks = ax3.get_xticks()
    ax3_top.set_xticks(top_ticks)
    ax3_top.set_xticklabels(day_names_list[0:len(top_ticks)]) # use this to match lengths of label list to ticks
    # have to set the correct x limits for top axis
    left, right = ax3.get_xlim()
    ax3_top.set_xlim(left,right)


    ax5 = plt.subplot(3,2,5) # daily precip summary

    ax5.scatter(df_water_daily['obsTimeLocal'], df_water_daily['precipCumDecay'], marker = 'x', color = 'y', label="Est. H20 in Soil")
    ax5.stem(df_water_daily['obsTimeLocal'], df_water_daily['precipTotal'], basefmt='k:', label="Recorded Precip") # set baseline as black, dotted
    plt.axhline(y=1.0, color='r', linestyle='-') # add horizontal line at one inch
    plt.title(f"Precipitation Past Week (Total {round(df_water_daily['precipTotal'].sum(),2)} Inches)")
    #plt.xlabel("Date & Time")
    plt.ylabel("Inches")
    ax5.legend()  # for this to work, here we make the plot w/ax5. and not plt. command, and use inline label
    # add ticks with names of days to top x axis, need one fewer tick
    ax5_top = ax5.twiny()
    top_ticks = ax5.get_xticks()
    ax5_top.set_xticks(top_ticks)
    ax5_top.set_xticklabels(day_names_list[0:len(top_ticks)])  # use this to match lengths of label list to ticks
    # have to set the correct x limits for top axis
    left, right = ax5.get_xlim()
    ax5_top.set_xlim(left, right)
    for x, y in zip(df_water_daily['obsTimeLocal'], df_water_daily['precipTotal']): # loop to annotate with value of each point
        ax5.annotate(y, (x,y), xytext = (0,10), textcoords='offset pixels', horizontalalignment = 'center') # xytext offset label by pixels, a la textcoords


    ax2 = plt.subplot(3,2,2) # forecast temp

    plt.plot(fc_data['daypartName'], fc_data['temperature'], marker = 's', markersize = 20, markerfacecolor= 'w')
    plt.xticks(rotation=25)
    plt.title("Forecast Temperature (F)")
    plt.ylabel("Temperature (F)")
    ax2.margins(y= 0.20)  # default is 0.05; larger number gives more padding, negative can zoom
    for i, quant in enumerate(fc_data['temperature']): # loop to annotate with value of each point
        ax2.annotate(quant, (i,quant), horizontalalignment = 'center', verticalalignment = 'center')


    ax4 = plt.subplot(3,2,4) # forecast percent chance of precip

    #plt.ylim(0,100)
    plt.plot(fc_data['daypartName'], fc_data['precipChance'])
    plt.xticks(rotation=25)
    plt.title("Forecast Chance of Precipitation")
    plt.ylabel("Percent Chance")
    ax4.margins(y= 0.20)
    ax4.set_ylim(0,100)
    for i, quant in enumerate(fc_data['precipChance']):
        if quant >30:
            ax4.annotate(quant, (i,quant), xytext = (0,10), textcoords='offset pixels', horizontalalignment = 'center')


    ax6 = plt.subplot(3,2,6) # forecast precip quantity

    plt.plot(fc_data['daypartName'], fc_data['qpf'])
    plt.axhline(y=1.0, color='r', linestyle='-') # add horizontal line at one inch
    plt.xticks(rotation=25)
    plt.title(f"Forecast Precipitation (Total {round(fc_data['qpf'].sum(),2)} Inches)")
    plt.ylabel("Inches")
    ax4.margins(y= 0.20)
    for i, quant in enumerate(fc_data['qpf']):
        if quant > 0:
            ax6.annotate(quant, (i,quant), xytext = (0,10), textcoords='offset pixels', horizontalalignment = 'center')


    plt.suptitle(f"Precipitation Data and Forecast for Will's Garden\n{df_water['obsTimeLocal'].iloc[-1].strftime('%A, %b %-d, %Y, %-I:%M %p')}", size=24, weight='demibold')
    plt.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=None, hspace=0.5)

    # save plot to memory to get binary data for API return

    figfile = BytesIO()  # create file-like object
    plt.savefig(figfile, format='png', bbox_inches='tight')  # save plot to memory (not disk)
    plt.close()
    figfile.seek(0) # make sure read from beginning
    image = figfile.read()  # read file from memory for returning from API

    return {
        'headers': { "Content-Type": "image/png" },
        'statusCode': 200,
        'body': base64.b64encode(image).decode('utf-8'), # need binary encoding
        'isBase64Encoded': True
    }
