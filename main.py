import os
import time
import json
import asyncio
import httpx
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query, Security, status, Body
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import random
from datetime import timedelta
from fastapi.responses import RedirectResponse

# Load environment variables
load_dotenv()

# Configuration
WORDPRESS_URL = os.getenv("WORDPRESS_URL", "https://wordpress-1368009-5111398.cloudwaysapps.com")
API_KEY = os.getenv("API_KEY", "")
REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL", "300"))  # Default: refresh every 5 minutes
FASTAPI_API_KEY = os.getenv("FASTAPI_API_KEY", "")
DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"
USE_SAMPLE_DATA = os.getenv("CONNECTION_ERROR_TEST", "true").lower() == "true"
# WordPress credentials for app password authentication
WORDPRESS_APP_USERNAME = os.getenv("WORDPRESS_APP_USERNAME", "rana1")
WORDPRESS_APP_PASSWORD = os.getenv("WORDPRESS_APP_PASSWORD", "TSQJ TqlX aI1y waL0 VxK0 eHoO")

print(f"Starting with WordPress URL: {WORDPRESS_URL}")
print(f"Debug mode: {DEBUG_MODE}")
print(f"Using sample data: {USE_SAMPLE_DATA}")
print(f"WordPress REST API Authentication: {'Enabled' if WORDPRESS_APP_USERNAME and WORDPRESS_APP_PASSWORD else 'Disabled'}")

# Sample data for development/testing
SAMPLE_PRODUCTS = [
    {"Product_id": "prod001", "Product_name": "eSIM 5GB Global", "GB": "5GB", "Days": "30", "Price_group": "1", "Price_USD_5": "29.99"},
    {"Product_id": "prod002", "Product_name": "eSIM 10GB Global", "GB": "10GB", "Days": "30", "Price_group": "2", "Price_USD_10": "49.99"},
    {"Product_id": "prod003", "Product_name": "eSIM 3GB Europe", "GB": "3GB", "Days": "7", "Price_group": "1", "Price_USD_5": "19.99"},
    {"Product_id": "prod004", "Product_name": "eSIM 20GB USA", "GB": "20GB", "Days": "14", "Price_group": "3", "Price_USD_15": "39.99"}
]

SAMPLE_COUNTRIES = [
    {"Country_Code": "US", "Country_Region": "North America", "IS_REGION": 0, "Price_group": "1", "Continent": "North America"},
    {"Country_Code": "CA", "Country_Region": "North America", "IS_REGION": 0, "Price_group": "1", "Continent": "North America"},
    {"Country_Code": "GB", "Country_Region": "Europe", "IS_REGION": 0, "Price_group": "2", "Continent": "Europe"},
    {"Country_Code": "DE", "Country_Region": "Europe", "IS_REGION": 0, "Price_group": "2", "Continent": "Europe"},
    {"Country_Code": "FR", "Country_Region": "Europe", "IS_REGION": 0, "Price_group": "2", "Continent": "Europe"},
    {"Country_Code": "JP", "Country_Region": "Asia", "IS_REGION": 0, "Price_group": "3", "Continent": "Asia"},
    {"Country_Code": "CN", "Country_Region": "Asia", "IS_REGION": 0, "Price_group": "3", "Continent": "Asia"}
]

app = FastAPI(
    title="eSIM Global API",
    description="API for delivering live eSIM data from WordPress to external applications",
    version="1.0.0"
)

# Add root endpoint to redirect to documentation
@app.get("/", include_in_schema=False)
async def root():
    """Redirect to API documentation"""
    return RedirectResponse(url="/docs")

# Security scheme for API Key authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Data storage
class ESIMData:
    def __init__(self):
        self.products = []
        self.countries = []
        self.last_updated = None
        self.is_updating = False
        
        # Initialize with sample data if enabled
        if USE_SAMPLE_DATA:
            print("Initializing with sample data for development")
            self.products = SAMPLE_PRODUCTS
            self.countries = SAMPLE_COUNTRIES
            self.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Global data store
data_store = ESIMData()

# Enhanced models based on actual data structure
class Product(BaseModel):
    Product_id: str
    Product_name: str
    GB: str
    Days: str
    Price_group: str
    Price_USD_5: Optional[str] = None
    Price_USD_10: Optional[str] = None
    Price_USD_15: Optional[str] = None
    Price_USD_20: Optional[str] = None
    Price_USD_25: Optional[str] = None
    Provider_type: Optional[str] = None
    Provider_name: Optional[str] = None
    Provider_id: Optional[str] = None
    auto_refill: Optional[int] = 0
    extra_field1: Optional[str] = None
    extra_field2: Optional[str] = None
    extra_field3: Optional[str] = None

class Country(BaseModel):
    Country_Code: str
    Country_Region: str
    IS_REGION: int
    Price_group: Optional[str] = None
    Continent: Optional[str] = None
    Provider_id: Optional[str] = None
    Notes: Optional[str] = None

class PriceGroup(BaseModel):
    id: str
    name: Optional[str] = None
    description: Optional[str] = None

class ProductFilter(BaseModel):
    country_code: Optional[str] = None
    price_group: Optional[str] = None
    min_days: Optional[int] = None
    max_days: Optional[int] = None
    min_gb: Optional[float] = None
    max_gb: Optional[float] = None
    provider_id: Optional[str] = None

class DataResponse(BaseModel):
    products: List[Dict[str, Any]]
    countries: List[Dict[str, Any]]
    timestamp: int
    last_updated: Optional[str] = None

# Authentication dependency
async def get_api_key(api_key: str = Security(api_key_header)):
    if FASTAPI_API_KEY and api_key != FASTAPI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    return api_key

# Helper function to parse GB value to float 
def parse_gb(gb_str: str) -> float:
    """Parse GB string (like '5GB') to float value"""
    if not gb_str:
        return 0.0
    try:
        return float(gb_str.replace('GB', '').replace('gb', '').strip())
    except ValueError:
        return 0.0

