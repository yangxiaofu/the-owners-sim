"""
Performance Metrics Tracker - System performance monitoring and optimization

This module provides comprehensive system performance tracking for the game engine,
monitoring execution times, memory usage, bottlenecks, and optimization opportunities.

The performance tracker operates independently of game logic to provide:
- Real-time performance monitoring during game execution
- Bottleneck identification and analysis
- Memory usage tracking and leak detection  
- Execution time profiling for optimization
- System resource utilization metrics
- Performance regression detection

Design Principles:
- Minimal overhead: performance tracking should not impact game performance
- Real-time monitoring: immediate feedback on performance issues
- Actionable insights: metrics that directly inform optimization decisions
- Historical tracking: trends and regression detection over time
- Modular monitoring: can track specific subsystems independently
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, DefaultDict
from collections import defaultdict, deque
from enum import Enum
import time
import statistics
import threading
import psutil
import gc
from contextlib import contextmanager

from game_engine.plays.data_structures import PlayResult


class PerformanceCategory(Enum):
    """Categories of performance metrics"""
    PLAY_EXECUTION = "play_execution"
    STATE_TRANSITION = "state_transition" 
    STATISTICS_TRACKING = "statistics_tracking"
    VALIDATION = "validation"
    CALCULATION = "calculation"
    DATABASE = "database"
    MEMORY = "memory"
    SYSTEM = "system"
    OVERALL_GAME = "overall_game"


@dataclass
class PerformanceMetric:
    """Individual performance measurement"""
    name: str
    category: PerformanceCategory
    value: float
    unit: str  # "ms", "MB", "count", "percentage"
    timestamp: float
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category.value,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp,
            "context": self.context
        }


@dataclass
class ExecutionProfile:
    """Profile of execution times for a specific operation"""
    operation_name: str
    category: PerformanceCategory
    
    # Execution time tracking
    execution_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    total_executions: int = 0
    total_time: float = 0.0
    
    # Statistical analysis
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0
    median_time: float = 0.0
    p95_time: float = 0.0  # 95th percentile
    p99_time: float = 0.0  # 99th percentile
    
    # Performance thresholds and alerts
    warning_threshold: Optional[float] = None
    error_threshold: Optional[float] = None
    warnings_triggered: int = 0
    errors_triggered: int = 0
    
    def add_execution_time(self, execution_time: float) -> None:
        """Add new execution time measurement"""
        self.execution_times.append(execution_time)
        self.total_executions += 1
        self.total_time += execution_time
        
        # Update statistics
        self.min_time = min(self.min_time, execution_time)
        self.max_time = max(self.max_time, execution_time)
        self.avg_time = self.total_time / self.total_executions
        
        # Calculate percentiles if we have enough data
        if len(self.execution_times) >= 10:
            sorted_times = sorted(self.execution_times)
            self.median_time = statistics.median(sorted_times)
            
            # Calculate percentiles
            n = len(sorted_times)
            self.p95_time = sorted_times[int(0.95 * n)]
            self.p99_time = sorted_times[int(0.99 * n)]
        
        # Check thresholds
        if self.warning_threshold and execution_time > self.warning_threshold:
            self.warnings_triggered += 1
            
        if self.error_threshold and execution_time > self.error_threshold:
            self.errors_triggered += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get statistical summary of performance"""
        return {
            "operation_name": self.operation_name,
            "category": self.category.value,
            "total_executions": self.total_executions,
            "total_time_ms": self.total_time * 1000,
            "avg_time_ms": self.avg_time * 1000,
            "min_time_ms": self.min_time * 1000,
            "max_time_ms": self.max_time * 1000,
            "median_time_ms": self.median_time * 1000,
            "p95_time_ms": self.p95_time * 1000,
            "p99_time_ms": self.p99_time * 1000,
            "warnings_triggered": self.warnings_triggered,
            "errors_triggered": self.errors_triggered,
            "executions_per_second": self.total_executions / self.total_time if self.total_time > 0 else 0
        }


