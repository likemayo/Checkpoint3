"""
Metrics collection module for system observability.
Tracks key business and technical metrics for monitoring and alerting.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict, deque
from threading import Lock
import json


class MetricsCollector:
    """
    Collects and aggregates system metrics in-memory.
    Provides counters, gauges, and histograms for various metrics.
    """
    
    def __init__(self):
        self.lock = Lock()
        
        # Counters (cumulative)
        self.counters = defaultdict(int)
        
        # Gauges (point-in-time values)
        self.gauges = defaultdict(float)
        
        # Histograms (time-series data with retention)
        self.histograms = defaultdict(lambda: deque(maxlen=1000))
        
        # Time-windowed metrics (for rate calculations)
        self.time_windowed = defaultdict(lambda: deque(maxlen=10000))
        
        # Start time for uptime calculation
        self.start_time = time.time()
    
    def increment_counter(self, name: str, value: int = 1, labels: Optional[Dict] = None):
        """Increment a counter metric."""
        with self.lock:
            key = self._make_key(name, labels)
            self.counters[key] += value
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict] = None):
        """Set a gauge metric to a specific value."""
        with self.lock:
            key = self._make_key(name, labels)
            self.gauges[key] = value
    
    def observe(self, name: str, value: float, labels: Optional[Dict] = None):
        """Record an observation for a histogram metric."""
        with self.lock:
            key = self._make_key(name, labels)
            self.histograms[key].append({
                'value': value,
                'timestamp': time.time()
            })
    
    def record_event(self, name: str, labels: Optional[Dict] = None):
        """Record a timestamped event for rate calculations."""
        with self.lock:
            key = self._make_key(name, labels)
            self.time_windowed[key].append(time.time())
    
    def _make_key(self, name: str, labels: Optional[Dict] = None) -> str:
        """Create a unique key from metric name and labels."""
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return f"{name}{{{label_str}}}"
        return name
    
    def get_counter(self, name: str, labels: Optional[Dict] = None) -> int:
        """Get current counter value."""
        key = self._make_key(name, labels)
        return self.counters.get(key, 0)
    
    def get_gauge(self, name: str, labels: Optional[Dict] = None) -> float:
        """Get current gauge value."""
        key = self._make_key(name, labels)
        return self.gauges.get(key, 0.0)
    
    def get_histogram_stats(self, name: str, labels: Optional[Dict] = None) -> Dict:
        """Get statistics for a histogram metric.
        
        If labels is None, aggregate observations across all label variants for
        this histogram name. This lets callers fetch global stats even when
        observations were recorded with per-endpoint/method/status labels.
        """
        # When labels are provided, look up the exact series
        if labels is not None:
            key = self._make_key(name, labels)
            observations = self.histograms.get(key, deque())
            values = sorted([obs['value'] for obs in observations])
        else:
            # Aggregate across all series that match this histogram name
            values = []
            prefix = f"{name}{'{'}"
            for k, dq in self.histograms.items():
                if k == name or k.startswith(prefix):
                    values.extend(obs['value'] for obs in dq)
            values.sort()
        
        if not values:
            return {
                'count': 0,
                'sum': 0,
                'min': 0,
                'max': 0,
                'avg': 0,
                'p50': 0,
                'p95': 0,
                'p99': 0
            }
        
        count = len(values)
        
        # Clamp percentile index to valid range
        def pct(values_list, p):
            if not values_list:
                return 0
            idx = int(p * len(values_list))
            if idx >= len(values_list):
                idx = len(values_list) - 1
            return values_list[idx]
        
        return {
            'count': count,
            'sum': sum(values),
            'min': values[0],
            'max': values[-1],
            'avg': sum(values) / count,
            'p50': pct(values, 0.50),
            'p95': pct(values, 0.95),
            'p99': pct(values, 0.99)
        }
    
    def get_rate(self, name: str, window_seconds: int = 60, labels: Optional[Dict] = None) -> float:
        """Calculate rate of events per second over a time window."""
        key = self._make_key(name, labels)
        events = self.time_windowed.get(key, deque())
        
        if not events:
            return 0.0
        
        now = time.time()
        cutoff = now - window_seconds
        
        # Count events within the window
        recent_events = sum(1 for timestamp in events if timestamp >= cutoff)
        
        return recent_events / window_seconds if window_seconds > 0 else 0.0
    
    def get_all_metrics(self) -> Dict:
        """Get all metrics in a structured format."""
        with self.lock:
            return {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'uptime_seconds': time.time() - self.start_time,
                'counters': dict(self.counters),
                'gauges': dict(self.gauges),
                'histograms': {
                    name: self.get_histogram_stats(name)
                    for name in self.histograms.keys()
                }
            }
    
    def get_business_metrics(self) -> Dict:
        """Get business-specific metrics for dashboard."""
        # Load real data from database if available
        try:
            import sqlite3
            import os
            
            db_path = os.environ.get("APP_DB_PATH", "app.sqlite")
            
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                
                # Get real order counts from database
                orders_result = conn.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN status IN ('COMPLETED', 'REFUNDED') THEN 1 ELSE 0 END) as successful,
                        SUM(CASE WHEN status IN ('FAILED', 'CANCELLED') THEN 1 ELSE 0 END) as failed
                    FROM sale
                """).fetchone()
                
                # Get real refund/RMA counts from database
                # Approved = COMPLETED with any disposition (REFUND, REPLACEMENT, REPAIR, STORE_CREDIT)
                # Rejected = COMPLETED with REJECT disposition
                # Pending = Not COMPLETED or CANCELLED (SUBMITTED, VALIDATED, AUTHORIZED, SHIPPING, INSPECTING, etc.)
                refunds_result = conn.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'COMPLETED' AND disposition IS NOT NULL AND disposition != 'REJECT' THEN 1 ELSE 0 END) as approved,
                        SUM(CASE WHEN status = 'COMPLETED' AND disposition = 'REJECT' THEN 1 ELSE 0 END) as rejected,
                        SUM(CASE WHEN status NOT IN ('COMPLETED', 'CANCELLED') THEN 1 ELSE 0 END) as pending
                    FROM rma_requests
                """).fetchone()
                
                conn.close()
                
                # Combine database data with in-memory counters
                orders_total = orders_result['total'] if orders_result else 0
                refunds_total = refunds_result['total'] if refunds_result else 0
                
                return {
                    'orders': {
                        'total': orders_total,
                        'successful': orders_result['successful'] if orders_result else 0,
                        'failed': orders_result['failed'] if orders_result else 0,
                        'rate_per_minute': self.get_rate('orders_total', window_seconds=60) * 60
                    },
                    'refunds': {
                        'total': refunds_total,
                        'approved': refunds_result['approved'] if refunds_result else 0,
                        'rejected': refunds_result['rejected'] if refunds_result else 0,
                        'pending': refunds_result['pending'] if refunds_result else 0,
                        'rate_per_day': self.get_rate('refunds_total', window_seconds=86400) * 86400
                    },
                    'errors': {
                        'total': self.get_counter('errors_total'),
                        'rate_per_minute': self.get_rate('errors_total', window_seconds=60) * 60,
                        'by_type': {
                            '4xx': self.get_counter('http_errors', {'type': '4xx'}),
                            '5xx': self.get_counter('http_errors', {'type': '5xx'})
                        }
                    },
                    'performance': {
                        'avg_response_time_ms': self.get_histogram_stats('http_request_duration_seconds').get('avg', 0) * 1000,
                        'p95_response_time_ms': self.get_histogram_stats('http_request_duration_seconds').get('p95', 0) * 1000,
                        'p99_response_time_ms': self.get_histogram_stats('http_request_duration_seconds').get('p99', 0) * 1000
                    }
                }
        except Exception as e:
            # Fall back to in-memory counters only
            pass
        
        return {
            'orders': {
                'total': self.get_counter('orders_total'),
                'successful': self.get_counter('orders_total', {'status': 'success'}),
                'failed': self.get_counter('orders_total', {'status': 'failed'}),
                'rate_per_minute': self.get_rate('orders_total', window_seconds=60) * 60
            },
            'refunds': {
                'total': self.get_counter('refunds_total'),
                'approved': self.get_counter('refunds_total', {'status': 'approved'}),
                'rejected': self.get_counter('refunds_total', {'status': 'rejected'}),
                'pending': self.get_counter('refunds_total', {'status': 'pending'}),
                'rate_per_day': self.get_rate('refunds_total', window_seconds=86400) * 86400
            },
            'errors': {
                'total': self.get_counter('errors_total'),
                'rate_per_minute': self.get_rate('errors_total', window_seconds=60) * 60,
                'by_type': {
                    '4xx': self.get_counter('http_errors', {'type': '4xx'}),
                    '5xx': self.get_counter('http_errors', {'type': '5xx'})
                }
            },
            'performance': {
                'avg_response_time_ms': self.get_histogram_stats('http_request_duration_seconds').get('avg', 0) * 1000,
                'p95_response_time_ms': self.get_histogram_stats('http_request_duration_seconds').get('p95', 0) * 1000,
                'p99_response_time_ms': self.get_histogram_stats('http_request_duration_seconds').get('p99', 0) * 1000
            }
        }


# Global metrics collector instance
metrics_collector = MetricsCollector()


def track_request_duration(endpoint: str):
    """Decorator to track request duration."""
    def decorator(f):
        from functools import wraps
        
        @wraps(f)
        def wrapped(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = f(*args, **kwargs)
                status = 'success'
                return result
            except Exception as e:
                status = 'error'
                metrics_collector.increment_counter('errors_total')
                raise
            finally:
                duration = time.time() - start_time
                metrics_collector.observe(
                    'http_request_duration_seconds',
                    duration,
                    labels={'endpoint': endpoint, 'status': status}
                )
        
        return wrapped
    return decorator