async def fetch_wordpress_data():
    """Fetch data from WordPress REST API"""
    if data_store.is_updating:
        return
    
    data_store.is_updating = True
    
    try:
        # For development/testing - skip actual API call if using sample data
        if USE_SAMPLE_DATA:
            print("Using sample data - skipping WordPress API call")
            if not data_store.last_updated:
                data_store.products = SAMPLE_PRODUCTS
                data_store.countries = SAMPLE_COUNTRIES
                data_store.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data_store.is_updating = False
            return

        async with httpx.AsyncClient() as client:
            # Set up authentication headers
            headers = {}
            
            # Use app password authentication if configured
            if WORDPRESS_APP_USERNAME and WORDPRESS_APP_PASSWORD:
                # Remove spaces from app password if present
                app_password = WORDPRESS_APP_PASSWORD.replace(" ", "")
                import base64
                auth_string = f"{WORDPRESS_APP_USERNAME}:{app_password}"
                encoded_auth = base64.b64encode(auth_string.encode()).decode()
                headers["Authorization"] = f"Basic {encoded_auth}"
                if DEBUG_MODE:
                    print(f"Using WordPress app password authentication for user: {WORDPRESS_APP_USERNAME}")
            # Fall back to API key if configured
            elif API_KEY:
                headers["Authorization"] = f"Bearer {API_KEY}"
                if DEBUG_MODE:
                    print("Using API key authentication")
            
            # Try the test endpoint first if enabled
            if os.getenv("WORDPRESS_TEST_ENDPOINT", "false").lower() == "true":
                test_url = f"{WORDPRESS_URL}/wp-json/esim-global/v1/test"
                if DEBUG_MODE:
                    print(f"Testing API connectivity with: {test_url}")
                
                try:
                    test_response = await client.get(test_url, headers=headers, timeout=10.0)
                    if test_response.status_code == 200:
                        print(f"Test endpoint successful: {test_response.text}")
                    else:
                        print(f"Test endpoint failed with status {test_response.status_code}: {test_response.text}")
                        print("Plugin may not be registered properly or REST API could be disabled")
                except Exception as e:
                    print(f"Error connecting to test endpoint: {str(e)}")
            
            # Now try the actual data endpoint
            url = f"{WORDPRESS_URL}/wp-json/esim-global/v1/data"
            if DEBUG_MODE:
                print(f"Attempting to connect to: {url}")
            
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                
                if response.status_code == 200:
                    data = response.json()
                    data_store.products = data.get("products", [])
                    data_store.countries = data.get("countries", [])
                    data_store.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"Data updated at {data_store.last_updated}")
                elif response.status_code == 404 and "rest_no_route" in response.text:
                    print("ERROR: WordPress REST API endpoint not found (rest_no_route)")
                    print("The eSIM Global plugin endpoint is not registered. Please check:")
                    print("1. The plugin is activated in WordPress")
                    print("2. Permalinks are updated (visit Settings > Permalinks and save)")
                    print("3. The REST API is not disabled by security plugins")
                    
                    # If fallback enabled, use sample data
                    if os.getenv("ALLOW_SAMPLE_DATA_FALLBACK", "false").lower() == "true":
                        print("Using sample data as fallback due to missing REST API endpoint")
                        data_store.products = SAMPLE_PRODUCTS
                        data_store.countries = SAMPLE_COUNTRIES
                        data_store.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                else:
                    print(f"Error fetching data: HTTP {response.status_code} - {response.text}")
                    # If we get an error but sample data is allowed as fallback
                    if os.getenv("ALLOW_SAMPLE_DATA_FALLBACK", "false").lower() == "true":
                        print("Using sample data as fallback")
                        data_store.products = SAMPLE_PRODUCTS
                        data_store.countries = SAMPLE_COUNTRIES
                        data_store.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            except httpx.ConnectError as e:
                print(f"Connection error: Could not connect to {url}")
                print(f"Details: {str(e)}")
                # Try to determine if the WordPress site is reachable
                try:
                    # Try to connect to the base URL
                    base_url = WORDPRESS_URL.split('/wp-json')[0]
                    print(f"Checking if WordPress site is reachable at: {base_url}")
                    test_response = await client.get(base_url, timeout=10.0)
                    if test_response.status_code < 400:
                        print(f"WordPress site is reachable (status {test_response.status_code}), but the REST API endpoint may not be available.")
                        print("Check if the REST API is enabled in WordPress and the eSIM Global plugin is activated.")
                        # Try accessing the default REST API endpoint
                        try:
                            wp_api_response = await client.get(f"{WORDPRESS_URL}/wp-json", timeout=10.0)
                            if wp_api_response.status_code < 400:
                                print("WordPress REST API is working, but the eSIM Global plugin endpoint is not available.")
                                print("Check if the plugin is activated and properly registering its REST routes.")
                            else:
                                print(f"WordPress REST API is not accessible (status {wp_api_response.status_code})")
                                print("Check WordPress settings and if any security plugins are blocking the REST API.")
                        except Exception as wp_api_e:
                            print(f"Error accessing WordPress REST API: {str(wp_api_e)}")
                    else:
                        print(f"WordPress site returned error status: {test_response.status_code}")
                except Exception as base_e:
                    print(f"WordPress site is not reachable: {str(base_e)}")
                    print("Please check your WORDPRESS_URL setting and ensure the WordPress site is running.")
                
                # Use sample data if fallback is enabled
                if os.getenv("ALLOW_SAMPLE_DATA_FALLBACK", "false").lower() == "true":
                    print("Using sample data as fallback due to connection error")
                    data_store.products = SAMPLE_PRODUCTS
                    data_store.countries = SAMPLE_COUNTRIES
                    data_store.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
            except httpx.TimeoutException:
                print(f"Timeout connecting to {url} - WordPress site may be slow to respond")
                # Use sample data if fallback is enabled
                if os.getenv("ALLOW_SAMPLE_DATA_FALLBACK", "false").lower() == "true":
                    print("Using sample data as fallback due to connection timeout")
                    data_store.products = SAMPLE_PRODUCTS
                    data_store.countries = SAMPLE_COUNTRIES
                    data_store.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            except Exception as e:
                print(f"Error connecting to WordPress: {str(e)}")
                # Use sample data if fallback is enabled
                if os.getenv("ALLOW_SAMPLE_DATA_FALLBACK", "false").lower() == "true":
                    print("Using sample data as fallback due to general error")
                    data_store.products = SAMPLE_PRODUCTS
                    data_store.countries = SAMPLE_COUNTRIES
                    data_store.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print(f"General error updating data: {str(e)}")
        # Use sample data if fallback is enabled
        if os.getenv("ALLOW_SAMPLE_DATA_FALLBACK", "false").lower() == "true":
            print("Using sample data as fallback due to general exception")
            data_store.products = SAMPLE_PRODUCTS
            data_store.countries = SAMPLE_COUNTRIES
            data_store.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    finally:
        data_store.is_updating = False

async def background_data_refresh():
    """Continuously refresh data in the background"""
    while True:
        try:
            await fetch_wordpress_data()
        except Exception as e:
            print(f"Error in background refresh: {str(e)}")
        await asyncio.sleep(REFRESH_INTERVAL)

@app.on_event("startup")
async def startup_event():
    """Initialize data and start background refresh task"""
    # Fetch data on startup
    await fetch_wordpress_data()
    
    # Start background task for continuous data refresh
    asyncio.create_task(background_data_refresh())

