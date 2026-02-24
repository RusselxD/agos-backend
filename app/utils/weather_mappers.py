
def get_weather_condition(self, weather_code: int) -> str:
        if weather_code == 0: # Clear sky
            return "Sunny"
        elif weather_code == 1:
            return "Mainly Clear"
        
        elif 2 <= weather_code <= 3: # Cloudy
            return "Cloudy"
    
        elif 45 <= weather_code <= 48: # Fog
            return "Foggy"
        
        elif 51 <= weather_code <= 57: # Drizzle
            return "Drizzle"
        
        elif 61 <= weather_code <= 67: # Rain
            return "Rain"
        
        elif 71 <= weather_code <= 77: # Snow
            return "Snow"
        
        elif 80 <= weather_code <= 82: # Rain showers
            return "Showers"
        
        elif 85 <= weather_code <= 86: # Snow showers
            return "Snow Showers"
        
        elif 95 <= weather_code <= 99: # Thunderstorm
            return "Thunderstorm"
        
        return "Unknown"


def get_weather_description(self, precipitation: float) -> str:
    if precipitation == 0:
        return "No rainfall detected"
    elif precipitation <= 2.5:
        return "Light precipitation"
    elif precipitation <= 10:
        return "Moderate rainfall intensity"
    elif precipitation <= 50:
        return "Heavy rainfall detected"
    else:
        return "Extreme rainfall conditions"


def get_temperature_description(self, temperature_c: float) -> str:
        if temperature_c < 15:
            return "Cold"
        elif temperature_c < 22:
            return "Cool"
        elif temperature_c < 30:
            return "Warm"
        else:
            return "Hot"


def get_humidity_level(self, humidity_percent: float) -> str:
    if humidity_percent < 40:
        return "Dry"
    elif humidity_percent < 60:
        return "Comfortable"
    elif humidity_percent < 80:
        return "Humid"
    else:
        return "Very humid"


def get_wind_category(self, wind_speed_kmh: float) -> str:
    if wind_speed_kmh < 5:
        return "Calm"
    elif wind_speed_kmh < 15:
        return "Light breeze"
    elif wind_speed_kmh < 30:
        return "Breezy"
    elif wind_speed_kmh < 50:
        return "Strong winds"
    else:
        return "High winds"


def get_wind_direction_label(self, degrees: float) -> str:
    # Normalize degrees to 0-360
    degrees = degrees % 360
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    # Each direction covers 45 degrees, offset by 22.5 to center
    index = int((degrees + 22.5) / 45) % 8
    return directions[index]


def get_cloudiness(self, cloud_cover_percent: float) -> str:
    if cloud_cover_percent < 20:
        return "Clear"
    elif cloud_cover_percent < 50:
        return "Partly cloudy"
    elif cloud_cover_percent < 80:
        return "Mostly cloudy"
    else:
        return "Overcast"


def get_comfort_level(self, temperature_c: float, humidity_percent: float) -> str:
    # Simplified heat index / comfort assessment
    if temperature_c < 15:
        return "Cool"
    elif temperature_c < 22:
        if humidity_percent > 70:
            return "Cool & damp"
        return "Comfortable"
    elif temperature_c < 28:
        if humidity_percent < 50:
            return "Comfortable"
        elif humidity_percent < 70:
            return "Warm & humid"
        else:
            return "Uncomfortable"
    elif temperature_c < 35:
        if humidity_percent < 40:
            return "Hot but tolerable"
        elif humidity_percent < 60:
            return "Uncomfortable"
        else:
            return "Oppressive"
    else:
        if humidity_percent > 50:
            return "Heat stress risk"
        return "Very hot"


def get_storm_risk_level(self, weather_code: int, precipitation_mm: float, wind_speed_kmh: float) -> str:
    # Thunderstorm codes: 95-99
    is_thunderstorm = 95 <= weather_code <= 99
    heavy_rain = precipitation_mm > 10
    strong_wind = wind_speed_kmh > 30
    
    if is_thunderstorm:
        return "Likely"
    elif heavy_rain and strong_wind:
        return "Possible"
    elif heavy_rain or (80 <= weather_code <= 82 and strong_wind):
        return "Low"
    else:
        return "None"