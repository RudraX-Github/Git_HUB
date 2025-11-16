import requests
import pandas as pd
from datetime import timedelta
import time
import sys
import json
import os
from tqdm import tqdm

# --- CONFIGURATION ---

# 1. ADD YOUR API KEYS HERE
# It will rotate through this list if one key hits its rate limit.
API_KEYS = [
    "fa82e8af08314f64ab0d2f7492b46e9f"  # Business Trial 4 (Expires 2025-12-07)
    "9e56a4f3fab748418bc299713138f15c", # Business Trial 3 (Expires 2025-12-07)
    "de8e274a65ec45929d501a63466da6cf", # Business Trial 1 (Expires 2025-12-03)
    "7335451fcc0646bb86611027b68292e0", # Business Trial 2 (Expires 2025-12-07)
    
    
]
# Global index to track which key we are currently using
current_key_index = 0

# 2. ADD YOUR MARKETS HERE
# The script will loop through this dictionary and create one CSV per market.
MARKETS = {
    "Bardoli": {"lat": 21.1439076246341, "lon": 73.249972681491997},
    "Bardoli_Katod": {"lat": 21.12, "lon": 73.12},
    "Bardoli_Madhi": {"lat": 21.15, "lon": 73.25},
    "Kosamba": {"lat": 21.464459923454399, "lon": 72.952089010333296},
    "Kosamba_Vankal": {"lat": 21.43, "lon": 73.23},
    "Kosamba_Zangvav": {"lat": 21.48, "lon": 72.95},
    "Mahuva": {"lat": 21.097129557468101, "lon": 71.760557527893894},
    "Mahuva_Anaval": {"lat": 20.84, "lon": 73.26},
    "Mandvi": {"lat": 21.259469954916099, "lon": 73.306064794408599},
    "Nizar": {"lat": 21.47, "lon": 74.19},
    "Nizar_Kukarmuda": {"lat": 21.51, "lon": 74.13},
    "Nizar_Pumkitalov": {"lat": 21.47, "lon": 74.10},
    "Songadh": {"lat": 21.175868577082898, "lon": 73.564033008192197},
    "Songadh_Badarpada": {"lat": 21.16, "lon": 73.56},
    "Songadh_Umrada": {"lat": 21.16, "lon": 73.56},
    "Surat": {"lat": 21.193417012914299, "lon": 72.852982768754401},
    "Uchhal": {"lat": 21.17, "lon": 73.74},
    "Valod_Buhari": {"lat": 20.97, "lon": 73.31},
    "Vyara_Paati": {"lat": 21.11, "lon": 73.38},
    "Vyra": {"lat": 21.112412216859902, "lon": 73.388557572057493},
    "Amreli": {"lat": 21.559338614206901, "lon": 71.227430257825006},
    "Babra": {"lat": 21.848355060711398, "lon": 71.311297950245503},
    "Bagasara": {"lat": 21.496945117777699, "lon": 70.959329215009802},
    "Dhari": {"lat": 21.331365216974699, "lon": 71.023828198856805},
    "Rajula": {"lat": 21.0339169150099, "lon": 71.443913765569206},
    "Savarkundla": {"lat": 21.332621199094, "lon": 71.313830460040407},
    "Ahmedabad_Chimanbhai_Patal_Market_Vasana": {"lat": 22.996976855033001, "lon": 72.536392460074595},
    "Bavla": {"lat": 22.830965521422801, "lon": 72.3579378735662},
    "Dhandhuka": {"lat": 22.377117706820101, "lon": 71.978523283421794},
    "Dholka": {"lat": 22.7212505077608, "lon": 72.448905310358995},
    "Mandal": {"lat": 23.282162015159599, "lon": 71.915345532018506},
    "Sanad": {"lat": 22.997609695821499, "lon": 72.381634273951903},
    "Viramgam": {"lat": 23.125945592319901, "lon": 72.045712191155303}
}

# 3. SETTINGS
BASE_URL = "https://api.weatherbit.io/v2.0/history/daily"
START_DATE = '2024-01-01'
END_DATE = '2024-12-31'

# Columns to remove from the final CSV
COLUMNS_TO_DROP = ['snow_rate', 'weather.icon', 'revision_version', 'timestamp_utc']

# Checkpoint file to resume progress
PROGRESS_FILE = 'scrape_progress.json'