@dataclass
class SystemResourceMetrics:
    """System resource utilization metrics"""
    cpu_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_percent: float = 0.0
    disk_io_read_mb: float = 0.0
    disk_io_write_mb: float = 0.0
    network_sent_mb: float = 0.0
    network_recv_mb: float = 0.0
    
    # Process-specific metrics
    process_cpu_percent: float = 0.0
    process_memory_mb: float = 0.0
    process_threads: int = 0
    
    # Python-specific metrics  
    garbage_collections: int = 0
    objects_tracked: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_percent": self.cpu_percent,
            "memory_used_mb": self.memory_used_mb,
            "memory_percent": self.memory_percent,
            "disk_io_read_mb": self.disk_io_read_mb,
            "disk_io_write_mb": self.disk_io_write_mb,
            "network_sent_mb": self.network_sent_mb,
            "network_recv_mb": self.network_recv_mb,
            "process_cpu_percent": self.process_cpu_percent,
            "process_memory_mb": self.process_memory_mb,
            "process_threads": self.process_threads,
            "garbage_collections": self.garbage_collections,
            "objects_tracked": self.objects_tracked
        }


class PerformanceTracker:
    """
    Comprehensive system performance tracking and monitoring.
    
    Provides real-time performance metrics, bottleneck identification, and
    optimization insights for the game simulation engine.
    
    Key Features:
    - Minimal overhead performance monitoring
    - Real-time bottleneck detection
    - Memory usage and leak tracking
    - Execution profiling for all major operations
    - System resource monitoring
    - Performance regression alerts
    - Historical trend analysis
    """
    
    def __init__(self, enable_system_monitoring: bool = True):
        self.enable_system_monitoring = enable_system_monitoring
        self.start_time = time.time()
        
        # Performance profiles for different operations
        self.execution_profiles: Dict[str, ExecutionProfile] = {}
        
        # Metrics storage
        self.metrics_history: List[PerformanceMetric] = []
        self.system_metrics: List[SystemResourceMetrics] = []
        
        # Real-time monitoring
        self.current_operations: Dict[str, float] = {}  # operation -> start_time
        
        # Alert thresholds (in seconds)
        self.default_thresholds = {
            PerformanceCategory.PLAY_EXECUTION: {"warning": 0.1, "error": 0.5},
            PerformanceCategory.STATE_TRANSITION: {"warning": 0.05, "error": 0.2},
            PerformanceCategory.STATISTICS_TRACKING: {"warning": 0.01, "error": 0.05},
            PerformanceCategory.VALIDATION: {"warning": 0.01, "error": 0.05},
            PerformanceCategory.CALCULATION: {"warning": 0.01, "error": 0.05}
        }
        
        # System monitoring setup
        if self.enable_system_monitoring:
            self.process = psutil.Process()
            self._baseline_system_metrics()
            
        # Performance alerts
        self.alerts: List[Dict[str, Any]] = []
    
    def _baseline_system_metrics(self) -> None:
        """Capture baseline system metrics"""
        self.baseline_cpu = psutil.cpu_percent()
        self.baseline_memory = psutil.virtual_memory().percent
        self.baseline_disk_io = psutil.disk_io_counters()
        self.baseline_network = psutil.net_io_counters()
    
    @contextmanager
    def measure_operation(self, operation_name: str, 
                         category: PerformanceCategory = PerformanceCategory.OVERALL_GAME,
                         context: Optional[Dict[str, Any]] = None):
        """Context manager for measuring operation execution time"""
        start_time = time.time()
        self.current_operations[operation_name] = start_time
        
        try:
            yield
        finally:
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Remove from current operations
            self.current_operations.pop(operation_name, None)
            
            # Record the measurement
            self.record_execution_time(operation_name, category, execution_time, context)
    
    def record_execution_time(self, operation_name: str, category: PerformanceCategory,
                             execution_time: float, context: Optional[Dict[str, Any]] = None) -> None:
        """Record execution time for an operation"""
        
        # Get or create execution profile
        if operation_name not in self.execution_profiles:
            self.execution_profiles[operation_name] = ExecutionProfile(
                operation_name=operation_name,
                category=category
            )
            
            # Set default thresholds
            if category in self.default_thresholds:
                thresholds = self.default_thresholds[category]
                self.execution_profiles[operation_name].warning_threshold = thresholds["warning"]
                self.execution_profiles[operation_name].error_threshold = thresholds["error"]
        
        profile = self.execution_profiles[operation_name]
        profile.add_execution_time(execution_time)
        
        # Create performance metric
        metric = PerformanceMetric(
            name=f"{operation_name}_execution_time",
            category=category,
            value=execution_time * 1000,  # Convert to milliseconds
            unit="ms",
            timestamp=time.time(),
            context=context or {}
        )
        
        self.metrics_history.append(metric)
        
        # Check for performance alerts
        self._check_performance_alerts(operation_name, execution_time, category)
    
    def _check_performance_alerts(self, operation_name: str, execution_time: float, 
                                 category: PerformanceCategory) -> None:
        """Check if performance thresholds are exceeded"""
        profile = self.execution_profiles[operation_name]
        
        alert_triggered = False
        alert_level = None
        
        if profile.error_threshold and execution_time > profile.error_threshold:
            alert_level = "ERROR"
            alert_triggered = True
        elif profile.warning_threshold and execution_time > profile.warning_threshold:
            alert_level = "WARNING"
            alert_triggered = True
        
        if alert_triggered:
            alert = {
                "timestamp": time.time(),
                "level": alert_level,
                "operation": operation_name,
                "category": category.value,
                "execution_time_ms": execution_time * 1000,
                "threshold_ms": (profile.error_threshold if alert_level == "ERROR" 
                                else profile.warning_threshold) * 1000,
                "avg_time_ms": profile.avg_time * 1000,
                "message": f"{operation_name} took {execution_time*1000:.2f}ms "
                          f"(threshold: {(profile.error_threshold if alert_level == 'ERROR' else profile.warning_threshold)*1000:.2f}ms)"
            }
            
            self.alerts.append(alert)
    
    def record_play_performance(self, play_result: PlayResult, execution_time: float) -> None:
        """Record performance metrics for play execution"""
        
        operation_name = f"play_{play_result.play_type}"
        context = {
            "play_type": play_result.play_type,
            "outcome": play_result.outcome,
            "yards_gained": play_result.yards_gained,
            "down": play_result.down,
            "distance": play_result.distance
        }
        
        self.record_execution_time(
            operation_name, 
            PerformanceCategory.PLAY_EXECUTION, 
            execution_time, 
            context
        )
        
        # Record additional play-specific metrics
        self._record_metric(
            f"play_{play_result.play_type}_yards",
            PerformanceCategory.PLAY_EXECUTION,
            abs(play_result.yards_gained),
            "yards",
            context
        )
        
        self._record_metric(
            f"play_{play_result.play_type}_time_elapsed",
            PerformanceCategory.PLAY_EXECUTION,
            play_result.time_elapsed,
            "seconds",
            context
        )
    
    def record_system_metrics(self) -> SystemResourceMetrics:
        """Record current system resource metrics"""
        if not self.enable_system_monitoring:
            return SystemResourceMetrics()
        
        try:
            # System-wide metrics
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk_io = psutil.disk_io_counters()
            network = psutil.net_io_counters()
            
            # Process-specific metrics
            process_cpu = self.process.cpu_percent()
            process_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            process_threads = self.process.num_threads()
            
            # Python-specific metrics
            gc_stats = gc.get_stats()
            gc_count = sum(stat.get('collections', 0) for stat in gc_stats)
            objects_tracked = len(gc.get_objects())
            
            metrics = SystemResourceMetrics(
                cpu_percent=cpu_percent,
                memory_used_mb=memory.used / 1024 / 1024,
                memory_percent=memory.percent,
                disk_io_read_mb=(disk_io.read_bytes - self.baseline_disk_io.read_bytes) / 1024 / 1024 if self.baseline_disk_io else 0,
                disk_io_write_mb=(disk_io.write_bytes - self.baseline_disk_io.write_bytes) / 1024 / 1024 if self.baseline_disk_io else 0,
                network_sent_mb=(network.bytes_sent - self.baseline_network.bytes_sent) / 1024 / 1024 if self.baseline_network else 0,
                network_recv_mb=(network.bytes_recv - self.baseline_network.bytes_recv) / 1024 / 1024 if self.baseline_network else 0,
                process_cpu_percent=process_cpu,
                process_memory_mb=process_memory,
                process_threads=process_threads,
                garbage_collections=gc_count,
                objects_tracked=objects_tracked
            )
            
            self.system_metrics.append(metrics)
            return metrics
            
        except Exception as e:
            # Fallback to basic metrics if system monitoring fails
            return SystemResourceMetrics()
    
    def _record_metric(self, name: str, category: PerformanceCategory, value: float,
                      unit: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Record a custom performance metric"""
        metric = PerformanceMetric(
            name=name,
            category=category,
            value=value,
            unit=unit,
            timestamp=time.time(),
            context=context or {}
        )
        
        self.metrics_history.append(metric)
    
    def get_operation_profile(self, operation_name: str) -> Optional[Dict[str, Any]]:
        """Get performance profile for a specific operation"""
        if operation_name in self.execution_profiles:
            return self.execution_profiles[operation_name].get_summary()
        return None
    
    def get_category_summary(self, category: PerformanceCategory) -> Dict[str, Any]:
        """Get performance summary for an entire category"""
        category_profiles = [
            profile for profile in self.execution_profiles.values() 
            if profile.category == category
        ]
        
        if not category_profiles:
            return {"category": category.value, "no_data": True}
        
        # Aggregate statistics
        total_executions = sum(profile.total_executions for profile in category_profiles)
        total_time = sum(profile.total_time for profile in category_profiles)
        avg_time = total_time / total_executions if total_executions > 0 else 0
        
        all_times = []
        for profile in category_profiles:
            all_times.extend(profile.execution_times)
        
        return {
            "category": category.value,
            "operations_count": len(category_profiles),
            "total_executions": total_executions,
            "total_time_ms": total_time * 1000,
            "avg_time_ms": avg_time * 1000,
            "min_time_ms": min(profile.min_time for profile in category_profiles) * 1000,
            "max_time_ms": max(profile.max_time for profile in category_profiles) * 1000,
            "median_time_ms": statistics.median(all_times) * 1000 if all_times else 0,
            "operations": [profile.get_summary() for profile in category_profiles]
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        current_time = time.time()
        uptime = current_time - self.start_time
        
        # Category summaries
        category_summaries = {}
        for category in PerformanceCategory:
            summary = self.get_category_summary(category)
            if not summary.get("no_data"):
                category_summaries[category.value] = summary
        
        # Overall statistics
        total_operations = sum(profile.total_executions for profile in self.execution_profiles.values())
        
        # Recent system metrics
        recent_system_metrics = self.system_metrics[-1] if self.system_metrics else None
        
        # Performance alerts summary
        recent_alerts = [alert for alert in self.alerts if current_time - alert["timestamp"] < 300]  # Last 5 minutes
        alert_summary = {
            "total_alerts": len(self.alerts),
            "recent_alerts": len(recent_alerts),
            "error_alerts": len([a for a in self.alerts if a["level"] == "ERROR"]),
            "warning_alerts": len([a for a in self.alerts if a["level"] == "WARNING"])
        }
        
        return {
            "uptime_seconds": uptime,
            "total_operations": total_operations,
            "operations_per_second": total_operations / uptime if uptime > 0 else 0,
            "categories": category_summaries,
            "alerts": alert_summary,
            "recent_alerts": recent_alerts[-10:],  # Last 10 alerts
            "system_metrics": recent_system_metrics.to_dict() if recent_system_metrics else None,
            "currently_executing": list(self.current_operations.keys())
        }
    
    def get_bottleneck_analysis(self) -> Dict[str, Any]:
        """Identify performance bottlenecks and optimization opportunities"""
        
        # Find slowest operations
        slowest_operations = sorted(
            self.execution_profiles.values(),
            key=lambda p: p.avg_time,
            reverse=True
        )[:10]
        
        # Find operations with highest variance (inconsistent performance)
        high_variance_operations = []
        for profile in self.execution_profiles.values():
            if len(profile.execution_times) > 10:
                variance = statistics.variance(profile.execution_times)
                if variance > profile.avg_time * 0.5:  # High variance threshold
                    high_variance_operations.append((profile, variance))
        
        high_variance_operations.sort(key=lambda x: x[1], reverse=True)
        
        # Find operations with most alerts
        operations_with_alerts = sorted(
            [profile for profile in self.execution_profiles.values() if profile.warnings_triggered > 0 or profile.errors_triggered > 0],
            key=lambda p: p.errors_triggered * 10 + p.warnings_triggered,
            reverse=True
        )[:10]
        
        # Calculate total time spent per operation type
        time_by_operation = {}
        for profile in self.execution_profiles.values():
            time_by_operation[profile.operation_name] = profile.total_time
        
        top_time_consumers = sorted(time_by_operation.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "slowest_operations": [profile.get_summary() for profile in slowest_operations],
            "high_variance_operations": [
                {**profile.get_summary(), "variance": variance} 
                for profile, variance in high_variance_operations[:10]
            ],
            "operations_with_alerts": [profile.get_summary() for profile in operations_with_alerts],
            "top_time_consumers": [
                {"operation": op, "total_time_ms": time * 1000} 
                for op, time in top_time_consumers
            ],
            "optimization_recommendations": self._generate_optimization_recommendations()
        }
    
    def _generate_optimization_recommendations(self) -> List[str]:
        """Generate optimization recommendations based on performance data"""
        recommendations = []
        
        # Check for slow operations
        for profile in self.execution_profiles.values():
            if profile.avg_time > 0.1:  # 100ms threshold
                recommendations.append(
                    f"Consider optimizing '{profile.operation_name}' - "
                    f"average execution time is {profile.avg_time*1000:.2f}ms"
                )
        
        # Check memory usage
        if self.system_metrics:
            recent_memory = self.system_metrics[-10:]  # Last 10 measurements
            avg_memory = sum(m.process_memory_mb for m in recent_memory) / len(recent_memory)
            
            if avg_memory > 500:  # 500MB threshold
                recommendations.append(
                    f"High memory usage detected: {avg_memory:.1f}MB average. "
                    "Consider memory optimization."
                )
        
        # Check for frequent alerts
        frequent_alert_operations = [
            profile.operation_name for profile in self.execution_profiles.values()
            if profile.warnings_triggered > 10 or profile.errors_triggered > 1
        ]
        
        if frequent_alert_operations:
            recommendations.append(
                f"Operations with frequent performance alerts: {', '.join(frequent_alert_operations)}"
            )
        
        return recommendations
    
    def export_metrics(self, filename: Optional[str] = None) -> str:
        """Export all performance metrics to JSON"""
        import json
        
        export_data = {
            "performance_summary": self.get_performance_summary(),
            "bottleneck_analysis": self.get_bottleneck_analysis(),
            "execution_profiles": {
                name: profile.get_summary() 
                for name, profile in self.execution_profiles.items()
            },
            "recent_system_metrics": [
                metrics.to_dict() for metrics in self.system_metrics[-100:]  # Last 100 measurements
            ],
            "all_alerts": self.alerts,
            "metrics_history": [metric.to_dict() for metric in self.metrics_history[-1000:]]  # Last 1000 metrics
        }
        
        json_str = json.dumps(export_data, indent=2, default=str)
        
        if filename:
            with open(filename, 'w') as f:
                f.write(json_str)
        
        return json_str
    
    def reset(self) -> None:
        """Reset all performance metrics"""
        self.__init__(self.enable_system_monitoring)