@app.get("/api/esim-data", response_model=DataResponse)
async def get_esim_data(api_key: str = Depends(get_api_key)):
    """Get the latest eSIM data"""
    if not data_store.products or not data_store.countries:
        await fetch_wordpress_data()
        if not data_store.products or not data_store.countries:
            raise HTTPException(status_code=503, detail="Data not available yet. Please check server logs for connection issues.")
    
    return {
        "products": data_store.products,
        "countries": data_store.countries,
        "timestamp": int(time.time()),
        "last_updated": data_store.last_updated
    }

@app.get("/api/products")
async def get_products(api_key: str = Depends(get_api_key)):
    """Get all products"""
    if not data_store.products:
        await fetch_wordpress_data()
    
    return {"products": data_store.products, "last_updated": data_store.last_updated}

@app.get("/api/countries")
async def get_countries(api_key: str = Depends(get_api_key)):
    """Get all countries"""
    if not data_store.countries:
        await fetch_wordpress_data()
    
    return {"countries": data_store.countries, "last_updated": data_store.last_updated}

@app.get("/api/products/{product_id}")
async def get_product(product_id: str, api_key: str = Depends(get_api_key)):
    """Get a specific product by ID"""
    if not data_store.products:
        await fetch_wordpress_data()
    
    for product in data_store.products:
        if product.get("Product_id") == product_id:
            return product
    
    raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")

@app.get("/api/products/filter")
async def filter_products(
    country_code: Optional[str] = Query(None, description="Filter by country code"),
    price_group: Optional[str] = Query(None, description="Filter by price group"),
    min_days: Optional[int] = Query(None, description="Minimum days"),
    max_days: Optional[int] = Query(None, description="Maximum days"),
    min_gb: Optional[float] = Query(None, description="Minimum GB"),
    max_gb: Optional[float] = Query(None, description="Maximum GB"),
    provider_id: Optional[str] = Query(None, description="Filter by provider ID"),
    api_key: str = Depends(get_api_key)
):
    """Filter products by various criteria"""
    if not data_store.products:
        await fetch_wordpress_data()

    filtered_products = data_store.products.copy()
    
    # Filter by country code
    if country_code:
        # First identify the price group for this country
        target_price_group = None
        for country in data_store.countries:
            if country.get("Country_Code") == country_code:
                target_price_group = country.get("Price_group")
                break
        
        if target_price_group:
            filtered_products = [p for p in filtered_products if p.get("Price_group") == target_price_group]
        else:
            # If no price group found for this country, return empty list
            return {"products": [], "last_updated": data_store.last_updated}
    
    # Filter by price group directly
    if price_group:
        filtered_products = [p for p in filtered_products if p.get("Price_group") == price_group]
    
    # Filter by days
    if min_days is not None:
        filtered_products = [p for p in filtered_products if p.get("Days") and int(p.get("Days", 0)) >= min_days]
    
    if max_days is not None:
        filtered_products = [p for p in filtered_products if p.get("Days") and int(p.get("Days", 0)) <= max_days]
    
    # Filter by GB (need to convert from string like "5GB" to float)
    if min_gb is not None:
        filtered_products = [p for p in filtered_products if parse_gb(p.get("GB", "0")) >= min_gb]
    
    if max_gb is not None:
        filtered_products = [p for p in filtered_products if parse_gb(p.get("GB", "0")) <= max_gb]
    
    # Filter by provider ID
    if provider_id:
        filtered_products = [p for p in filtered_products if p.get("Provider_id") == provider_id]
    
    return {"products": filtered_products, "last_updated": data_store.last_updated}

@app.get("/api/countries/region/{region_code}")
async def get_countries_by_region(
    region_code: str, 
    api_key: str = Depends(get_api_key)
):
    """Get countries by region code"""
    if not data_store.countries:
        await fetch_wordpress_data()
    
    filtered_countries = [c for c in data_store.countries if c.get("Country_Region") == region_code]
    
    return {"countries": filtered_countries, "last_updated": data_store.last_updated}

@app.get("/api/price-groups")
async def get_price_groups(api_key: str = Depends(get_api_key)):
    """Get all unique price groups"""
    if not data_store.products:
        await fetch_wordpress_data()
    
    # Get unique price groups
    price_groups = set()
    for product in data_store.products:
        if "Price_group" in product and product["Price_group"]:
            price_groups.add(product["Price_group"])
    
    return {"price_groups": sorted(list(price_groups)), "last_updated": data_store.last_updated}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "timestamp": int(time.time()),
        "last_updated": data_store.last_updated or "never",
        "wordpress_url": WORDPRESS_URL,
        "connection_status": "connected" if data_store.last_updated else "disconnected",
        "using_sample_data": USE_SAMPLE_DATA
    }

@app.get("/api/debug")
async def debug_info(api_key: str = Depends(get_api_key)):
    """Get debug information about the current configuration"""
    try:
        async with httpx.AsyncClient() as client:
            base_url = WORDPRESS_URL
            base_api_url = f"{WORDPRESS_URL}/wp-json"
            plugin_url = f"{WORDPRESS_URL}/wp-json/esim-global/v1/data"
            
            base_reachable = False
            base_api_reachable = False
            plugin_api_reachable = False
            base_error = None
            base_api_error = None
            plugin_error = None
            plugin_data = None
            
            if not USE_SAMPLE_DATA:
                try:
                    base_response = await client.get(base_url, timeout=10.0)
                    base_reachable = base_response.status_code < 400
                except Exception as e:
                    base_error = str(e)
                
                try:
                    base_api_response = await client.get(base_api_url, timeout=10.0)
                    base_api_reachable = base_api_response.status_code < 400
                except Exception as e:
                    base_api_error = str(e)
                    
                try:
                    plugin_response = await client.get(plugin_url, timeout=10.0)
                    plugin_api_reachable = plugin_response.status_code < 400
                    plugin_data = plugin_response.text[:100] + "..." if plugin_response.status_code < 400 else None
                except Exception as e:
                    plugin_error = str(e)
            
            return {
                "config": {
                    "wordpress_url": WORDPRESS_URL,
                    "refresh_interval": REFRESH_INTERVAL,
                    "debug_mode": DEBUG_MODE,
                    "using_sample_data": USE_SAMPLE_DATA,
                    "environment_variables": {
                        "CONNECTION_ERROR_TEST": os.getenv("CONNECTION_ERROR_TEST", "not set"),
                        "DEBUG_MODE": os.getenv("DEBUG_MODE", "not set")
                    }
                },
                "connection_tests": {
                    "wordpress_base_url": {
                        "url": base_url,
                        "reachable": base_reachable if not USE_SAMPLE_DATA else "skipped (using sample data)",
                        "error": base_error
                    },
                    "wordpress_api_base": {
                        "url": base_api_url,
                        "reachable": base_api_reachable if not USE_SAMPLE_DATA else "skipped (using sample data)",
                        "error": base_api_error
                    },
                    "esim_plugin_endpoint": {
                        "url": plugin_url,
                        "reachable": plugin_api_reachable if not USE_SAMPLE_DATA else "skipped (using sample data)",
                        "error": plugin_error,
                        "sample_data": plugin_data
                    }
                },
                "data_store": {
                    "has_products": len(data_store.products) > 0,
                    "product_count": len(data_store.products),
                    "has_countries": len(data_store.countries) > 0,
                    "country_count": len(data_store.countries),
                    "last_updated": data_store.last_updated
                }
            }
    except Exception as e:
        return {
            "error": f"Error running diagnostics: {str(e)}",
            "config": {
                "wordpress_url": WORDPRESS_URL,
                "refresh_interval": REFRESH_INTERVAL,
                "using_sample_data": USE_SAMPLE_DATA
            }
        }

