# Train Departure Board

A Python-based digital train departure board that displays real-time train information for a specific platform at a railway station. The application uses the National Rail Data Feeds API to fetch live departure information and presents it in a visually appealing digital display format.



## Features

- Real-time train departure information
- Platform-specific display
- Scrolling text for calling points
- Digital clock display
- Configurable display settings
- Support for multiple platforms
- Weather information integration (optional)

![Alt text](assets/screenshot.png)

## Prerequisites

- Python 3.x
- Pygame
- Zeep (SOAP client for Python)
- National Rail Data Feeds API key https://realtime.nationalrail.co.uk/OpenLDBWSRegistration

## Installation

1. Clone this repository:
```bash
git clone https://github.com/jennybuni/departure_board.git
cd departure_board
```

2. Install the required dependencies:
```bash
pip install pygame zeep
```

3. Configure the application:
 
   First copy the config-template.json to config.json
```bash
mv config-template.json config.json
```

The `config.json` file allows you to customize various aspects of the display:

- `API_KEY`: Your National Rail Data Feeds API key
- `STATION_CODE`: The station CRS code (e.g., "WAT" for London Waterloo)
- `TARGET_PLATFORMS`: Array of platform numbers to display 
- `UPDATE_INTERVAL`: Time between API updates (in seconds) *advised to keep between 45 & 60 seconds to not overload the api*
- `ROTATE_DISPLAY`: Enable/disable display rotation 180deg
- `SCROLL_SPEED`: Speed of scrolling text 
- `CLOCK_FONT_SIZE`: Size of the clock display
- `TRAIN_FONT_SIZE`: Size of train information text
- `STATUS_FONT_SIZE`: Size of status text
- `LATITUDE`: Latitude for temp *weather API Queried every 10 minutes*
- `LONGITUDE`: Longitude for temp

## Usage

Run the main application:
```bash
python3 departure_board.py
```

The display will show:
- Current time
- Train departures for the specified platform
- Destination and scheduled departure time
- Calling points (scrolling text)
- Service status
- temperature of the location set in the config.json

## Controls

- Press `ESC` to exit the application
- Close the window to quit


## 
This program has been written for use on a raspbery pi zero W
so it is lightweight and outputs to HDMI.
Outputting to spi is in the works.



