"""
GREST Product Scraper - Uses Shopify Admin API to populate PostgreSQL database.
Optimized for bulk operations - syncs ~2,300 variants in under 60 seconds.

Requires environment variables:
- SHOPIFY_ACCESS_TOKEN: Admin API access token
- SHOPIFY_STORE_URL: Store URL (e.g., grestmobile.myshopify.com)
"""

import os
import json
import requests
from time import time
from itertools import islice
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func
from database import get_db_session, GRESTProduct, init_database

SHOPIFY_STORE_URL = os.environ.get('SHOPIFY_STORE_URL', 'grestmobile.myshopify.com')
SHOPIFY_ACCESS_TOKEN = os.environ.get('SHOPIFY_ACCESS_TOKEN')
API_VERSION = '2024-10'
CHUNK_SIZE = 500


def get_shopify_headers():
    """Get headers for Shopify Admin API requests."""
    return {
        'X-Shopify-Access-Token': SHOPIFY_ACCESS_TOKEN,
        'Content-Type': 'application/json'
    }


def fetch_all_products():
    """Fetch ALL active products from Shopify Admin API with pagination.
    
    Only fetches products with status='active' to exclude:
    - Draft products (not ready for sale)
    - Archived products (removed from store)
    """
    if not SHOPIFY_ACCESS_TOKEN:
        print("ERROR: SHOPIFY_ACCESS_TOKEN not set!")
        return []
    
    all_products = []
    base_url = f"https://{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}/products.json"
    params = {'limit': 250, 'status': 'active'}
    
    while True:
        response = requests.get(base_url, headers=get_shopify_headers(), params=params)
        
        if response.status_code != 200:
            print(f"API Error: {response.status_code} - {response.text[:200]}")
            break
        
        data = response.json()
        products = data.get('products', [])
        all_products.extend(products)
        
        print(f"Fetched {len(products)} products (total: {len(all_products)})")
        
        link_header = response.headers.get('Link', '')
        if 'rel="next"' in link_header:
            import re
            next_match = re.search(r'<([^>]+)>; rel="next"', link_header)
            if next_match:
                base_url = next_match.group(1)
                params = {}
            else:
                break
        else:
            break
    
    return all_products


def _chunk(iterable, size):
    """Split an iterable into chunks of specified size."""
    it = iter(iterable)
    while True:
        batch = list(islice(it, size))
        if not batch:
            break
        yield batch


def get_category(title, product_type=''):
    """Determine product category from title and product type."""
    title_lower = title.lower()
    product_type_lower = product_type.lower() if product_type else ''
    
    if 'protection' in title_lower or 'accidental' in title_lower:
        return 'Protection Plan'
    if 'iphone' in title_lower:
        return 'iPhone'
    if 'ipad' in title_lower:
        return 'iPad'
    if 'macbook' in title_lower or 'mac book' in title_lower:
        return 'MacBook'
    if 'watch' in title_lower:
        return 'Apple Watch'
    if 'airpod' in title_lower:
        return 'AirPods'
    if 'charger' in title_lower or 'cable' in title_lower:
        return 'Accessories'
    if 'case' in title_lower or 'cover' in title_lower:
        return 'Cases'
    if 'screen' in title_lower:
        return 'Screen Protectors'
    
    return product_type or 'Other'


def extract_specs_from_body(body_html):
    """Extract specifications from product HTML body."""
    if not body_html:
        return {}
    
    specs = {}
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(body_html, 'html.parser')
        text = soup.get_text(separator='\n')
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        for line in lines:
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if key and value and len(key) < 50:
                        specs[key] = value
    except Exception:
        pass
    
    return specs


def fetch_product_metafields(product_id):
    """Fetch metafields for a specific product from Shopify API."""
    if not SHOPIFY_ACCESS_TOKEN:
        return {}
    
    url = f"https://{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}/products/{product_id}/metafields.json"
    
    try:
        response = requests.get(url, headers=get_shopify_headers())
        if response.status_code != 200:
            return {}
        
        metafields = response.json().get('metafields', [])
        specs = {}
        
        for mf in metafields:
            namespace = mf.get('namespace', '')
            key = mf.get('key', '')
            value = mf.get('value', '')
            
            # Extract custom namespace metafields as specs (these contain product specs)
            if namespace == 'custom' and value:
                # Convert key from snake_case to Title Case for display
                display_key = key.replace('_', ' ').title()
                # Clean up the value (remove leading/trailing whitespace)
                clean_value = str(value).strip()
                if clean_value and display_key not in ['Protection Variant', 'Charging', 'Case', 'Screenprotector']:
                    specs[display_key] = clean_value
        
        return specs
    except Exception as e:
        print(f"Error fetching metafields for product {product_id}: {e}")
        return {}