# Additional models for SimTLV API integration
class SubscriberRequest(BaseModel):
    phone_number: str = Field(..., description="Subscriber's phone number")
    email: Optional[str] = Field(None, description="Subscriber's email address")

class SubscriberResponse(BaseModel):
    subscriber_id: str = Field(..., description="Unique identifier for the subscriber")
    phone_number: str = Field(..., description="Subscriber's phone number")
    email: Optional[str] = Field(None, description="Subscriber's email address")
    status: str = Field(..., description="Subscriber status (active, suspended, etc.)")
    created_at: str = Field(..., description="Date and time when subscriber was created")

class PlanInfo(BaseModel):
    plan_id: str = Field(..., description="Unique identifier for the plan")
    name: str = Field(..., description="Name of the plan")
    description: str = Field(..., description="Description of the plan")
    data_amount: str = Field(..., description="Amount of data included in the plan")
    validity_days: int = Field(..., description="Number of days the plan is valid for")
    price: float = Field(..., description="Price of the plan")
    currency: str = Field(..., description="Currency for the price")

class TopupPlan(BaseModel):
    plan_id: str
    template_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    data_amount: str
    validity_days: int
    price: float
    currency: str = "ILS"
    supported_regions: Optional[List[str]] = None
    supported_countries: Optional[List[str]] = None

class TopupPlansResponse(BaseModel):
    status: str
    plans: List[TopupPlan]
    count: int

class TopupRequest(BaseModel):
    iccid: str = Field(..., description="The ICCID of the eSIM to topup")
    plan_id: str = Field(..., description="The ID of the topup plan to apply")
    payment_reference: Optional[str] = Field(None, description="Optional payment reference for tracking")

class TopupResponse(BaseModel):
    status: str
    message: str
    transaction_id: Optional[str] = None
    iccid: str
    plan_id: str
    activation_date: Optional[str] = None
    expiry_date: Optional[str] = None
    provider_reference: Optional[str] = None

class TopupHistoryItem(BaseModel):
    transaction_id: str
    plan_id: str
    plan_name: str
    created_at: str
    activation_date: str
    expiry_date: str
    amount: str
    price: str
    currency: str
    status: str

class TopupHistoryResponse(BaseModel):
    status: str
    iccid: str
    history: List[TopupHistoryItem]
    count: int

class ESIMRequest(BaseModel):
    package_id: str = Field(..., description="Package ID to download eSIM for")

class ESIMResponse(BaseModel):
    esim_qr_code: str = Field(..., description="Base64 encoded QR code for eSIM installation")
    activation_code: str = Field(..., description="eSIM activation code")
    instructions: str = Field(..., description="Installation instructions")

class PackageUsage(BaseModel):
    package_id: str = Field(..., description="Package ID")
    total_data: str = Field(..., description="Total data in the package")
    used_data: str = Field(..., description="Amount of data used")
    remaining_data: str = Field(..., description="Remaining data")
    expiry_date: str = Field(..., description="Expiry date of the package")
    status: str = Field(..., description="Package status")

# Add ICCID lookup models
class ICCIDInfo(BaseModel):
    iccid: str = Field(..., description="The ICCID of the eSIM")
    subscriber_id: Optional[str] = Field(None, description="Associated subscriber ID")
    status: str = Field(..., description="Status of the eSIM (active, inactive, etc.)")
    activation_date: Optional[str] = Field(None, description="When the eSIM was activated")
    expiry_date: Optional[str] = Field(None, description="When the eSIM expires")
    plan_id: Optional[str] = Field(None, description="Associated plan ID")
    plan_name: Optional[str] = Field(None, description="Name of the plan")
    total_data: Optional[str] = Field(None, description="Total data allocation")
    used_data: Optional[str] = Field(None, description="Data used so far")
    remaining_data: Optional[str] = Field(None, description="Remaining data")
    provider_reference: Optional[str] = Field(None, description="Reference ID in the provider's system")
    last_updated: Optional[str] = Field(None, description="When this data was last updated")
    data_source: Optional[str] = Field(None, description="Source of the data (telco_vision, wordpress_fallback, or sample_data)")

class ICCIDInfoDetailed(ICCIDInfo):
    usage_history: Optional[List[Dict[str, Any]]] = Field(None, description="Recent usage history")
    connectivity_status: Optional[str] = Field(None, description="Current connectivity status")
    location: Optional[str] = Field(None, description="Last known location/country")
    customer_details: Optional[Dict[str, Any]] = Field(None, description="Customer information")

# Add ICCID-related configuration
ESIM_PROVIDER_API_URL = os.getenv("ESIM_PROVIDER_API_URL", "")
ESIM_PROVIDER_API_KEY = os.getenv("ESIM_PROVIDER_API_KEY", "")
ESIM_PROVIDER_CLIENT_ID = os.getenv("ESIM_PROVIDER_CLIENT_ID", "")
ESIM_PROVIDER_CLIENT_SECRET = os.getenv("ESIM_PROVIDER_CLIENT_SECRET", "")

