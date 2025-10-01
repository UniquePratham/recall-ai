"""
LRU Cache Manager for Recall AI
Manages persistent user modes and search result caching
"""
import json
import os
import time
from typing import Dict, List, Optional, Any
from collections import OrderedDict
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class SearchResult:
    """Represents a cached search result"""
    query: str
    results: List[Dict[str, Any]]
    timestamp: float
    username: str

@dataclass
class UserMode:
    """Represents user's last selected mode"""
    user_id: int
    mode: str
    timestamp: float

class CacheManager:
    """Manages LRU cache for search results and user modes"""
    
    def __init__(self, cache_dir: str = ".", max_search_cache: int = 10):
        self.cache_dir = Path(cache_dir)
        self.max_search_cache = max_search_cache
        
        # File paths
        self.search_cache_file = self.cache_dir / "search_cache.txt"
        self.user_modes_file = self.cache_dir / "user_modes.txt"
        
        # In-memory caches
        self.search_cache: OrderedDict[str, SearchResult] = OrderedDict()
        self.user_modes: Dict[int, UserMode] = {}
        
        # Load existing data
        self._load_search_cache()
        self._load_user_modes()
    
    def _load_search_cache(self):
        """Load search cache from file"""
        try:
            if self.search_cache_file.exists():
                with open(self.search_cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        result = SearchResult(**item)
                        cache_key = f"{result.username}:{result.query}"
                        self.search_cache[cache_key] = result
        except Exception as e:
            print(f"Warning: Could not load search cache: {e}")
    
    def _load_user_modes(self):
        """Load user modes from file"""
        try:
            if self.user_modes_file.exists():
                with open(self.user_modes_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        mode = UserMode(**item)
                        self.user_modes[mode.user_id] = mode
        except Exception as e:
            print(f"Warning: Could not load user modes: {e}")
    
    def _save_search_cache(self):
        """Save search cache to file"""
        try:
            data = [asdict(result) for result in self.search_cache.values()]
            with open(self.search_cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Could not save search cache: {e}")
    
    def _save_user_modes(self):
        """Save user modes to file"""
        try:
            data = [asdict(mode) for mode in self.user_modes.values()]
            with open(self.user_modes_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Could not save user modes: {e}")
    
    def cache_search_result(self, query: str, results: List[Dict[str, Any]], username: str):
        """Cache a search result with LRU eviction"""
        cache_key = f"{username}:{query}"
        
        # Remove if already exists (to update position)
        if cache_key in self.search_cache:
            del self.search_cache[cache_key]
        
        # Add new result
        result = SearchResult(
            query=query,
            results=results,
            timestamp=time.time(),
            username=username
        )
        self.search_cache[cache_key] = result
        
        # Evict oldest if over limit
        while len(self.search_cache) > self.max_search_cache:
            self.search_cache.popitem(last=False)
        
        self._save_search_cache()
    
    def get_cached_searches(self, username: str, limit: int = 5) -> List[SearchResult]:
        """Get recent cached searches for a user"""
        user_searches = [
            result for key, result in self.search_cache.items()
            if result.username == username
        ]
        
        # Sort by timestamp (newest first) and limit
        user_searches.sort(key=lambda x: x.timestamp, reverse=True)
        return user_searches[:limit]
    
    def get_search_context_for_chat(self, username: str) -> str:
        """Get formatted search context for chat mode"""
        recent_searches = self.get_cached_searches(username, limit=3)
        
        if not recent_searches:
            return ""
        
        context_parts = ["Recent search context (for reference only):"]
        
        for i, search in enumerate(recent_searches, 1):
            context_parts.append(f"\\nSearch {i}: {search.query}")
            
            # Add top 2 results from each search
            for j, result in enumerate(search.results[:2], 1):
                snippet = result.get('text', '')[:200]
                if len(snippet) == 200:
                    snippet += "..."
                context_parts.append(f"  Result {j}: {snippet}")
        
        return "\\n".join(context_parts)
    
    def set_user_mode(self, user_id: int, mode: str):
        """Set user's current mode"""
        self.user_modes[user_id] = UserMode(
            user_id=user_id,
            mode=mode,
            timestamp=time.time()
        )
        self._save_user_modes()
    
    def get_user_mode(self, user_id: int) -> Optional[str]:
        """Get user's last selected mode"""
        mode = self.user_modes.get(user_id)
        return mode.mode if mode else None
    
    def clear_old_cache(self, max_age_days: int = 7):
        """Clear cache entries older than specified days"""
        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
        
        # Clear old search results
        to_remove = [
            key for key, result in self.search_cache.items()
            if result.timestamp < cutoff_time
        ]
        
        for key in to_remove:
            del self.search_cache[key]
        
        if to_remove:
            self._save_search_cache()
    
    def clear_user_search_cache(self, username: str, search_terms: str):
        """Clear cache entries for a user that contain specific search terms"""
        to_remove = []
        search_terms_lower = search_terms.lower()
        
        for key, result in self.search_cache.items():
            if (result.username == username and 
                search_terms_lower in result.query.lower()):
                to_remove.append(key)
        
        for key in to_remove:
            del self.search_cache[key]
        
        if to_remove:
            self._save_search_cache()
    
    def clear_all_user_cache(self, username: str):
        """Clear all cache entries and modes for a specific user"""
        # Clear search cache
        to_remove = [
            key for key, result in self.search_cache.items()
            if result.username == username
        ]
        
        for key in to_remove:
            del self.search_cache[key]
        
        # Clear user mode
        user_id_to_remove = None
        for user_id, mode in self.user_modes.items():
            if mode.mode and str(user_id) == username:  # Match by string conversion
                user_id_to_remove = user_id
                break
        
        if user_id_to_remove:
            del self.user_modes[user_id_to_remove]
        
        # Save changes
        if to_remove:
            self._save_search_cache()
        if user_id_to_remove:
            self._save_user_modes()
    
    def get_cache_stats(self, username: str = None) -> Dict[str, int]:
        """Get cache statistics"""
        if username:
            user_searches = sum(1 for result in self.search_cache.values() if result.username == username)
            user_mode = 1 if any(mode.mode for user_id, mode in self.user_modes.items() if str(user_id) == username) else 0
            return {
                "total_searches": user_searches,
                "user_mode_saved": user_mode
            }
        else:
            return {
                "total_searches": len(self.search_cache),
                "total_user_modes": len(self.user_modes)
            }

# Global cache manager instance
cache_manager = CacheManager()