def get_price_range(variants):
    """Get min and max price from variants."""
    prices = []
    for v in variants:
        try:
            price = float(v.get('price', 0) or 0)
            if price > 0:
                prices.append(price)
        except (ValueError, TypeError):
            pass
    
    if prices:
        return min(prices), max(prices)
    return None, None


def parse_variant_options(variants):
    """Extract storage, colors, and conditions from all variants."""
    storage_options = set()
    colors = set()
    conditions = set()
    
    for v in variants:
        for opt_key in ['option1', 'option2', 'option3']:
            opt = v.get(opt_key, '')
            if opt:
                opt_lower = opt.lower()
                if 'gb' in opt_lower or 'tb' in opt_lower:
                    storage_options.add(opt)
                elif opt_lower in ['fair', 'good', 'superb', 'excellent', 'like new', 'refurbished']:
                    conditions.add(opt)
                elif opt_lower not in ['', 'default', 'title']:
                    colors.add(opt)
    
    return list(storage_options), list(colors), list(conditions)


def parse_variant_options_single(variant):
    """Extract storage, color, and condition from a single variant."""
    storage = None
    color = None
    condition = None
    
    for opt_key in ['option1', 'option2', 'option3']:
        opt = variant.get(opt_key, '')
        if opt:
            opt_lower = opt.lower().strip()
            if 'gb' in opt_lower or 'tb' in opt_lower:
                storage = opt.strip()
            elif opt_lower in ['fair', 'good', 'superb', 'excellent', 'like new', 'refurbished']:
                condition = opt.strip()
            elif opt_lower not in ['', 'default', 'title', 'random']:
                if not color:
                    color = opt.strip()
    
    return storage, color, condition


def _prepare_product_variants(product):
    """Transform a Shopify product into a list of variant dictionaries for bulk insert."""
    title = product.get('title', '')
    product_id = product.get('id')
    handle = product.get('handle', '')
    product_type = product.get('product_type', '')
    
    category = get_category(title, product_type)
    if category == 'Protection Plan':
        return []
    
    variants = product.get('variants', [])
    if not variants:
        return []
    
    # Fetch specs from metafields (canonical source for product specifications)
    specs = fetch_product_metafields(product_id)
    # Fallback to body_html if no metafields found
    if not specs:
        specs = extract_specs_from_body(product.get('body_html', ''))
    
    images = product.get('images', [])
    image_url = images[0].get('src', '') if images else None
    
    min_price, max_price = get_price_range(variants)
    storage_options, colors, conditions = parse_variant_options(variants)
    
    specs_json = json.dumps({
        'specs': specs,
        'storage_options': storage_options,
        'colors': colors,
        'conditions': conditions,
        'variant_count': len(variants),
        'product_type': product_type,
        'tags': product.get('tags', ''),
        'price_range': (
            f"Rs. {int(min_price):,} - Rs. {int(max_price):,}"
            if max_price and min_price and max_price != min_price
            else (f"Rs. {int(min_price):,}" if min_price else "")
        ),
    })
    
    base_url = f"https://grest.in/products/{handle}"
    rows = []
    
    for variant in variants:
        try:
            price = float(variant.get('price', 0) or 0)
        except (ValueError, TypeError):
            continue
        
        if price <= 0:
            continue
        
        variant_id = variant.get('id')
        storage, color, condition = parse_variant_options_single(variant)
        
        compare_price = variant.get('compare_at_price')
        try:
            compare_price = float(compare_price) if compare_price else None
        except (ValueError, TypeError):
            compare_price = None
        
        discount = None
        if compare_price and compare_price > price:
            discount = int(((compare_price - price) / compare_price) * 100)
        
        # WORKAROUND: Shopify Admin API doesn't reliably return inventory data
        # All products on grest.in are purchasable, so mark everything in stock
        # The website handles actual availability at checkout time
        in_stock = True
        
        sku = f"SHOPIFY_{product_id}_{variant_id}"
        variant_title = ' - '.join(filter(None, [title, storage, condition])) or title
        
        rows.append({
            'sku': sku,
            'name': title,
            'category': category,
            'variant': variant_title,
            'storage': storage,
            'color': color,
            'condition': condition,
            'price': price,
            'original_price': compare_price,
            'discount_percent': discount,
            'in_stock': in_stock,
            'warranty_months': 12,
            'product_url': f"{base_url}?variant={variant_id}",
            'image_url': image_url,
            'specifications': specs_json,
        })
    
    return rows