# Add ICCID lookup function
async def fetch_iccid_data(iccid: str) -> Dict[str, Any]:
    """
    Fetch ICCID data from WordPress (primary) or TelcoVision OCS API (fallback)
    """
    if DEBUG_MODE:
        print(f"Fetching ICCID data for: {iccid}")
    
    # First try to get data from WordPress (PRIMARY SOURCE)
    try:
        # Get data from WordPress as the primary source
        wordpress_data = await fetch_iccid_data_from_wordpress(iccid)
        
        # Check if we got valid data from WordPress
        if wordpress_data and "not_found" not in wordpress_data and "error" not in wordpress_data:
            if DEBUG_MODE:
                print(f"Successfully retrieved data from WordPress for ICCID {iccid}")
            
            # Add data source indicator
            if "source" not in wordpress_data:
                wordpress_data["source"] = "wordpress_primary"
                
            return wordpress_data
        else:
            # If WordPress data retrieval failed or returned empty, try TelcoVision as fallback
            print(f"WordPress data not found or invalid for ICCID {iccid}, trying TelcoVision as fallback")
    except Exception as e:
        # If there's an error with WordPress, log it and try TelcoVision
        print(f"Error fetching data from WordPress for ICCID {iccid}: {str(e)}")
        print("Trying TelcoVision as fallback")
    
    # Only proceed with TelcoVision if it's configured
    if os.getenv("ESIM_PROVIDER_API_URL") and os.getenv("ESIM_PROVIDER_API_KEY"):
        try:
            # Get data from TelcoVision OCS API as fallback
            async with httpx.AsyncClient() as client:
                base_url = os.getenv("ESIM_PROVIDER_API_URL")
                api_key = os.getenv("ESIM_PROVIDER_API_KEY")
                headers = {
                    "Content-Type": "application/json",
                    "X-API-KEY": api_key
                }
                
                # Additional credentials if provided
                client_id = os.getenv("ESIM_PROVIDER_CLIENT_ID")
                client_secret = os.getenv("ESIM_PROVIDER_CLIENT_SECRET")
                if client_id and client_secret:
                    headers["X-CLIENT-ID"] = client_id
                    headers["X-CLIENT-SECRET"] = client_secret
                
                # Get subscriber information
                subscriber_url = f"{base_url}/subscribers/{iccid}"
                try:
                    subscriber_response = await client.get(subscriber_url, headers=headers, timeout=30.0)
                    if subscriber_response.status_code != 200:
                        print(f"Error fetching subscriber data from TelcoVision: HTTP {subscriber_response.status_code}")
                        print(f"Response: {subscriber_response.text}")
                        # Return empty data if subscriber not found
                        return {"subscriber": {}, "packages": [], "not_found": True, "source": "telco_vision_fallback"}
                    
                    subscriber_data = subscriber_response.json()
                except httpx.RequestError as e:
                    print(f"Error connecting to TelcoVision for subscriber data: {str(e)}")
                    # Return empty data on connection error
                    return {"subscriber": {}, "packages": [], "error": str(e), "source": "telco_vision_fallback"}
                
                # Get package information
                packages_url = f"{base_url}/subscribers/{iccid}/packages"
                try:
                    packages_response = await client.get(packages_url, headers=headers, timeout=30.0)
                    if packages_response.status_code != 200:
                        print(f"Error fetching package data from TelcoVision: HTTP {packages_response.status_code}")
                        # Still return subscriber data if available
                        return {
                            "subscriber": subscriber_data.get('getSingleSubscriber', {}),
                            "packages": [],
                            "partial_data": True,
                            "source": "telco_vision_fallback"
                        }
                    
                    packages_data = packages_response.json()
                except httpx.RequestError as e:
                    print(f"Error connecting to TelcoVision for package data: {str(e)}")
                    # Still return subscriber data if available
                    return {
                        "subscriber": subscriber_data.get('getSingleSubscriber', {}),
                        "packages": [],
                        "partial_data": True,
                        "error": str(e),
                        "source": "telco_vision_fallback"
                    }
                
                # Combine the data
                combined_data = {
                    "subscriber": subscriber_data.get('getSingleSubscriber', {}),
                    "packages": packages_data.get('listSubscriberPrepaidPackages', {}).get('packages', []),
                    "source": "telco_vision_fallback"
                }
                
                if DEBUG_MODE:
                    print(f"Successfully fetched data from TelcoVision for ICCID {iccid}")
                    
                return combined_data
        except Exception as e:
            print(f"General error fetching ICCID data from TelcoVision: {str(e)}")
    else:
        if DEBUG_MODE:
            print("TelcoVision OCS API not configured, skipping fallback")
    
    # If we couldn't get data from WordPress or TelcoVision, return sample data if allowed
    if os.getenv("ALLOW_SAMPLE_DATA_FALLBACK", "false").lower() == "true":
        print(f"Returning sample data for ICCID {iccid} as final fallback")
        return {
            "subscriber": {
                "sim": {
                    "id": f"sample_{iccid[-6:]}",
                    "state": "ACTIVATED"
                }
            },
            "packages": [
                {
                    "id": "sample_package_001",
                    "name": "Sample Global 10GB Package",
                    "active": True,
                    "pckdatabyte": 10 * 1024 * 1024 * 1024,  # 10GB in bytes
                    "useddatabyte": 1 * 1024 * 1024 * 1024,   # 1GB in bytes
                    "tsactivationutc": (datetime.now() - timedelta(days=5)).isoformat(),
                    "tsexpirationutc": (datetime.now() + timedelta(days=25)).isoformat()
                }
            ],
            "source": "sample_data"
        }
    else:
        # Return empty data if all options failed and sample data is not allowed
        return {"subscriber": {}, "packages": [], "error": "No data available from any source", "source": "none"}

async def fetch_iccid_data_from_wordpress(iccid: str) -> Dict[str, Any]:
    """
    Fetch ICCID data from WordPress as a fallback when Telco Vision OCS API is unavailable
    """
    if DEBUG_MODE:
        print(f"Fetching ICCID data from WordPress for: {iccid}")
    
    try:
        async with httpx.AsyncClient() as client:
            # Set up WordPress API URL for ICCID lookup
            url = f"{WORDPRESS_URL}/wp-json/esim-global/v1/iccid/{iccid}"
            
            # Set up authentication headers
            headers = {}
            if WORDPRESS_APP_USERNAME and WORDPRESS_APP_PASSWORD:
                # Remove spaces from app password if present
                app_password = WORDPRESS_APP_PASSWORD.replace(" ", "")
                import base64
                auth_string = f"{WORDPRESS_APP_USERNAME}:{app_password}"
                encoded_auth = base64.b64encode(auth_string.encode()).decode()
                headers["Authorization"] = f"Basic {encoded_auth}"
            elif API_KEY:
                headers["Authorization"] = f"Bearer {API_KEY}"
            
            if DEBUG_MODE:
                print(f"Making request to WordPress API: {url}")
            
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                
                if response.status_code == 200:
                    wordpress_data = response.json()
                    if DEBUG_MODE:
                        print(f"Successfully fetched ICCID data from WordPress for {iccid}")
                    
                    # Convert WordPress data to the format expected by the ICCID endpoint
                    wp_formatted_data = {
                        "subscriber": {
                            "sim": {
                                "id": wordpress_data.get("subscriber_id", ""),
                                "state": "ACTIVATED" if wordpress_data.get("status") == "active" else "UNAVAILABLE"
                            }
                        },
                        "packages": []
                    }
                    
                    # Add package data if available
                    if wordpress_data.get("plan_id") and wordpress_data.get("total_data"):
                        # Convert data strings like "5GB" to bytes (approximate)
                        def parse_data_to_bytes(data_str):
                            try:
                                # Remove 'GB' and convert to bytes (1 GB = 1024^3 bytes)
                                gb_value = float(data_str.replace('GB', '').strip())
                                return int(gb_value * 1024 * 1024 * 1024)
                            except:
                                return 0
                        
                        total_bytes = parse_data_to_bytes(wordpress_data.get("total_data", "0GB"))
                        used_bytes = parse_data_to_bytes(wordpress_data.get("used_data", "0GB"))
                        
                        wp_formatted_data["packages"].append({
                            "id": wordpress_data.get("plan_id", ""),
                            "name": wordpress_data.get("plan_name", "WordPress Plan"),
                            "active": True,
                            "pckdatabyte": total_bytes,
                            "useddatabyte": used_bytes,
                            "tsactivationutc": wordpress_data.get("activation_date", datetime.now().isoformat()),
                            "tsexpirationutc": wordpress_data.get("expiry_date", (datetime.now() + timedelta(days=30)).isoformat())
                        })
                    
                    return wp_formatted_data
                elif response.status_code == 404:
                    if DEBUG_MODE:
                        print(f"ICCID {iccid} not found in WordPress")
                    
                    # Return mock data structure for not found
                    return {
                        "subscriber": {},
                        "packages": [],
                        "not_found": True,
                        "source": "wordpress_fallback"
                    }
                else:
                    print(f"Error fetching ICCID from WordPress: HTTP {response.status_code} - {response.text}")
                    # Return empty data structure for error
                    return {
                        "subscriber": {},
                        "packages": [],
                        "error": f"WordPress API returned {response.status_code}",
                        "source": "wordpress_fallback"
                    }
            except httpx.RequestError as e:
                print(f"Error connecting to WordPress for ICCID lookup: {str(e)}")
                return {
                    "subscriber": {},
                    "packages": [],
                    "error": f"Connection error: {str(e)}",
                    "source": "wordpress_fallback"
                }
    except Exception as e:
        print(f"General error fetching ICCID data from WordPress: {str(e)}")
        return {
            "subscriber": {},
            "packages": [],
            "error": f"General error: {str(e)}",
            "source": "wordpress_fallback"
        }

