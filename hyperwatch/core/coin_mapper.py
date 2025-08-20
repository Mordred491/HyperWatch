import os
import json
import logging
import requests
from datetime import datetime, timedelta

class CoinMapper:
    def __init__(self, cache_file="coin_mappings.json", cache_duration_hours=1):
        self.cache_file = cache_file
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self.perp_map = {}   # token_key -> {"name": str, "index": int}
        self.spot_map = {}   # token_key -> {"name": str, "index": int}
        self.name_to_key = {}  # "BTC" -> token_key
        self.index_to_name = {}  # For @193 style lookups
        self.all_tokens = {}  # Comprehensive token storage
        self.load_mappings()

    def load_mappings(self):
        """Load mappings from cache if valid, otherwise fetch fresh."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    data = json.load(f)
                    cache_time = datetime.fromisoformat(data["timestamp"])
                    if datetime.now() - cache_time < self.cache_duration:
                        self.perp_map = data.get("perp_map", {})
                        self.spot_map = data.get("spot_map", {})
                        self.name_to_key = data.get("name_to_key", {})
                        self.index_to_name = data.get("index_to_name", {})
                        self.all_tokens = data.get("all_tokens", {})
                        logging.info(f"✅ Loaded coin mappings from cache: {len(self.all_tokens)} tokens")
                        return
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logging.warning(f"⚠️ Cache file corrupted: {e}, fetching fresh data")
        
        self.fetch_and_cache_mapping()

    def fetch_and_cache_mapping(self):
        """Fetch fresh coin mappings from Hyperliquid and store indexes for accurate pricing."""
        try:
            # Fetch perpetual markets (meta)
            logging.info("🔄 Fetching perpetual markets...")
            perp_response = requests.post("https://api.hyperliquid.xyz/info", 
                                        json={"type": "meta"}, timeout=10)
            perp_response.raise_for_status()
            perp_meta = perp_response.json()
            
            perp_count = 0
            for i, coin in enumerate(perp_meta["universe"]):
                name = coin["name"]
                token_key = f"@{i}"  # Standard format
                
                self.perp_map[token_key] = {"name": name, "index": i}
                self.name_to_key[name.upper()] = token_key
                self.index_to_name[token_key] = name
                
                # Store all possible representations
                self.all_tokens[name.upper()] = {
                    "type": "perp",
                    "index": i,
                    "token_key": token_key,
                    "name": name
                }
                self.all_tokens[token_key] = self.all_tokens[name.upper()]
                perp_count += 1
                
                # Also store by raw index for direct lookups
                self.all_tokens[str(i)] = self.all_tokens[name.upper()]

            # Fetch spot markets (spotMeta)
            logging.info("🔄 Fetching spot markets...")
            spot_response = requests.post("https://api.hyperliquid.xyz/info", 
                                        json={"type": "spotMeta"}, timeout=10)
            spot_response.raise_for_status()
            spot_meta = spot_response.json()
            
            spot_count = 0
            for i, coin in enumerate(spot_meta["universe"]):
                name = coin["name"]
                
                # Better validation for malformed entries
                if not name or not isinstance(name, str) or len(name.strip()) == 0:
                    logging.debug(f"🗑️ Skipping empty/invalid spot token at index {i}")
                    continue
                
                # Skip malformed entries where name is just an index or starts with @
                if (name.startswith("@") and name[1:].replace(".", "").isdigit()) or name.isdigit():
                    logging.debug(f"🗑️ Skipping malformed spot token at index {i}: name='{name}'")
                    continue
                
                # Use a higher offset for spot tokens to avoid conflicts
                spot_index_offset = 10000
                token_key = f"@{spot_index_offset + i}"
                
                self.spot_map[token_key] = {"name": name, "index": i}
                self.index_to_name[token_key] = name
                
                # Don't overwrite perp mappings for name lookup
                if name.upper() not in self.name_to_key:
                    self.name_to_key[name.upper()] = token_key
                
                # Store comprehensive mapping (only if not already a perp)
                if name.upper() not in self.all_tokens or self.all_tokens[name.upper()]["type"] != "perp":
                    self.all_tokens[name.upper()] = {
                        "type": "spot",
                        "index": i,
                        "token_key": token_key,
                        "name": name
                    }
                
                self.all_tokens[token_key] = {
                    "type": "spot",
                    "index": i,
                    "token_key": token_key,
                    "name": name
                }
                spot_count += 1

            # Save to cache
            with open(self.cache_file, "w") as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "perp_map": self.perp_map,
                    "spot_map": self.spot_map,
                    "name_to_key": self.name_to_key,
                    "index_to_name": self.index_to_name,
                    "all_tokens": self.all_tokens
                }, f, indent=2)

            logging.info(f"🔥 Coin mappings refreshed: {perp_count} perp + {spot_count} spot = {len(self.all_tokens)} total")
            
            # Debug: Print some sample mappings
            sample_perps = list(self.perp_map.keys())[:5]
            sample_spots = list(self.spot_map.keys())[:5]
            logging.debug(f"Sample perp mappings: {[(k, self.perp_map[k]['name']) for k in sample_perps]}")
            logging.debug(f"Sample spot mappings: {[(k, self.spot_map[k]['name']) for k in sample_spots]}")

        except requests.RequestException as e:
            logging.error(f"❌ Network error fetching coin mappings: {e}")
        except Exception as e:
            logging.error(f"❌ Error fetching coin mappings: {e}")

    def get_coin_name(self, token_identifier):
        """Return the coin name for any token identifier with enhanced fallback."""
        if not token_identifier:
            return "UNKNOWN"
            
        token_str = str(token_identifier).strip()
        
        # IMPORTANT: Log what we're looking up for debugging
        logging.debug(f"🔍 Looking up coin name for: '{token_str}'")
        
        # Direct lookup in comprehensive mapping
        if token_str in self.all_tokens:
            name = self.all_tokens[token_str]["name"]
            logging.debug(f"✅ Found direct match: {token_str} -> {name}")
            return name
        
        # Try uppercase version
        if token_str.upper() in self.all_tokens:
            name = self.all_tokens[token_str.upper()]["name"]
            logging.debug(f"✅ Found uppercase match: {token_str} -> {name}")
            return name
        
        # Legacy lookups
        if token_str in self.perp_map:
            name = self.perp_map[token_str]["name"]
            logging.debug(f"✅ Found in perp_map: {token_str} -> {name}")
            return name
        if token_str in self.spot_map:
            name = self.spot_map[token_str]["name"]
            logging.debug(f"✅ Found in spot_map: {token_str} -> {name}")
            return name
        if token_str in self.index_to_name:
            name = self.index_to_name[token_str]
            logging.debug(f"✅ Found in index_to_name: {token_str} -> {name}")
            return name
        
        # Enhanced fallback for @index format
        if token_str.startswith("@") and token_str[1:].isdigit():
            index = int(token_str[1:])
            
            # Check if it's a direct perp index
            if index < 1000:  # Reasonable perp index range
                direct_key = f"@{index}"
                if direct_key in self.perp_map:
                    name = self.perp_map[direct_key]["name"]
                    logging.debug(f"✅ Found perp by index: {token_str} -> {name}")
                    return name
                if direct_key in self.index_to_name:
                    name = self.index_to_name[direct_key]
                    logging.debug(f"✅ Found by index_to_name: {token_str} -> {name}")
                    return name
            
            # Check spot with offset
            spot_key = f"@{10000 + index}"
            if spot_key in self.spot_map:
                name = self.spot_map[spot_key]["name"]
                logging.debug(f"✅ Found spot by offset: {token_str} -> {name}")
                return name
                
            logging.debug(f"🔍 Could not resolve token index: {token_str}")
            return f"TOKEN_{token_str}"  # More descriptive fallback
        
        # If we still can't find it, force a cache refresh and try once more
        if not hasattr(self, '_refresh_attempted'):
            logging.info(f"🔄 Token '{token_str}' not found, attempting cache refresh...")
            self._refresh_attempted = True
            self.fetch_and_cache_mapping()
            return self.get_coin_name(token_identifier)  # Recursive call after refresh
            
        logging.debug(f"🔍 Unknown token identifier: {token_identifier}")
        return f"TOKEN_{token_str}"  # Fallback with original identifier

    def get_coin_price(self, token_identifier, price_data=None):
        """
        Return the correct price for any token identifier.
        price_data should be the result from allMids API call which returns a dict like:
        {"BTC": "50000", "ETH": "3000", "@107": "1.23", ...}
        """
        try:
            if not token_identifier or not price_data:
                logging.warning("❌ Empty token identifier or price data for price lookup")
                return 0.0
                
            token_str = str(token_identifier).strip()
            logging.debug(f"🔍 Looking up price for: '{token_str}'")
            
            # Direct price lookup using allMids format
            if token_str in price_data:
                price = float(price_data[token_str])
                logging.debug(f"💰 Direct price for {token_str}: ${price}")
                return price
            
            # Try to get coin name and look up by name
            coin_name = self.get_coin_name(token_str)
            if coin_name != f"TOKEN_{token_str}" and coin_name in price_data:
                price = float(price_data[coin_name])
                logging.debug(f"💰 Price by name lookup {token_str} -> {coin_name}: ${price}")
                return price
            
            # For spot tokens that use @index format, try that
            if token_str in self.all_tokens:
                token_info = self.all_tokens[token_str]
                if token_info["type"] == "spot":
                    spot_key = token_info["token_key"]
                    if spot_key in price_data:
                        price = float(price_data[spot_key])
                        logging.debug(f"💰 Spot price via token_key {token_str} -> {spot_key}: ${price}")
                        return price
                    
                    # Try the raw @index format that might be in price data
                    raw_index_key = f"@{token_info['index']}"
                    if raw_index_key in price_data:
                        price = float(price_data[raw_index_key])
                        logging.debug(f"💰 Spot price via raw index {token_str} -> {raw_index_key}: ${price}")
                        return price
            
            # Try uppercase versions
            if token_str.upper() != token_str:
                return self.get_coin_price(token_str.upper(), price_data)
                    
        except (ValueError, TypeError, KeyError) as e:
            logging.error(f"❌ Price lookup error for {token_identifier}: {e}")
        
        logging.warning(f"⚠️ Price not found for: {token_identifier}")
        return 0.0

    def get_token_key_by_name(self, coin_name):
        """Find token_key from coin name."""
        if not coin_name:
            return None
            
        coin_upper = str(coin_name).upper().strip()
            
        # Check comprehensive mapping
        if coin_upper in self.all_tokens:
            return self.all_tokens[coin_upper]["token_key"]
        
        # Legacy lookup
        key = self.name_to_key.get(coin_upper)
        if not key:
            logging.debug(f"🔍 No token_key found for coin: {coin_name}")
        return key

    def get_token_info(self, token_identifier):
        """Get comprehensive token information."""
        if not token_identifier:
            return None
            
        token_str = str(token_identifier).strip()
            
        if token_str in self.all_tokens:
            return self.all_tokens[token_str].copy()
        
        if token_str.upper() in self.all_tokens:
            return self.all_tokens[token_str.upper()].copy()
            
        return None

    def is_valid_order(self, size, price, min_usd_value=0.01):
        """Check if an order is valid for notification."""
        try:
            size_float = float(size)
            price_float = float(price)
            usd_value = size_float * price_float
            
            # Filter out zero/dust orders
            if size_float <= 0 or usd_value < min_usd_value:
                logging.debug(f"🗑️ Filtering out dust order: size={size_float}, value=${usd_value}")
                return False
                
            return True
        except (ValueError, TypeError):
            return False

    def fetch_all_prices(self):
        """Fetch current prices for all tokens using the allMids endpoint."""
        try:
            logging.info("🔄 Fetching all current prices...")
            response = requests.post("https://api.hyperliquid.xyz/info", 
                                   json={"type": "allMids"}, timeout=10)
            response.raise_for_status()
            price_data = response.json()
            
            logging.info(f"📊 Fetched prices for {len(price_data)} tokens")
            return price_data
        except requests.RequestException as e:
            logging.error(f"❌ Network error fetching prices: {e}")
            return {}
        except Exception as e:
            logging.error(f"❌ Error fetching prices: {e}")
            return {}

    def debug_mappings(self):
        """Debug method to print current mappings."""
        print(f"\n🔍 Debug: Current mappings")
        print(f"Total tokens: {len(self.all_tokens)}")
        print(f"Perp tokens: {len(self.perp_map)}")
        print(f"Spot tokens: {len(self.spot_map)}")
        
        print(f"\nSample perp mappings:")
        for i, (key, info) in enumerate(list(self.perp_map.items())[:10]):
            print(f"  {key} -> {info['name']} (index: {info['index']})")
        
        print(f"\nSample spot mappings:")
        for i, (key, info) in enumerate(list(self.spot_map.items())[:10]):
            print(f"  {key} -> {info['name']} (index: {info['index']})")

# Singleton instance for reuse
coin_mapper = CoinMapper()