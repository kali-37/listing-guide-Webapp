# Multi-Seller eBay Scraper

A Streamlit-based web application for concurrent scraping of multiple sellers and categories on eBay with real-time progress monitoring and data export capabilities.

## Features

- 🔄 Concurrent scraping with adjustable concurrency levels
- 👥 Multi-seller support
- 📑 Multiple category filtering
- 📊 Real-time progress monitoring
- 📤 CSV export functionality
- 🎛️ Configurable request delays to prevent rate limiting
- 🌐 Web interface built with Streamlit

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/multi-seller-ebay-scraper.git
cd multi-seller-ebay-scraper
```

2. Create a virtual environment and install dependencies using uv:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

## Usage

1. Start the Streamlit application:
```bash
streamlit run app.py
```

2. Access the web interface (default: http://localhost:8501)

3. In the sidebar:
   - Add seller names
   - Select categories to scrape
   - Adjust concurrent request settings
   - Set delay between requests
   - Specify output filename

4. Click "Start Scrape" to begin the scraping process

5. Monitor progress through the live logs

6. Download the CSV file when scraping is complete

## Configuration

### Concurrency Settings

- **Max Concurrency**: Control the number of concurrent requests (1-15)
  - Lower values are recommended for shared instances
  - Default: 2

- **Delay after request**: Set the delay between concurrent requests (0-10 seconds)
  - Higher values reduce the risk of rate limiting
  - Default: 0

### File Management

- Output files are stored in the `data` directory
- Log files are stored in the `logs` directory
- Files are automatically cleaned up after download

## Cloud Deployment

The application is hosted at:
[https://kali-37-listing-guide-webapp-srcapp-4aosuh.streamlit.app/](https://kali-37-listing-guide-webapp-srcapp-4aosuh.streamlit.app/)

Note: Live logs and data downloads require running the application on your own server or using a paid Streamlit cloud service.

## Project Structure

```
.
├── app.py                 # Streamlit web application
├── scrapper.py           # Core scraping functionality
├── category_dict.py      # Category definitions
├── requirements.txt      # Project dependencies
├── pyproject.toml        # Project metadata
├── data/                 # CSV output directory
└── logs/                 # Log file directory
```

## Dependencies

- streamlit
- httpx
- beautifulsoup4
- asyncio
- streamlit-autorefresh

## License

Under MIT License
