import requests
import pandas as pd
from datetime import date
import os
from orchestra_sdk.enum import TaskRunStatus
from orchestra_sdk.orchestra import OrchestraSDK


def get_daily_weather_data():
    """
    Fetches the hourly temperature forecast for the current day from the Open-Meteo API.

    This function retrieves data for London, UK, and returns it as a pandas DataFrame.
    The script is designed to be run at the beginning of a day (e.g., 00:00) to get the
    forecast for the next 24 hours.
    """
    try:
        # --- Configuration ---
        # Get today's date in the required YYYY-MM-DD format
        today = date.today().strftime("%Y-%m-%d")

        # Define the API endpoint and parameters
        # Location: London, UK
        # Hourly data: Temperature at 2 meters
        # Dates: Start and end date are both today for a 24-hour forecast
        api_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 51.51,
            "longitude": -0.12,
            "hourly": "temperature_2m",
            "start_date": today,
            "end_date": today,
            "timezone": "auto",  # Use the location's timezone
        }

        # --- Data Fetching ---
        print(f"Fetching weather data for {today}...")
        response = requests.get(api_url, params=params)

        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()

        data = response.json()
        print("Data fetched successfully.")

        # --- Data Processing ---
        # Extract the hourly data from the JSON response
        hourly_data = data.get("hourly", {})

        if (
            not hourly_data
            or "time" not in hourly_data
            or "temperature_2m" not in hourly_data
        ):
            print("Error: The API response did not contain the expected hourly data.")
            return None

        # Create a pandas DataFrame
        df = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(hourly_data["time"]),
                "temperature_celsius": hourly_data["temperature_2m"],
            }
        )

        # Set the timestamp as the index for easier time-based analysis
        df.set_index("timestamp", inplace=True)

        return df

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the API request: {e}")
        return None
    except KeyError as e:
        print(f"Error parsing the API response. Missing key: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


if __name__ == "__main__":
    # Initialize OrchestraSDK with API key from environment variable
    api_key = os.getenv("ORCHESTRA_API_KEY", "your_api_key")
    orchestra = OrchestraSDK(api_key=api_key)

    try:
        print("Starting weather data processing")
        weather_df = get_daily_weather_data()
        if weather_df is not None:
            print("\n--- Hourly Temperature Forecast for London ---")
            print(weather_df)
            print("\n------------------------------------------")
            # Set the DataFrame as output (convert to dict for serialization)
            orchestra.set_output(name="weather_data", value=weather_df.to_dict())
        else:
            orchestra.update_task(
                status=TaskRunStatus.FAILED, message="No weather data returned."
            )
    except Exception as e:
        orchestra.update_task(status=TaskRunStatus.FAILED, message=str(e))
        print(f"An error occurred: {e}")