# Add ICCID lookup endpoints
@app.get("/api/iccid/{iccid}", response_model=ICCIDInfo)
async def get_iccid_info(iccid: str, api_key: str = Depends(get_api_key)):
    """
    Get information about an eSIM using its ICCID, primarily from WordPress
    """
    if DEBUG_MODE:
        print(f"ICCID lookup request received for: {iccid}")
    
    try:
        # Fetch data from WordPress as primary source, with fallbacks if needed
        response_data = await fetch_iccid_data(iccid)
        
        if DEBUG_MODE:
            print(f"Data source: {response_data.get('source', 'unknown')}")
            
        # Check if data is empty or has error
        if response_data.get("not_found", False) or not response_data.get("subscriber", {}):
            if DEBUG_MODE:
                print(f"No data found for ICCID: {iccid}")
            raise HTTPException(
                status_code=404, 
                detail=f"No data found for ICCID: {iccid}. Please check the ICCID and try again."
            )
        
        # Populate response based on the data source
        data_source = response_data.get("source", "unknown")
        
        # Extract subscriber data
        subscriber = response_data.get("subscriber", {})
        packages = response_data.get("packages", [])
        
        # Initialize the response with the ICCID and data source
        result = {
            "iccid": iccid,
            "data_source": data_source
        }
        
        if data_source == "wordpress_primary":
            # WordPress data format
            result["subscriber_id"] = subscriber.get("sim_id", f"sub_{iccid[-6:]}")
            result["status"] = subscriber.get("status", "active")
            result["provider_reference"] = subscriber.get("sim_id", "")
            result["country"] = subscriber.get("country", "")
            result["network"] = subscriber.get("network", "")
            result["last_updated"] = subscriber.get("last_updated", datetime.now().isoformat())
            
            # Get data from the first package
            if packages and len(packages) > 0:
                active_package = packages[0]
                
                result["activation_date"] = active_package.get("activation_date", "")
                result["expiry_date"] = active_package.get("expiry_date", "")
                result["plan_id"] = active_package.get("plan_id", "")
                result["plan_name"] = active_package.get("plan_name", "")
                result["total_data"] = active_package.get("total_data", "")
                result["used_data"] = active_package.get("used_data", "")
                result["remaining_data"] = active_package.get("remaining_data", "")
            
        elif data_source == "telco_vision_fallback":
            # Extract TelcoVision data
            sim = subscriber.get("sim", {})
            
            # Basic subscriber info
            result["subscriber_id"] = sim.get("id", f"sub_{iccid[-6:]}")
            result["status"] = sim.get("state", "UNKNOWN").lower()
            result["provider_reference"] = sim.get("id", "")
            result["last_updated"] = datetime.now().isoformat()
            
            # Get data from the first active package
            active_packages = [p for p in packages if p.get("active", False)]
            if active_packages:
                active_package = active_packages[0]
                
                # Get data from the package
                result["activation_date"] = active_package.get("tsactivationutc", "")
                result["expiry_date"] = active_package.get("tsexpirationutc", "")
                result["plan_id"] = f"plan_{active_package.get('id', '')}"
                # Get plan name from template
                template = active_package.get("packageTemplate", {})
                result["plan_name"] = template.get("name", "Unknown Plan")
                
                # Calculate data usage
                total_bytes = active_package.get("pckdatabyte", 0)
                used_bytes = active_package.get("useddatabyte", 0)
                remaining_bytes = total_bytes - used_bytes
                
                # Convert to GB for display with 2 decimal places
                def bytes_to_gb(bytes_val):
                    gb_val = bytes_val / (1024 * 1024 * 1024)
                    return f"{gb_val:.2f}GB"
                
                result["total_data"] = bytes_to_gb(total_bytes)
                result["used_data"] = bytes_to_gb(used_bytes)
                result["remaining_data"] = bytes_to_gb(remaining_bytes)
        
        elif data_source == "sample_data":
            # Sample data format
            sim = subscriber.get("sim", {})
            
            # Basic subscriber info
            result["subscriber_id"] = sim.get("id", f"sub_{iccid[-6:]}")
            result["status"] = sim.get("state", "ACTIVATED").lower()
            result["provider_reference"] = sim.get("id", "")
            result["last_updated"] = datetime.now().isoformat()
            
            # Get data from the first package
            if packages and len(packages) > 0:
                sample_package = packages[0]
                
                # Get data from the sample package
                result["activation_date"] = sample_package.get("tsactivationutc", "")
                result["expiry_date"] = sample_package.get("tsexpirationutc", "")
                result["plan_id"] = f"plan_{sample_package.get('id', '')}"
                result["plan_name"] = sample_package.get("name", "Sample Plan")
                
                # Calculate data usage
                total_bytes = sample_package.get("pckdatabyte", 0)
                used_bytes = sample_package.get("useddatabyte", 0)
                remaining_bytes = total_bytes - used_bytes
                
                # Convert to GB for display
                def bytes_to_gb(bytes_val):
                    gb_val = bytes_val / (1024 * 1024 * 1024)
                    return f"{gb_val:.2f}GB"
                
                result["total_data"] = bytes_to_gb(total_bytes)
                result["used_data"] = bytes_to_gb(used_bytes)
                result["remaining_data"] = bytes_to_gb(remaining_bytes)
        
        if DEBUG_MODE:
            print(f"ICCID response data: {json.dumps(result)}")
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing ICCID request: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error processing ICCID request: {str(e)}"
        )

