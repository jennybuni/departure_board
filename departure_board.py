import pygame
import zeep
from datetime import datetime
import json
import time
import logging
import requests

# === Setup logging ===
logging.basicConfig(
    filename="departure_board.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# === Load configuration ===
with open("config.json", "r") as config_file:
    config = json.load(config_file)

API_KEY = config["API_KEY"]
STATION_CODE = config["STATION_CODE"]
TARGET_PLATFORMS = [str(p) for p in config["TARGET_PLATFORMS"]]
TEST_MODE = config.get("TEST_MODE", False)
UPDATE_INTERVAL = config.get("UPDATE_INTERVAL", 30)
ROTATE_DISPLAY = config.get("ROTATE_DISPLAY", False)
SCROLL_SPEED = config.get("SCROLL_SPEED", 14)
CLOCK_FONT_SIZE = config.get("CLOCK_FONT_SIZE", 148)
TRAIN_FONT_SIZE = config.get("TRAIN_FONT_SIZE", 56)
STATUS_FONT_SIZE = config.get("STATUS_FONT_SIZE", 50)
LATITUDE = config.get("LATITUDE")
LONGITUDE = config.get("LONGITUDE")
# === Set up SOAP client ===
WSDL_URL = "https://lite.realtime.nationalrail.co.uk/OpenLDBWS/wsdl.aspx"
client = zeep.Client(wsdl=WSDL_URL)
header = zeep.xsd.Element(
    "{http://thalesgroup.com/RTTI/2013-11-28/Token/types}AccessToken",
    zeep.xsd.ComplexType([zeep.xsd.Element("TokenValue", zeep.xsd.String())]),
)
header_value = header(TokenValue=API_KEY)

# === Initialize Pygame ===
pygame.mixer.pre_init(0, 0, 0, 0)
pygame.init()
pygame.mixer.quit()

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Departures Board")

BLACK = (0, 0, 0)
ORANGE = (255, 165, 0)

font_path = "fonts/bus-stop.ttf"
clock_font = pygame.font.Font(font_path, CLOCK_FONT_SIZE)
train_font = pygame.font.Font(font_path, TRAIN_FONT_SIZE)
status_font = pygame.font.Font(font_path, STATUS_FONT_SIZE)

class ScrollingText:
    def __init__(self, y_pos, text, x_start, end_x):
        self.text = text
        rendered_text = train_font.render(self.text, True, ORANGE)
        self.text_width = rendered_text.get_width()
        self.surface = pygame.Surface((self.text_width, train_font.get_height()), pygame.SRCALPHA).convert_alpha()
        self.surface.blit(rendered_text, (0, 0))
        self.x_pos = x_start
        self.y_pos = y_pos
        self.speed = SCROLL_SPEED
        self.end_x = end_x

    def update(self):
        self.x_pos -= self.speed
        if self.x_pos < self.end_x:
            self.x_pos = WINDOW_WIDTH

    def draw(self, surface, clip_rect=None):
        if clip_rect:
            surface.set_clip(clip_rect)
        surface.blit(self.surface, (self.x_pos, self.y_pos))
        surface.set_clip(None)

def fetch_test_data_grouped(target_platforms):
    try:
        with open("test_data.json", "r") as file:
            test_data = json.load(file)
            platform_map = {platform: [] for platform in target_platforms}
            for entry in test_data:
                platform = entry.get("platform")
                if platform in platform_map and len(platform_map[platform]) < 2:
                    platform_map[platform].append((entry["departure_time"], entry["destination"], entry["calling_at"], entry["status"]))
            return platform_map
    except Exception as e:
        logging.error(f"Error loading test data: {e}")
        return {}

def fetch_departures():
    if TEST_MODE:
        return fetch_test_data_grouped(TARGET_PLATFORMS)

    try:
        response = client.service.GetDepartureBoard(10, STATION_CODE, _soapheaders=[header_value])
        if not hasattr(response, 'trainServices') or not response.trainServices:
            return {}

        services_by_platform = {platform: [] for platform in TARGET_PLATFORMS}

        for service in response.trainServices.service:
            platform = service.platform
            if platform in services_by_platform and len(services_by_platform[platform]) < 2:
                destination = service.destination.location[0].locationName
                departure_time = service.std
                etd = service.etd.strip().lower()
                status = "On time" if etd == "on time" else f"Exp {etd}" if ":" in etd else "Exp unknown"

                calling_at = ""
                if len(services_by_platform[platform]) == 0:
                    try:
                        details = client.service.GetServiceDetails(service.serviceID, _soapheaders=[header_value])
                        if hasattr(details, 'subsequentCallingPoints') and details.subsequentCallingPoints:
                            point_lists = details.subsequentCallingPoints.callingPointList
                            if isinstance(point_lists, list) and point_lists:
                                points = point_lists[0].callingPoint
                                calling_at = ", ".join(cp.locationName for cp in points if hasattr(cp, "locationName"))
                    except Exception as e:
                        logging.error(f"Failed to extract calling points for {destination}: {e}")

                services_by_platform[platform].append((departure_time, destination, calling_at, status))

        return services_by_platform
    except Exception as e:
        logging.error(f"Error fetching data: {str(e)}")
        return {}

def update_display_multi_platform(departures_by_platform, static_text, scrolling_texts):
    static_text.clear()
    scrolling_texts.clear()

    y_pos = 0
    for idx, (platform, departures) in enumerate(departures_by_platform.items()):
        header_text = f"Platform {platform}"
        header_surface = train_font.render(header_text, True, ORANGE)
        header_x = (WINDOW_WIDTH - header_surface.get_width()) // 2
        static_text.append((header_surface, (header_x, y_pos)))
        y_pos += train_font.get_height()

        for i, (departure_time, destination, calling_at, status) in enumerate(departures):
            if i == 1:
                y_pos += 40  # more spacing for second arrival

            static_text.append((train_font.render(departure_time, True, ORANGE), (20, y_pos)))

            if len(destination) > 90:
                scrolling_texts.append(ScrollingText(y_pos, destination, WINDOW_WIDTH, -150))
            else:
                static_text.append((train_font.render(destination, True, ORANGE), (250, y_pos)))

            if i == 0 and calling_at:
                label_surface = train_font.render("Calling at: ", True, ORANGE)
                static_text.append(("CALLING_AT_LABEL", (20, y_pos + 60), label_surface))
                scroll_text = f"{calling_at}"
                label_padding = 250
                x_start = 40 + label_surface.get_width() + label_padding
                scrolling_texts.append(ScrollingText(y_pos + 70, scroll_text, WINDOW_WIDTH, -len(scroll_text) * 60))

            color = (255, 0, 0) if "Exp" in status else ORANGE
            status_surface = status_font.render(status, True, color)
            status_x = WINDOW_WIDTH - status_surface.get_width() - 30
            status_y = y_pos + (train_font.get_height() - status_surface.get_height()) // 2
            static_text.append((status_surface, (status_x, status_y)))

            y_pos += train_font.get_height() + status_font.get_height() - 60

        y_pos -= 20  # reduced spacing between platforms

def get_temperature():
    try:
        # Using London coordinates as default (you can change these)
        latitude = LATITUDE
        longitude = LONGITUDE
        url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m"
        response = requests.get(url)
        data = response.json()
        if response.status_code == 200:
            return f"{round(data['current']['temperature_2m'])}°C"
        return "N/A"
    except Exception as e:
        logging.error(f"Error fetching temperature: {e}")
        return "N/A"

def main():
    clock = pygame.time.Clock()
    scrolling_texts = []
    static_text = []
    static_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    last_update_time = 0

    last_departures = fetch_departures()
    update_display_multi_platform(last_departures, static_text, scrolling_texts)
    static_surface.fill(BLACK)
    for item in static_text:
        if isinstance(item[0], str) and item[0] == "CALLING_AT_LABEL":
            static_surface.blit(item[2], item[1])
        elif isinstance(item[0], pygame.Surface):
            static_surface.blit(item[0], item[1])

    last_temp_update = 0
    current_temp = "N/A"

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

        if time.time() - last_update_time >= UPDATE_INTERVAL:
            last_departures = fetch_departures()
            update_display_multi_platform(last_departures, static_text, scrolling_texts)
            static_surface.fill(BLACK)
            for item in static_text:
                if isinstance(item[0], str) and item[0] == "CALLING_AT_LABEL":
                    static_surface.blit(item[2], item[1])
                elif isinstance(item[0], pygame.Surface):
                    static_surface.blit(item[0], item[1])
            last_update_time = time.time()

        # Update temperature every 10 minutes
        if time.time() - last_temp_update >= 600:  # 600 seconds = 10 minutes
            current_temp = get_temperature()
            last_temp_update = time.time()

        frame_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        frame_surface.blit(static_surface, (0, 0))

        for text in scrolling_texts:
            text.update()
            clip_x = 400
            clip_rect = pygame.Rect(clip_x, text.y_pos, WINDOW_WIDTH - clip_x, train_font.get_height())
            text.draw(frame_surface, clip_rect)

        # Draw clock and temperature
        current_time = datetime.now().strftime("%H:%M:%S")
        clock_text = clock_font.render(current_time, True, ORANGE)
        temp_text = train_font.render(current_temp, True, ORANGE)        
        # Center the clock
        clock_x = (WINDOW_WIDTH - clock_text.get_width()) // 2
        clock_y = WINDOW_HEIGHT - clock_text.get_height() - 20
        
       # Position temperature to the right of the clock with fixed spacing
        temp_x = clock_x + clock_text.get_width() + 60  # Fixed 60px spacing
        temp_y = clock_y + (clock_text.get_height() - temp_text.get_height()) // 2
        
        # Draw background for both clock and temperature
        pygame.draw.rect(frame_surface, BLACK, (
            clock_x - 10,
            clock_y - 10,
            clock_text.get_width() + temp_text.get_width() + 70,
            clock_text.get_height() + 20
        ))       
        # Draw clock and temperature
        frame_surface.blit(clock_text, (clock_x, clock_y))
        frame_surface.blit(temp_text, (temp_x, temp_y))

        if ROTATE_DISPLAY:
            frame_surface = pygame.transform.rotate(frame_surface, 180)

        screen.blit(frame_surface, (0, 0))
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
    # End-of-file (EOF)