# --- END CONFIGURATION ---

def load_progress():
    """Loads the progress file if it exists."""
    if os.path.exists(PROGRESS_FILE):
        print(f"Loading progress from {PROGRESS_FILE}...")
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    print("No progress file found, starting from scratch.")
    return {}

def save_progress(progress):
    """Saves the current progress to the checkpoint file."""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=4)

def fetch_weather_for_market(market_name, lat, lon, start_date_str, end_date_str, output_file, progress):
    """
    Fetches weather data for a single market, starting from start_date_str.
    Includes API key rotation and saves progress *per day*.
    """
    global current_key_index
    
    print(f"\n--- Processing Market: {market_name} ---")
    print(f"Period: {start_date_str} to {end_date_str}")
    
    try:
        # Create the date range to iterate over
        date_range = pd.date_range(start=start_date_str, end=end_date_str, freq='D')
    except Exception as e:
        print(f"Error: Invalid date range. Start: {start_date_str}, End: {END_DATE}. {e}")
        return False # Signal failure

    if date_range.empty:
        print("Date range is empty, nothing to fetch.")
        return True # Signal success (nothing to do)

    all_data = [] # Master list for this market's records
    
    print(f"Total days to query for this market: {len(date_range)}.")
    
    # Check if a partial CSV already exists from a previous run
    if os.path.exists(output_file):
        print(f"Found existing file: {output_file}. Appending new data.")
        try:
            # Load existing data to avoid re-writing it
            df_existing = pd.read_csv(output_file)
            # Convert to list of dicts to easily append
            all_data = df_existing.to_dict('records')
            print(f"Loaded {len(all_data)} existing records.")
        except Exception as e:
            print(f"Warning: Could not read existing CSV {output_file}. Will start fresh. Error: {e}")
            all_data = []
    else:
        print(f"Creating new file: {output_file}")
    
    # Use tqdm for a nice progress bar
    pbar = tqdm(date_range, desc=f"Fetching for {market_name}")
    for day_start in pbar:
        
        current_start_date = day_start.strftime('%Y-%m-%d')
        current_end_date = (day_start + timedelta(days=1)).strftime('%Y-%m-%d')
        
        day_fetched = False
        
        # Loop to handle API key rotation and retries for a single day
        while not day_fetched:
            if current_key_index >= len(API_KEYS):
                tqdm.write("\nCRITICAL: All API keys are exhausted. Stopping script.")
                tqdm.write("Run the script again tomorrow (or add new keys) to resume.")
                return False # Signal failure (keys exhausted)

            # Get the current API key
            current_key = API_KEYS[current_key_index]
            pbar.set_postfix_str(f"Key: ...{current_key[-4:]}")

            params = {
                'lat': lat,
                'lon': lon,
                'start_date': current_start_date,
                'end_date': current_end_date,
                'key': current_key
            }
            
            try:
                # Make the API request
                response = requests.get(BASE_URL, params=params)
                
                # Check for HTTP errors (4xx, 5xx)
                response.raise_for_status() 
                
                # Extract the JSON data
                data = response.json()
                
                # The actual weather records are in the 'data' key
                if 'data' in data and data['data']:
                    all_data.extend(data['data'])
                else:
                    tqdm.write(f"Warning: No data found for {current_start_date}")

                day_fetched = True # Success! Move to the next day
                
                # --- THIS IS THE CHECKPOINT ---
                # Save progress *after* a successful day fetch
                next_start_date = (day_start + timedelta(days=1)).strftime('%Y-%m-%d')
                progress[market_name] = next_start_date
                save_progress(progress)
                # -----------------------------

                time.sleep(0.2) # Be polite to the API

            except requests.exceptions.HTTPError as e:
                if e.response.status_code in [403, 429]:
                    # 403 (Forbidden) or 429 (Too Many Requests)
                    tqdm.write(f"\nWarning: Key ...{current_key[-4:]} failed (Rate Limit/Auth). Trying next key.")
                    current_key_index += 1 # Move to the next key
                    # The loop will retry this day with the new key
                else:
                    tqdm.write(f"\nHTTP Error on {current_start_date}: {e}. Retrying after 10s...")
                    time.sleep(10)
            
            except requests.exceptions.RequestException as e:
                tqdm.write(f"\nNetwork error on {current_start_date}: {e}. Retrying after 10s...")
                time.sleep(10)
            
            except Exception as e:
                tqdm.write(f"\nAn unexpected error occurred on {current_start_date}: {e}. Skipping day.")
                break # Stop trying this day and move on

    # --- End of date loop ---

    if not all_data:
        print(f"No data was fetched for {market_name}. Check parameters and API plan.")
        return True # Return True to continue to the next market

    print(f"\nSuccessfully fetched {len(all_data)} total records for {market_name}.")
    
    # Process the data with Pandas
    try:
        print("Processing data into flat DataFrame (using json_normalize)...")
        # Use json_normalize for robust nested JSON handling
        df = pd.json_normalize(all_data)
        
        # Remove duplicate rows that might have come from re-runs
        # Use 'timestamp' or 'ts' if available, 'datetime' is good for daily
        if 'datetime' in df.columns:
            df = df.drop_duplicates(subset=['datetime'])
            print(f"Dropped duplicates, {len(df)} unique records remain.")
        
        # --- Drop unwanted columns ---
        # Check which of the columns to drop actually exist in the DataFrame
        existing_cols_to_drop = [col for col in COLUMNS_TO_DROP if col in df.columns]
        if existing_cols_to_drop:
            print(f"Dropping columns: {existing_cols_to_drop}")
            df = df.drop(columns=existing_cols_to_drop)
        else:
            print("No columns to drop were found.")
        # --- End of drop ---
        
        print(f"Saving data to {output_file}...")
        df.to_csv(output_file, index=False)
        
        print(f"\nSuccessfully saved all data for {market_name} to {output_file}")
        
    except Exception as e:
        print(f"Error processing data with Pandas or saving to CSV: {e}")
        
    return True # Signal success, move to next market

