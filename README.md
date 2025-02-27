# eSIM Global FastAPI Integration

This FastAPI application connects to the eSIM Global WordPress plugin to deliver live data.

## Setup Instructions

### Development Environment

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**

   Copy the `.env.example` file to `.env` and update the values:

   ```
   WORDPRESS_URL=http://your-wordpress-site.com
   API_KEY=your_api_key_here  # For WordPress API (optional)
   REFRESH_INTERVAL=300  # Data refresh interval in seconds (default: 5 minutes)
   FASTAPI_API_KEY=your_fastapi_api_key_here  # For securing FastAPI endpoints
   ```

3. **Run the FastAPI application for development:**

   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Production Deployment with Docker and Nginx

1. **Build and start the containers:**

   ```bash
   docker-compose up -d
   ```

2. **Configure SSL:**

   Place your SSL certificate and key in the `nginx/ssl` directory:
   - `server.crt`: SSL certificate
   - `server.key`: SSL private key

3. **Update Nginx configuration:**

   Edit `nginx/conf.d/default.conf` to set your domain name instead of the placeholder.

4. **Restart the Nginx container to apply changes:**

   ```bash
   docker-compose restart nginx
   ```

### Production Deployment with Gunicorn (without Docker)

1. **Install Gunicorn:**

   ```bash
   pip install gunicorn
   ```

2. **Run with Gunicorn:**

   ```bash
   gunicorn -c gunicorn_conf.py main:app
   ```

## API Endpoints

### Basic Endpoints

- **GET /api/esim-data**: Get all eSIM products and countries data
- **GET /api/products**: Get all products
- **GET /api/countries**: Get all countries
- **GET /api/products/{product_id}**: Get a specific product by ID
- **GET /api/health**: Health check endpoint

### Filtering and Advanced Endpoints

- **GET /api/products/filter**: Filter products by various criteria:
  - `country_code`: Filter by country code
  - `price_group`: Filter by price group
  - `min_days` & `max_days`: Filter by duration
  - `min_gb` & `max_gb`: Filter by data amount
  - `provider_id`: Filter by provider ID

- **GET /api/countries/region/{region_code}**: Get countries by region code
- **GET /api/price-groups**: Get all unique price groups

## Authentication

All API endpoints except `/api/health` require authentication. To authenticate:

1. Include the `X-API-Key` header in your requests with the value set in the `FASTAPI_API_KEY` environment variable.

Example:
```
curl -H "X-API-Key: your_fastapi_api_key_here" http://your-api-domain.com/api/products
```

## Data Models

The API includes enhanced data models:

- **Product**: Represents an eSIM product with fields for data amount, duration, pricing, etc.
- **Country**: Represents a country or region where eSIM services are available
- **PriceGroup**: Represents a pricing tier for products
- **ProductFilter**: Used for filtering products by various criteria

## Integration with WordPress

This application connects to the REST API endpoint created in the eSIM Global WordPress plugin. The plugin exposes data through the following endpoint:

```
/wp-json/esim-global/v1/data
```

The FastAPI application fetches data from this endpoint at startup and then refreshes it periodically based on the `REFRESH_INTERVAL` configuration.

## Security

The API includes several security features:

1. API Key authentication for all endpoints
2. HTTPS encryption with Nginx (in production)
3. Rate limiting to prevent abuse
4. Security headers to protect against common web vulnerabilities 
5. Regular data refresh to ensure data is up-to-date

## Customization

You can customize the data models in `main.py` to match your specific eSIM data structure by modifying the Pydantic models:

- `Product`: Add or modify fields to match your product structure
- `Country`: Adjust fields based on your country data

## Troubleshooting

- If you encounter connection issues to WordPress, check the `WORDPRESS_URL` setting and ensure the WordPress site is accessible.
- For authentication issues, verify the API keys are set correctly.
- Check the logs from Gunicorn for detailed error information. 