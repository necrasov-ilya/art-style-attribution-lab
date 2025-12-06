"""Rate limiting and concurrent operation control."""
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Set, Tuple
from fastapi import HTTPException, Request, status


class ConcurrentOperationLimiter:
    """Prevents users from running multiple heavy operations simultaneously."""
    
    # Maximum time (seconds) an operation can be "active" before being considered stale
    STALE_OPERATION_TIMEOUT = 300  # 5 minutes

    def __init__(self):
        # Track active operations per user: {user_id: {operation_type: start_time}}
        self._active_operations: Dict[int, Dict[str, datetime]] = defaultdict(dict)
        self._lock = asyncio.Lock()

    async def acquire(self, user_id: int, operation_type: str) -> None:
        """
        Acquire permission to run an operation.

        Raises HTTPException if user already has an active operation of this type
        or incompatible operations.
        """
        async with self._lock:
            now = datetime.now()
            
            # Clean up stale operations for this user first
            self._cleanup_stale_operations(user_id, now)
            
            active = self._active_operations[user_id]

            # Define mutually exclusive operation groups
            heavy_ops = {"generate", "deep_analysis", "analyze"}

            if operation_type in heavy_ops:
                # Check if any heavy operation is already running
                active_heavy = set(active.keys()) & heavy_ops
                if active_heavy:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Another analysis or generation is already in progress. Please wait for it to complete."
                    )

            # Add to active operations with timestamp
            self._active_operations[user_id][operation_type] = now
    
    def _cleanup_stale_operations(self, user_id: int, now: datetime) -> None:
        """Remove operations that have been running too long (likely stuck)."""
        if user_id not in self._active_operations:
            return
        
        stale_ops = []
        for op_type, start_time in self._active_operations[user_id].items():
            if (now - start_time).total_seconds() > self.STALE_OPERATION_TIMEOUT:
                stale_ops.append(op_type)
        
        for op_type in stale_ops:
            del self._active_operations[user_id][op_type]

    async def release(self, user_id: int, operation_type: str) -> None:
        """Release an operation lock."""
        async with self._lock:
            if user_id in self._active_operations:
                self._active_operations[user_id].pop(operation_type, None)
                # Clean up empty dicts
                if not self._active_operations[user_id]:
                    del self._active_operations[user_id]
    
    async def force_release_all(self, user_id: int) -> None:
        """Force release all operations for a user (emergency cleanup)."""
        async with self._lock:
            if user_id in self._active_operations:
                del self._active_operations[user_id]


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self):
        # Track requests: {user_id: [(timestamp, endpoint)]}
        self._requests: Dict[int, list] = defaultdict(list)
        self._lock = asyncio.Lock()

        # Rate limits per endpoint (requests per minute)
        self.limits = {
            "/api/analyze": 10,
            "/api/generate": 5,
            "/api/deep-analysis/full": 3,
            "/api/deep-analysis/module": 10,
            "default": 60,
        }

    async def check_rate_limit(self, user_id: int, endpoint: str) -> None:
        """
        Check if user has exceeded rate limit for this endpoint.

        Raises HTTPException if limit exceeded.
        """
        async with self._lock:
            now = datetime.now()
            window_start = now - timedelta(minutes=1)

            # Clean old requests
            self._requests[user_id] = [
                (ts, ep) for ts, ep in self._requests[user_id]
                if ts > window_start
            ]

            # Normalize endpoint path
            normalized_endpoint = self._normalize_endpoint(endpoint)

            # Get limit for this endpoint
            limit = self.limits.get(normalized_endpoint, self.limits["default"])

            # Count recent requests to this endpoint
            recent_count = sum(
                1 for ts, ep in self._requests[user_id]
                if ep == normalized_endpoint
            )

            if recent_count >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Maximum {limit} requests per minute for this endpoint."
                )

            # Add current request
            self._requests[user_id].append((now, normalized_endpoint))

    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path to match rate limit keys."""
        for key in self.limits.keys():
            if key != "default" and path.startswith(key):
                return key
        return "default"


# Global instances
concurrent_limiter = ConcurrentOperationLimiter()
rate_limiter = RateLimiter()