def main():
    """
    Main function to iterate over markets and call the fetcher.
    Manages overall progress and resumes from checkpoints.
    """
    # This try block handles the --f=... argument from jupyter
    try:
        import argparse
        parser = argparse.ArgumentParser()
        # We don't add any arguments, we just want to parse_known_args
        # to ignore jupyter's --f argument
        parser.parse_known_args()
    except:
        pass

    if not MARKETS:
        print("Error: The 'MARKETS' dictionary is empty. Please add markets to scrape.")
        sys.exit(1)
        
    if not API_KEYS:
        print("Error: The 'API_KEYS' list is empty. Please add at least one API key.")
        sys.exit(1)
        
    print(f"--- Starting Weatherbit Batch Scraper ---")
    print(f"Found {len(MARKETS)} markets to process.")
    
    # Load progress from checkpoint file
    progress = load_progress()
    
    # Loop over each market defined in the config
    for market_name, coords in MARKETS.items():
        
        # Check the status of this market
        market_status = progress.get(market_name)
        
        if market_status == "completed":
            print(f"Skipping '{market_name}': Already marked as 'completed'.")
            continue
            
        # Determine the start date for this market
        # If it's not in progress, use the global START_DATE
        # If it is in progress, use the date from the progress file
        current_start_date = START_DATE if not market_status else market_status
        
        # Check if the start date is already past the end date (edge case)
        if pd.to_datetime(current_start_date) > pd.to_datetime(END_DATE):
            print(f"Skipping '{market_name}': Progress file shows it is finished.")
            progress[market_name] = "completed"
            save_progress(progress)
            continue
            
        output_file = f"{market_name}_weather_{START_DATE}_to_{END_DATE}.csv"
        
        # Call the main fetching function for this market
        success = fetch_weather_for_market(
            market_name,
            coords['lat'],
            coords['lon'],
            current_start_date, # Start from where we left off
            END_DATE,
            output_file,
            progress # Pass the progress object to be updated
        )
        
        if not success:
            # This happens if all API keys are exhausted
            print("Batch process stopped due to API key exhaustion.")
            print("Run the script again later to resume from the last checkpoint.")
            break # Stop iterating over markets
        
        # If the fetcher finished without exhausting keys, it means this market is done
        progress[market_name] = "completed"
        save_progress(progress)
        print(f"--- Completed market: {market_name}. Marked as 'completed'. ---")
        time.sleep(1) # Small delay between markets
        
    print("--- Batch processing finished. ---")

if __name__ == "__main__":
    main()