def _bulk_upsert_variants(session, rows):
    """Perform bulk upsert using PostgreSQL ON CONFLICT DO UPDATE."""
    if not rows:
        return
    
    table = GRESTProduct.__table__
    
    for chunk in _chunk(rows, CHUNK_SIZE):
        insert_stmt = insert(table).values(chunk)
        
        update_cols = {
            c.name: insert_stmt.excluded[c.name]
            for c in table.columns
            if c.name not in {'id', 'created_at', 'sku'}
        }
        update_cols['updated_at'] = func.now()
        
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=['sku'],
            set_=update_cols
        )
        
        session.execute(upsert_stmt)


def populate_database(hard_delete_stale: bool = True, progress_callback=None):
    """
    Fetch all products from Shopify and sync to database using bulk operations.
    
    This is optimized for speed:
    - Single API call to fetch all products
    - In-memory transformation of all variants
    - Bulk upsert using PostgreSQL ON CONFLICT
    - Single transaction for atomicity
    
    Args:
        hard_delete_stale: If True, delete variants not in current Shopify data
        progress_callback: Optional function(step, message, progress_pct) for real-time updates
    
    Returns:
        dict with success status and metrics
    """
    def emit(step, message, progress=0):
        if progress_callback:
            try:
                progress_callback(step, message, progress)
            except:
                pass
        print(f"[{step}] {message}")
    
    init_database()
    
    emit("connecting", "Connecting to Shopify API...", 5)
    
    start = time()
    
    emit("fetching", "Fetching products from Shopify...", 10)
    products = fetch_all_products()
    if not products:
        emit("error", "No products fetched from Shopify", 0)
        return {"success": False, "error": "No products fetched from Shopify"}
    
    emit("fetched", f"Fetched {len(products)} products from Shopify", 30)
    
    emit("processing", f"Processing {len(products)} products...", 40)
    
    variant_rows = []
    seen_skus = set()
    products_processed = 0
    
    for product in products:
        rows = _prepare_product_variants(product)
        variant_rows.extend(rows)
        seen_skus.update(row['sku'] for row in rows)
        products_processed += 1
    
    emit("processed", f"Prepared {len(variant_rows)} variants from {products_processed} products", 60)
    
    if not variant_rows:
        emit("error", "No sellable variants found", 0)
        return {"success": False, "error": "No sellable variants found"}
    
    deleted = 0
    created = 0
    updated = 0
    
    with get_db_session() as session:
        if session is None:
            emit("error", "Database not available", 0)
            return {"success": False, "error": "Database not available"}
        
        try:
            # Count existing SKUs before upsert to calculate created vs updated
            existing_skus = set(
                row[0] for row in session.query(GRESTProduct.sku).filter(
                    GRESTProduct.sku.in_(seen_skus)
                ).all()
            )
            
            new_skus = seen_skus - existing_skus
            updated_skus = seen_skus & existing_skus
            
            created = len(new_skus)
            updated = len(updated_skus)
            
            emit("upserting", f"Updating database: {created} new, {updated} existing...", 70)
            _bulk_upsert_variants(session, variant_rows)
            
            if hard_delete_stale and seen_skus:
                emit("cleaning", "Removing stale products...", 85)
                stale_count = session.query(GRESTProduct).filter(
                    ~GRESTProduct.sku.in_(seen_skus)
                ).count()
                
                if stale_count > 0:
                    deleted = session.query(GRESTProduct).filter(
                        ~GRESTProduct.sku.in_(seen_skus)
                    ).delete(synchronize_session=False)
            
            session.commit()
            
        except Exception as exc:
            session.rollback()
            emit("error", f"Sync failed: {exc}", 0)
            raise
    
    elapsed = round(time() - start, 2)
    
    with get_db_session() as session:
        if session:
            total = session.query(GRESTProduct).count()
            in_stock = session.query(GRESTProduct).filter(GRESTProduct.in_stock == True).count()
            emit("complete", f"Sync complete! {total} variants ({created} new, {updated} updated, {deleted} removed)", 100)
    
    return {
        "success": True,
        "variants_processed": len(variant_rows),
        "variants_created": created,
        "variants_updated": updated,
        "variants_deleted": deleted,
        "elapsed_seconds": elapsed,
    }


def get_shopify_product_count():
    """Get total variant count from Shopify without full sync."""
    products = fetch_all_products()
    if not products:
        return 0
    
    total_variants = 0
    for product in products:
        variants = product.get('variants', [])
        total_variants += len(variants)
    
    return total_variants


if __name__ == "__main__":
    result = populate_database(hard_delete_stale=True)
    print(f"\nResult: {result}")