# SimTLV API Endpoints
@app.post("/api/subscribers/identify", response_model=SubscriberResponse)
async def identify_subscriber(request: SubscriberRequest, api_key: str = Depends(get_api_key)):
    """Identify a subscriber by phone number or create a new one if not found"""
    # This is a placeholder implementation - in a real system, this would check a database
    # For now, we'll generate a fake subscriber response
    return {
        "subscriber_id": f"sub_{hash(request.phone_number) % 10000}",
        "phone_number": request.phone_number,
        "email": request.email,
        "status": "active",
        "created_at": datetime.now().isoformat()
    }

@app.get("/api/plans", response_model=List[PlanInfo])
async def get_plans(api_key: str = Depends(get_api_key)):
    """Get available plans"""
    # This implementation will eventually connect to the WordPress data
    # For now, we'll use placeholder data that references our products
    plans = []
    
    if data_store.products:
        for product in data_store.products[:5]:  # Convert first 5 products to plans
            plans.append({
                "plan_id": product.get("Product_id", "unknown"),
                "name": product.get("Product_name", "Unknown Plan"),
                "description": f"eSIM plan with {product.get('GB', '0')} for {product.get('Days', '0')} days",
                "data_amount": product.get("GB", "0GB"),
                "validity_days": int(product.get("Days", 0)),
                "price": float(product.get("Price_USD_5", 0)) if product.get("Price_USD_5") else 0.0,
                "currency": "USD"
            })
    
    return plans

@app.post("/api/topup", response_model=TopupResponse)
async def process_topup(request: TopupRequest, api_key: str = Depends(get_api_key)):
    """Process a topup/purchase of a plan"""
    # Placeholder implementation
    transaction_id = f"tx_{int(time.time())}_{random.randint(1000, 9999)}"
    package_id = f"pkg_{int(time.time())}_{random.randint(1000, 9999)}"
    
    return {
        "transaction_id": transaction_id,
        "subscriber_id": request.subscriber_id,
        "plan_id": request.plan_id,
        "package_id": package_id,
        "amount": 29.99,  # This would be looked up from the plan
        "currency": "USD",
        "status": "completed",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/subscribers/{subscriber_id}/packages")
async def get_subscriber_packages(subscriber_id: str, api_key: str = Depends(get_api_key)):
    """Get packages belonging to a subscriber"""
    # Placeholder implementation
    return {
        "subscriber_id": subscriber_id,
        "packages": [
            {
                "package_id": f"pkg_{int(time.time())}_{random.randint(1000, 9999)}",
                "plan_id": "sample1",
                "data_amount": "5GB",
                "remaining_data": "3.2GB",
                "activation_date": (datetime.now() - timedelta(days=3)).isoformat(),
                "expiry_date": (datetime.now() + timedelta(days=27)).isoformat(),
                "status": "active"
            }
        ]
    }

@app.post("/api/esim/download", response_model=ESIMResponse)
async def download_esim(request: ESIMRequest, api_key: str = Depends(get_api_key)):
    """Download an eSIM profile"""
    # In a real implementation, this would connect to an eSIM provider API
    # For now, return placeholder data
    return {
        "esim_qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
        "activation_code": "LPA:1$SMDP.EXAMPLE.COM$04386-AGYFT-A7TYQ-66734",
        "instructions": "Scan this QR code with your phone's camera or go to Settings and add eSIM manually using the activation code."
    }

@app.get("/api/packages/{package_id}/usage", response_model=PackageUsage)
async def get_package_usage(package_id: str, api_key: str = Depends(get_api_key)):
    """Get usage information for a specific package"""
    # Placeholder implementation
    return {
        "package_id": package_id,
        "total_data": "5GB",
        "used_data": "1.8GB",
        "remaining_data": "3.2GB",
        "expiry_date": (datetime.now() + timedelta(days=27)).isoformat(),
        "status": "active"
    }

@app.post("/api/packages/{package_id}/auto-renew")
async def set_auto_renew(
    package_id: str, 
    auto_renew: bool = Body(..., embed=True), 
    api_key: str = Depends(get_api_key)
):
    """Enable or disable auto-renewal for a package"""
    return {
        "package_id": package_id,
        "auto_renew": auto_renew,
        "message": f"Auto-renew for package {package_id} has been {'enabled' if auto_renew else 'disabled'}"
    }

@app.get("/api/subscribers/{subscriber_id}/usage-history")
async def get_usage_history(subscriber_id: str, api_key: str = Depends(get_api_key)):
    """Get usage history for a subscriber"""
    # Placeholder implementation
    return {
        "subscriber_id": subscriber_id,
        "usage_history": [
            {
                "date": (datetime.now() - timedelta(days=1)).isoformat(),
                "data_used": "0.8GB",
                "package_id": f"pkg_{int(time.time())}_{random.randint(1000, 9999)}"
            },
            {
                "date": (datetime.now() - timedelta(days=2)).isoformat(),
                "data_used": "1.0GB",
                "package_id": f"pkg_{int(time.time())}_{random.randint(1000, 9999)}"
            }
        ]
    }

@app.post("/api/subscribers/{subscriber_id}/suspend")
async def suspend_subscriber(
    subscriber_id: str, 
    reason: str = Body(..., embed=True), 
    api_key: str = Depends(get_api_key)
):
    """Suspend a subscriber"""
    return {
        "subscriber_id": subscriber_id,
        "status": "suspended",
        "reason": reason,
        "suspension_date": datetime.now().isoformat()
    }

async def fetch_topup_plans() -> List[Dict[str, Any]]:
    """Fetch available topup plans from WordPress"""
    if DEBUG_MODE:
        print("Fetching topup plans from WordPress")
    
    try:
        async with httpx.AsyncClient() as client:
            # Set up WordPress API URL for topup plans
            url = f"{WORDPRESS_URL}/wp-json/esim-global/v1/topup-plans"
            
            # Set up authentication headers
            headers = {}
            if WORDPRESS_APP_USERNAME and WORDPRESS_APP_PASSWORD:
                # Remove spaces from app password if present
                app_password = WORDPRESS_APP_PASSWORD.replace(" ", "")
                import base64
                auth_string = f"{WORDPRESS_APP_USERNAME}:{app_password}"
                encoded_auth = base64.b64encode(auth_string.encode()).decode()
                headers["Authorization"] = f"Basic {encoded_auth}"
            elif API_KEY:
                headers["Authorization"] = f"Bearer {API_KEY}"
            
            if DEBUG_MODE:
                print(f"Making request to WordPress API: {url}")
            
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                
                if response.status_code == 200:
                    return response.json().get("plans", [])
                else:
                    print(f"Error fetching topup plans: HTTP {response.status_code} - {response.text}")
                    return []
            except httpx.RequestError as e:
                print(f"Error connecting to WordPress for topup plans: {str(e)}")
                return []
    except Exception as e:
        print(f"General error fetching topup plans: {str(e)}")
        return []

async def execute_topup(iccid: str, plan_id: str, payment_reference: Optional[str] = None) -> Dict[str, Any]:
    """Execute a topup for an eSIM through WordPress API"""
    if DEBUG_MODE:
        print(f"Executing topup for ICCID {iccid} with plan {plan_id}")
    
    try:
        async with httpx.AsyncClient() as client:
            # Set up WordPress API URL for topup execution
            url = f"{WORDPRESS_URL}/wp-json/esim-global/v1/execute-topup"
            
            # Set up authentication headers
            headers = {
                "Content-Type": "application/json"
            }
            
            if WORDPRESS_APP_USERNAME and WORDPRESS_APP_PASSWORD:
                # Remove spaces from app password if present
                app_password = WORDPRESS_APP_PASSWORD.replace(" ", "")
                import base64
                auth_string = f"{WORDPRESS_APP_USERNAME}:{app_password}"
                encoded_auth = base64.b64encode(auth_string.encode()).decode()
                headers["Authorization"] = f"Basic {encoded_auth}"
            elif API_KEY:
                headers["Authorization"] = f"Bearer {API_KEY}"
            
            # Prepare payload
            payload = {
                "iccid": iccid,
                "plan_id": plan_id
            }
            
            if payment_reference:
                payload["payment_reference"] = payment_reference
            
            if DEBUG_MODE:
                print(f"Making request to WordPress API: {url}")
                print(f"Payload: {payload}")
            
            try:
                response = await client.post(url, headers=headers, json=payload, timeout=60.0)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    error_message = f"Error executing topup: HTTP {response.status_code}"
                    try:
                        error_data = response.json()
                        if "message" in error_data:
                            error_message = error_data["message"]
                    except:
                        error_message += f" - {response.text}"
                    
                    return {
                        "status": "error",
                        "message": error_message,
                        "iccid": iccid,
                        "plan_id": plan_id
                    }
            except httpx.RequestError as e:
                print(f"Error connecting to WordPress for topup execution: {str(e)}")
                return {
                    "status": "error",
                    "message": f"Connection error: {str(e)}",
                    "iccid": iccid,
                    "plan_id": plan_id
                }
    except Exception as e:
        print(f"General error executing topup: {str(e)}")
        return {
            "status": "error",
            "message": f"General error: {str(e)}",
            "iccid": iccid,
            "plan_id": plan_id
        }

async def get_topup_history(iccid: str) -> Dict[str, Any]:
    """Get topup history for an eSIM from WordPress API"""
    if DEBUG_MODE:
        print(f"Getting topup history for ICCID {iccid}")
    
    try:
        async with httpx.AsyncClient() as client:
            # Set up WordPress API URL for topup history
            url = f"{WORDPRESS_URL}/wp-json/esim-global/v1/topup-history/{iccid}"
            
            # Set up authentication headers
            headers = {}
            if WORDPRESS_APP_USERNAME and WORDPRESS_APP_PASSWORD:
                # Remove spaces from app password if present
                app_password = WORDPRESS_APP_PASSWORD.replace(" ", "")
                import base64
                auth_string = f"{WORDPRESS_APP_USERNAME}:{app_password}"
                encoded_auth = base64.b64encode(auth_string.encode()).decode()
                headers["Authorization"] = f"Basic {encoded_auth}"
            elif API_KEY:
                headers["Authorization"] = f"Bearer {API_KEY}"
            
            if DEBUG_MODE:
                print(f"Making request to WordPress API: {url}")
            
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"Error fetching topup history: HTTP {response.status_code} - {response.text}")
                    return {
                        "status": "error",
                        "iccid": iccid,
                        "history": [],
                        "count": 0
                    }
            except httpx.RequestError as e:
                print(f"Error connecting to WordPress for topup history: {str(e)}")
                return {
                    "status": "error",
                    "iccid": iccid,
                    "history": [],
                    "count": 0
                }
    except Exception as e:
        print(f"General error fetching topup history: {str(e)}")
        return {
            "status": "error",
            "iccid": iccid,
            "history": [],
            "count": 0
        }

# Add topup related endpoints
@app.get("/api/topup/plans", response_model=TopupPlansResponse)
async def get_topup_plans(api_key: str = Depends(get_api_key)):
    """
    Get available topup plans for eSIMs
    """
    plans = await fetch_topup_plans()
    
    return {
        "status": "success",
        "plans": plans,
        "count": len(plans)
    }

@app.post("/api/topup/execute", response_model=TopupResponse)
async def execute_topup_endpoint(
    request: TopupRequest,
    api_key: str = Depends(get_api_key)
):
    """
    Execute a topup for an eSIM
    """
    # Validate ICCID format
    if not request.iccid.isdigit() or not (18 <= len(request.iccid) <= 22):
        raise HTTPException(
            status_code=400,
            detail="Invalid ICCID format. ICCID should be 18-22 digits."
        )
    
    result = await execute_topup(
        request.iccid,
        request.plan_id,
        request.payment_reference
    )
    
    if result.get("status") == "error":
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "Error executing topup")
        )
    
    return result

@app.get("/api/topup/history/{iccid}", response_model=TopupHistoryResponse)
async def get_topup_history_endpoint(
    iccid: str,
    api_key: str = Depends(get_api_key)
):
    """
    Get topup history for an eSIM
    """
    # Validate ICCID format
    if not iccid.isdigit() or not (18 <= len(iccid) <= 22):
        raise HTTPException(
            status_code=400,
            detail="Invalid ICCID format. ICCID should be 18-22 digits."
        )
    
    result = await get_topup_history(iccid)
    
    if result.get("status") == "error":
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "Error fetching topup history")
        )
    
    return result

if __name__ == "__main__":
    import uvicorn
    
    # Get port and host from environment variables
    port = int(os.getenv("LISTEN_PORT", 8080))
    host = os.getenv("LISTEN_HOST", "0.0.0.0")
    
    print(f"Starting eSIM Global API server on {host}:{port}")
    print(f"API Documentation available at: http://{host}:{port}/docs")
    print(f"Health check endpoint: http://{host}:{port}/api/health")
    print("Press Ctrl+C to stop the server")
    
    # Run the application
    uvicorn.run(app, host=host, port=port) 