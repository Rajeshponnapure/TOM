"""
TOM Autonomous Agent -- Auto-Scaling System
Manages system resources, parallel execution, performance optimization,
load balancing, and distributed processing for Tom.
"""

import json
import os
import sys
import math
import time
import uuid
import random
import threading
import traceback
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_EXCEPTION
from typing import Any, Dict, List, Optional, Tuple, Union, Callable

_RESOURCE_MONITOR = Dict[str, Any]

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

try:
    import GPUtil
    _HAS_GPUTIL = True
except ImportError:
    _HAS_GPUTIL = False

_RESPONSE = Dict[str, Any]

def _ok(result=None, message="OK"):
    return {"status": "success", "result": result, "message": message}

def _err(message):
    return {"status": "error", "result": None, "message": message}


class AutoScaler:
    """Auto-scaling resource manager for Tom.
    Manages system resources, parallel execution, performance optimization.
    """

    def __init__(self, config: dict = None):
        self._config = config or {}
        self._schedulers: Dict[str, threading.Thread] = {}
        self._scheduler_flags: Dict[str, threading.Event] = {}
        self._performance_history: List[dict] = []
        self._task_timings: Dict[str, List[float]] = defaultdict(list)
        self._resource_log: List[dict] = []
        self._lock = threading.Lock()
        self._active_workers: Dict[str, Dict] = {}
        self._worker_loads: Dict[str, int] = defaultdict(int)
        self._throttle_active = False
        self._throttle_factor = 1.0
        self._cpu_count = self._detect_cpu_count()
        self._start_time = time.time()
        self._task_counter: Dict[str, int] = defaultdict(int)
        self._shard_registry: Dict[str, dict] = {}
        self._balance_strategy = self._config.get("balance_strategy", "round_robin")

    def _detect_cpu_count(self) -> int:
        try:
            if _HAS_PSUTIL:
                return psutil.cpu_count(logical=True) or os.cpu_count() or 4
            return os.cpu_count() or 4
        except Exception:
            return 4

    # ------------------------------------------------------------------
    # 1. detect_resources
    # ------------------------------------------------------------------
    def detect_resources(self) -> _RESPONSE:
        """Detect CPU cores, RAM, disk space, GPU availability.
        Return system capability report."""
        try:
            report = {
                "cpu": self._detect_cpu_section(),
                "memory": self._detect_memory_section(),
                "disk": self._detect_disk_section(),
                "gpu": self._detect_gpu_section(),
                "system": self._detect_system_info(),
                "python": {
                    "version": sys.version,
                    "executable": sys.executable,
                    "platform": sys.platform,
                },
                "psutil_available": _HAS_PSUTIL,
                "gputil_available": _HAS_GPUTIL,
                "detected_at": datetime.now().isoformat(),
            }
            return _ok(report, "System resources detected successfully")
        except Exception as exc:
            return _err(f"Resource detection failed: {exc}")

    def _detect_cpu_section(self) -> dict:
        result = {
            "logical_cores": self._cpu_count,
            "physical_cores": None,
            "usage_percent": None,
            "frequency": None,
            "load_avg": None,
        }
        try:
            if _HAS_PSUTIL:
                result["physical_cores"] = psutil.cpu_count(logical=False)
                result["usage_percent"] = psutil.cpu_percent(interval=0.1)
                freq = psutil.cpu_freq()
                if freq:
                    result["frequency"] = {
                        "current_mhz": freq.current,
                        "min_mhz": freq.min,
                        "max_mhz": freq.max,
                    }
                if hasattr(os, "getloadavg"):
                    result["load_avg"] = os.getloadavg()
        except Exception:
            pass
        return result

    def _detect_memory_section(self) -> dict:
        result = {
            "total_gb": None,
            "available_gb": None,
            "used_gb": None,
            "percent_used": None,
            "swap_total_gb": None,
            "swap_used_gb": None,
        }
        try:
            if _HAS_PSUTIL:
                mem = psutil.virtual_memory()
                result["total_gb"] = round(mem.total / (1024 ** 3), 2)
                result["available_gb"] = round(mem.available / (1024 ** 3), 2)
                result["used_gb"] = round(mem.used / (1024 ** 3), 2)
                result["percent_used"] = mem.percent
                swap = psutil.swap_memory()
                result["swap_total_gb"] = round(swap.total / (1024 ** 3), 2)
                result["swap_used_gb"] = round(swap.used / (1024 ** 3), 2)
        except Exception:
            pass
        return result

    def _detect_disk_section(self) -> dict:
        result = {
            "partitions": [],
            "total_gb": None,
            "used_gb": None,
            "free_gb": None,
        }
        try:
            if _HAS_PSUTIL:
                total = 0
                used = 0
                free = 0
                for part in psutil.disk_partitions():
                    try:
                        usage = psutil.disk_usage(part.mountpoint)
                        pinfo = {
                            "device": part.device,
                            "mountpoint": part.mountpoint,
                            "fstype": part.fstype,
                            "total_gb": round(usage.total / (1024 ** 3), 2),
                            "used_gb": round(usage.used / (1024 ** 3), 2),
                            "free_gb": round(usage.free / (1024 ** 3), 2),
                            "percent_used": usage.percent,
                        }
                        result["partitions"].append(pinfo)
                        total += usage.total
                        used += usage.used
                        free += usage.free
                    except Exception:
                        continue
                result["total_gb"] = round(total / (1024 ** 3), 2)
                result["used_gb"] = round(used / (1024 ** 3), 2)
                result["free_gb"] = round(free / (1024 ** 3), 2)
        except Exception:
            pass
        return result

    def _detect_gpu_section(self) -> dict:
        result = {
            "available": False,
            "devices": [],
            "total_vram_gb": None,
            "driver_version": None,
        }
        try:
            if _HAS_GPUTIL:
                gpus = GPUtil.getGPUs()
                if gpus:
                    result["available"] = True
                    for gpu in gpus:
                        result["devices"].append({
                            "id": gpu.id,
                            "name": gpu.name,
                            "load_percent": gpu.load * 100,
                            "memory_used_mb": gpu.memoryUsed,
                            "memory_total_mb": gpu.memoryTotal,
                            "temperature_c": gpu.temperature,
                            "driver": gpu.driver,
                        })
                    result["total_vram_gb"] = round(
                        sum(g.memoryTotal for g in gpus) / 1024, 2
                    )
                    if gpus:
                        result["driver_version"] = gpus[0].driver
            elif _HAS_PSUTIL:
                nvidia_smi = os.popen("nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>nul")
                output = nvidia_smi.read().strip()
                nvidia_smi.close()
                if output and "N/A" not in output:
                    result["available"] = True
                    for line in output.split("\n"):
                        parts = [p.strip() for p in line.split(",")]
                        if len(parts) >= 2:
                            result["devices"].append({
                                "name": parts[0],
                                "memory_total": parts[1],
                                "driver": parts[2] if len(parts) > 2 else "unknown",
                            })
        except Exception:
            pass
        return result

    def _detect_system_info(self) -> dict:
        result = {
            "hostname": None,
            "os": None,
            "boot_time": None,
            "uptime_seconds": None,
            "processes": None,
        }
        try:
            if _HAS_PSUTIL:
                import socket
                result["hostname"] = socket.gethostname()
                result["os"] = f"{sys.platform} {psutil.WINDOWS and 'Windows' or psutil.LINUX and 'Linux' or psutil.MACOS and 'macOS' or 'Unknown'}"
                result["boot_time"] = datetime.fromtimestamp(psutil.boot_time()).isoformat()
                result["uptime_seconds"] = int(time.time() - psutil.boot_time())
                result["processes"] = len(psutil.pids())
        except Exception:
            result["hostname"] = os.environ.get("COMPUTERNAME", "unknown")
            result["os"] = sys.platform
        return result

    # ------------------------------------------------------------------
    # 2. parallel_execute
    # ------------------------------------------------------------------
    def parallel_execute(self, tasks: list, max_workers: int = None) -> _RESPONSE:
        """Execute multiple tasks in parallel using ThreadPoolExecutor.
        Auto-detect optimal worker count based on CPU cores."""
        if not tasks:
            return _ok([], "No tasks to execute")

        if max_workers is None:
            max_workers = self._cpu_count * 2

        worker_count = min(max_workers, len(tasks))
        results = []
        errors = []
        start = time.time()

        try:
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                future_map = {}
                for i, task in enumerate(tasks):
                    if callable(task):
                        future = executor.submit(task)
                        future_map[future] = (i, "callable", None)
                    elif isinstance(task, (list, tuple)) and len(task) >= 1:
                        fn = task[0]
                        args = task[1] if len(task) > 1 else ()
                        kwargs = task[2] if len(task) > 2 else {}
                        if not callable(fn):
                            future = executor.submit(self._noop, fn)
                            future_map[future] = (i, "non_callable", fn)
                        else:
                            future = executor.submit(fn, *args, **kwargs)
                            future_map[future] = (i, "callable_with_args", fn)
                    elif isinstance(task, dict) and "func" in task:
                        fn = task["func"]
                        args = task.get("args", ())
                        kwargs = task.get("kwargs", {})
                        future = executor.submit(fn, *args, **kwargs)
                        future_map[future] = (i, "dict_task", fn)
                    else:
                        future = executor.submit(self._noop, task)
                        future_map[future] = (i, "raw_value", task)

                for future in as_completed(future_map):
                    idx, task_type, desc = future_map[future]
                    try:
                        res = future.result()
                        results.append({
                            "index": idx,
                            "type": task_type,
                            "result": res,
                            "status": "completed",
                        })
                    except Exception as exc:
                        errors.append({
                            "index": idx,
                            "type": task_type,
                            "error": str(exc),
                            "status": "failed",
                        })
                        results.append({
                            "index": idx,
                            "type": task_type,
                            "result": None,
                            "status": "failed",
                            "error": str(exc),
                        })

            elapsed = round(time.time() - start, 4)
            timing_key = "parallel_execute"
            with self._lock:
                self._task_timings[timing_key].append(elapsed)
                self._task_counter["parallel_execute"] += len(tasks)

            return _ok({
                "results": sorted(results, key=lambda x: x["index"]),
                "total_tasks": len(tasks),
                "completed": len([r for r in results if r["status"] == "completed"]),
                "failed": len(errors),
                "worker_count": worker_count,
                "elapsed_seconds": elapsed,
            }, f"Executed {len(tasks)} tasks with {worker_count} workers in {elapsed}s")
        except Exception as exc:
            return _err(f"Parallel execution failed: {exc}")

    def _noop(self, value):
        return value

    # ------------------------------------------------------------------
    # 3. optimize_workers
    # ------------------------------------------------------------------
    def optimize_workers(self, task_type: str) -> _RESPONSE:
        """Return optimal worker count based on task type.
        CPU-bound: use cpu_count, IO-bound: use cpu_count * 5."""
        try:
            ttype = task_type.lower().strip()
            base = self._cpu_count

            if ttype in ("cpu", "cpu-bound", "cpu_bound", "compute", "computation"):
                count = base
                reasoning = f"CPU-bound tasks use cpu_count ({base})"
            elif ttype in ("io", "io-bound", "io_bound", "network", "disk", "file"):
                count = base * 5
                reasoning = f"IO-bound tasks use cpu_count * 5 ({base} * 5 = {count})"
            elif ttype in ("mixed", "hybrid", "general"):
                count = base * 2
                reasoning = f"Mixed tasks use cpu_count * 2 ({base} * 2 = {count})"
            elif ttype in ("gpu", "gpu-bound", "gpu_bound"):
                gpu_count = 0
                if _HAS_GPUTIL:
                    try:
                        gpu_count = len(GPUtil.getGPUs())
                    except Exception:
                        pass
                count = max(gpu_count, 1) * 2
                reasoning = f"GPU tasks use gpu_count * 2 ({count})"
            elif ttype in ("memory", "memory-bound", "memory_bound", "ram"):
                count = max(1, base // 2)
                reasoning = f"Memory-bound tasks use cpu_count / 2 ({count})"
            elif ttype in ("real-time", "realtime", "low_latency", "low-latency"):
                count = max(1, base // 4)
                reasoning = f"Real-time tasks use cpu_count / 4 ({count})"
            else:
                count = base
                reasoning = f"Unknown type '{task_type}', defaulting to cpu_count ({base})"

            return _ok({
                "task_type": task_type,
                "recommended_workers": count,
                "cpu_count": base,
                "reasoning": reasoning,
            }, f"Optimal workers for '{task_type}': {count}")
        except Exception as exc:
            return _err(f"Worker optimization failed: {exc}")

    # ------------------------------------------------------------------
    # 4. monitor_performance
    # ------------------------------------------------------------------
    def monitor_performance(self, interval: float = 1.0) -> _RESPONSE:
        """Monitor CPU, memory, disk usage. Return performance metrics."""
        try:
            metrics = self._collect_performance_metrics()
            alerts = self._check_thresholds(metrics)
            metrics["alerts"] = alerts
            metrics["interval_seconds"] = interval
            metrics["timestamp"] = datetime.now().isoformat()
            metrics["uptime_seconds"] = int(time.time() - self._start_time)

            with self._lock:
                self._performance_history.append(metrics)
                if len(self._performance_history) > 1000:
                    self._performance_history = self._performance_history[-500:]
                self._resource_log.append({
                    "timestamp": metrics["timestamp"],
                    "cpu_percent": metrics.get("cpu", {}).get("percent"),
                    "ram_percent": metrics.get("memory", {}).get("percent"),
                    "disk_percent": metrics.get("disk", {}).get("percent"),
                })

            status = "healthy"
            if any(a.get("level") == "critical" for a in alerts):
                status = "critical"
            elif any(a.get("level") == "warning" for a in alerts):
                status = "warning"

            return _ok({
                "status": status,
                "metrics": metrics,
                "alert_count": len(alerts),
                "monitoring_since": datetime.fromtimestamp(self._start_time).isoformat(),
            }, f"Performance monitored: CPU {metrics.get('cpu', {}).get('percent', 'N/A')}%, RAM {metrics.get('memory', {}).get('percent', 'N/A')}%, {len(alerts)} alert(s)")
        except Exception as exc:
            return _err(f"Performance monitoring failed: {exc}")

    def _collect_performance_metrics(self) -> dict:
        metrics = {
            "cpu": self._get_cpu_metrics(),
            "memory": self._get_memory_metrics(),
            "disk": self._get_disk_metrics(),
            "network": self._get_network_metrics(),
        }
        if _HAS_GPUTIL:
            try:
                metrics["gpu"] = self._get_gpu_metrics()
            except Exception:
                pass
        return metrics

    def _get_cpu_metrics(self) -> dict:
        result = {"percent": None, "count": self._cpu_count, "per_core": []}
        try:
            if _HAS_PSUTIL:
                result["percent"] = psutil.cpu_percent(interval=0.1)
                result["per_core"] = psutil.cpu_percent(interval=0.1, percpu=True)
                result["stats"] = {
                    "ctx_switches": psutil.cpu_stats().ctx_switches,
                    "interrupts": psutil.cpu_stats().interrupts,
                    "soft_interrupts": psutil.cpu_stats().soft_interrupts,
                }
        except Exception:
            pass
        return result

    def _get_memory_metrics(self) -> dict:
        result = {
            "percent": None,
            "total_gb": None,
            "available_gb": None,
            "used_gb": None,
        }
        try:
            if _HAS_PSUTIL:
                mem = psutil.virtual_memory()
                result["percent"] = mem.percent
                result["total_gb"] = round(mem.total / (1024 ** 3), 2)
                result["available_gb"] = round(mem.available / (1024 ** 3), 2)
                result["used_gb"] = round(mem.used / (1024 ** 3), 2)
                result["swap_percent"] = psutil.swap_memory().percent
        except Exception:
            pass
        return result

    def _get_disk_metrics(self) -> dict:
        result = {"percent": None, "total_gb": None, "used_gb": None, "free_gb": None, "io_counters": None}
        try:
            if _HAS_PSUTIL:
                usage = psutil.disk_usage(os.path.abspath(os.sep))
                result["percent"] = usage.percent
                result["total_gb"] = round(usage.total / (1024 ** 3), 2)
                result["used_gb"] = round(usage.used / (1024 ** 3), 2)
                result["free_gb"] = round(usage.free / (1024 ** 3), 2)
                io = psutil.disk_io_counters()
                if io:
                    result["io_counters"] = {
                        "read_bytes": io.read_bytes,
                        "write_bytes": io.write_bytes,
                        "read_count": io.read_count,
                        "write_count": io.write_count,
                    }
        except Exception:
            pass
        return result

    def _get_network_metrics(self) -> dict:
        result = {"bytes_sent": None, "bytes_recv": None, "connections": None}
        try:
            if _HAS_PSUTIL:
                net = psutil.net_io_counters()
                result["bytes_sent"] = net.bytes_sent
                result["bytes_recv"] = net.bytes_recv
                result["packets_sent"] = net.packets_sent
                result["packets_recv"] = net.packets_recv
                try:
                    result["connections"] = len(psutil.net_connections())
                except Exception:
                    result["connections"] = "access_denied"
        except Exception:
            pass
        return result

    def _get_gpu_metrics(self) -> dict:
        result = {"available": False, "devices": []}
        if _HAS_GPUTIL:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    result["available"] = True
                    for gpu in gpus:
                        result["devices"].append({
                            "name": gpu.name,
                            "load_percent": gpu.load * 100,
                            "memory_used_mb": gpu.memoryUsed,
                            "memory_total_mb": gpu.memoryTotal,
                            "temperature_c": gpu.temperature,
                        })
            except Exception:
                pass
        return result

    def _check_thresholds(self, metrics: dict) -> list:
        alerts = []
        cpu_pct = metrics.get("cpu", {}).get("percent")
        if cpu_pct is not None:
            if cpu_pct > 90:
                alerts.append({"metric": "cpu", "value": cpu_pct, "level": "critical", "message": f"CPU at {cpu_pct}% — critical threshold exceeded"})
            elif cpu_pct > 75:
                alerts.append({"metric": "cpu", "value": cpu_pct, "level": "warning", "message": f"CPU at {cpu_pct}% — approaching limit"})

        mem_pct = metrics.get("memory", {}).get("percent")
        if mem_pct is not None:
            if mem_pct > 90:
                alerts.append({"metric": "memory", "value": mem_pct, "level": "critical", "message": f"RAM at {mem_pct}% — critical threshold exceeded"})
            elif mem_pct > 75:
                alerts.append({"metric": "memory", "value": mem_pct, "level": "warning", "message": f"RAM at {mem_pct}% — approaching limit"})

        disk_pct = metrics.get("disk", {}).get("percent")
        if disk_pct is not None:
            if disk_pct > 95:
                alerts.append({"metric": "disk", "value": disk_pct, "level": "critical", "message": f"Disk at {disk_pct}% — critical threshold exceeded"})
            elif disk_pct > 85:
                alerts.append({"metric": "disk", "value": disk_pct, "level": "warning", "message": f"Disk at {disk_pct}% — approaching limit"})

        gpu_devices = metrics.get("gpu", {}).get("devices", [])
        for dev in gpu_devices:
            temp = dev.get("temperature_c")
            if temp is not None and temp > 85:
                alerts.append({"metric": f"gpu_temp_{dev['name']}", "value": temp, "level": "critical", "message": f"GPU {dev['name']} at {temp}C — overheating"})

        return alerts

    # ------------------------------------------------------------------
    # 5. chunk_work
    # ------------------------------------------------------------------
    def chunk_work(self, items: list, chunk_size: int = None) -> _RESPONSE:
        """Split large work into chunks for parallel processing.
        Auto-calculate optimal chunk size."""
        if not items:
            return _ok({"chunks": [], "total_items": 0, "chunk_count": 0}, "No items to chunk")

        total = len(items)

        if chunk_size is None:
            chunk_size = self._calculate_chunk_size(total)

        if chunk_size <= 0:
            chunk_size = 1

        chunks = []
        for i in range(0, total, chunk_size):
            chunk = items[i:i + chunk_size]
            chunks.append({
                "index": len(chunks),
                "start": i,
                "end": min(i + chunk_size, total),
                "size": len(chunk),
                "items": chunk,
            })

        return _ok({
            "chunks": chunks,
            "total_items": total,
            "chunk_count": len(chunks),
            "chunk_size": chunk_size,
            "estimated_parallelism": min(len(chunks), self._cpu_count),
        }, f"Split {total} items into {len(chunks)} chunks of size {chunk_size}")

    def _calculate_chunk_size(self, total: int) -> int:
        if total <= 0:
            return 1
        workers = max(1, self._cpu_count)
        base = math.ceil(total / workers)
        min_chunk = self._config.get("min_chunk_size", 1)
        max_chunk = self._config.get("max_chunk_size", 10000)
        return max(min_chunk, min(base, max_chunk))

    # ------------------------------------------------------------------
    # 6. schedule_periodic
    # ------------------------------------------------------------------
    def schedule_periodic(self, interval: int, func, *args, **kwargs) -> _RESPONSE:
        """Schedule a function to run periodically in a background thread.
        Return scheduler ID."""
        if not callable(func):
            return _err("Provided function is not callable")
        if interval <= 0:
            return _err("Interval must be positive")

        try:
            scheduler_id = str(uuid.uuid4())
            stop_event = threading.Event()
            self._scheduler_flags[scheduler_id] = stop_event

            def _runner():
                while not stop_event.is_set():
                    try:
                        func(*args, **kwargs)
                    except Exception as exc:
                        with self._lock:
                            self._task_timings["scheduler_errors"].append({
                                "scheduler_id": scheduler_id,
                                "error": str(exc),
                                "time": datetime.now().isoformat(),
                            })
                    stop_event.wait(interval)

            thread = threading.Thread(target=_runner, daemon=True, name=f"scheduler-{scheduler_id[:8]}")
            thread.start()
            self._schedulers[scheduler_id] = thread

            return _ok({
                "scheduler_id": scheduler_id,
                "interval_seconds": interval,
                "function": func.__name__ if hasattr(func, "__name__") else "anonymous",
                "started_at": datetime.now().isoformat(),
                "active_schedulers": len(self._schedulers),
            }, f"Scheduler '{scheduler_id[:8]}' started every {interval}s for {func.__name__ if hasattr(func, '__name__') else 'anonymous'}")
        except Exception as exc:
            return _err(f"Failed to schedule periodic task: {exc}")

    # ------------------------------------------------------------------
    # 7. cancel_scheduler
    # ------------------------------------------------------------------
    def cancel_scheduler(self, scheduler_id: str) -> _RESPONSE:
        """Cancel a running scheduler."""
        try:
            if scheduler_id not in self._schedulers:
                return _err(f"Scheduler '{scheduler_id}' not found")

            stop_event = self._scheduler_flags.get(scheduler_id)
            if stop_event:
                stop_event.set()

            thread = self._schedulers[scheduler_id]
            if thread.is_alive():
                thread.join(timeout=5)

            del self._schedulers[scheduler_id]
            if scheduler_id in self._scheduler_flags:
                del self._scheduler_flags[scheduler_id]

            return _ok({
                "scheduler_id": scheduler_id,
                "cancelled_at": datetime.now().isoformat(),
                "active_schedulers": len(self._schedulers),
            }, f"Scheduler '{scheduler_id[:8]}' cancelled")
        except Exception as exc:
            return _err(f"Failed to cancel scheduler: {exc}")

    def list_schedulers(self) -> _RESPONSE:
        """List all active schedulers."""
        try:
            active = []
            for sid, thread in self._schedulers.items():
                active.append({
                    "scheduler_id": sid,
                    "alive": thread.is_alive(),
                    "name": thread.name,
                })
            return _ok({
                "schedulers": active,
                "count": len(active),
            }, f"{len(active)} active scheduler(s)")
        except Exception as exc:
            return _err(f"Failed to list schedulers: {exc}")

    # ------------------------------------------------------------------
    # 8. resource_guard
    # ------------------------------------------------------------------
    def resource_guard(self, max_cpu_percent: float = 80.0, max_ram_percent: float = 80.0) -> _RESPONSE:
        """Monitor resources and throttle if limits exceeded.
        Auto-slow down operations when system is busy."""
        try:
            if not _HAS_PSUTIL:
                return _ok({
                    "throttled": False,
                    "cpu_percent": None,
                    "ram_percent": None,
                    "reason": "psutil not available — resource guard disabled",
                    "throttle_factor": 1.0,
                }, "Resource guard skipped (psutil unavailable)")

            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory().percent
            disk = psutil.disk_usage(os.path.abspath(os.sep)).percent

            violations = []
            throttled = False
            factor = 1.0

            if cpu > max_cpu_percent:
                violations.append(f"CPU {cpu}% > {max_cpu_percent}%")
                throttled = True

            if mem > max_ram_percent:
                violations.append(f"RAM {mem}% > {max_ram_percent}%")
                throttled = True

            if disk > 95:
                violations.append(f"Disk {disk}% > 95%")
                throttled = True

            if throttled:
                excess_ratio = max(
                    cpu / max_cpu_percent if cpu > max_cpu_percent else 1.0,
                    mem / max_ram_percent if mem > max_ram_percent else 1.0,
                )
                factor = max(0.1, 1.0 / (excess_ratio * 1.5))
                if cpu > 95 or mem > 95:
                    factor = min(factor, 0.25)

            self._throttle_active = throttled
            self._throttle_factor = factor

            guard_result = {
                "throttled": throttled,
                "cpu_percent": cpu,
                "ram_percent": mem,
                "disk_percent": disk,
                "max_cpu_percent": max_cpu_percent,
                "max_ram_percent": max_ram_percent,
                "violations": violations,
                "throttle_factor": round(factor, 4),
                "recommended_delay_ms": round((1.0 / factor - 1.0) * 1000, 2) if factor < 1.0 else 0,
            }

            if throttled:
                return _ok(guard_result, f"THROTTLED: {', '.join(violations)} (factor={factor:.2f})")
            return _ok(guard_result, "Resources within limits")
        except Exception as exc:
            return _err(f"Resource guard failed: {exc}")

    def wait_if_busy(self, max_cpu_percent: float = 80.0, max_ram_percent: float = 80.0) -> None:
        """Blocking call — waits until resources are below thresholds."""
        if not _HAS_PSUTIL:
            return
        try:
            while True:
                cpu = psutil.cpu_percent(interval=0.1)
                mem = psutil.virtual_memory().percent
                if cpu <= max_cpu_percent and mem <= max_ram_percent:
                    return
                time.sleep(1)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 9. load_balance
    # ------------------------------------------------------------------
    def load_balance(self, tasks: list, workers: list = None) -> _RESPONSE:
        """Distribute tasks across available workers.
        Implement round-robin or least-loaded balancing."""
        if not tasks:
            return _ok({"assignments": {}, "unassigned": [], "strategy": self._balance_strategy}, "No tasks to balance")

        try:
            if workers is None:
                workers = [f"worker-{i}" for i in range(self._cpu_count)]

            if not workers:
                return _err("No workers available for load balancing")

            worker_count = len(workers)
            strategy = self._balance_strategy
            assignments = {w: [] for w in workers}
            worker_metrics = {}

            if strategy == "least_loaded":
                for w in workers:
                    load = self._worker_loads.get(w, 0)
                    worker_metrics[w] = {"current_load": load, "tasks_assigned": 0}

                for task in tasks:
                    worker = min(worker_metrics, key=lambda w: worker_metrics[w]["current_load"] + worker_metrics[w]["tasks_assigned"])
                    assignments[worker].append(task)
                    worker_metrics[worker]["tasks_assigned"] += 1
                    self._worker_loads[worker] += 1

            elif strategy == "weighted":
                weights = {}
                for w in workers:
                    weight_key = f"{w}_weight"
                    weights[w] = self._config.get(weight_key, 1.0)
                total_weight = sum(weights.values()) or 1.0
                capacity = {w: int(len(tasks) * (weights[w] / total_weight)) for w in workers}
                idx = 0
                for task in tasks:
                    sorted_workers = sorted(workers, key=lambda w: (len(assignments[w]), -weights[w]))
                    for w in sorted_workers:
                        if len(assignments[w]) < capacity.get(w, 0) or idx >= sum(capacity.values()):
                            assignments[w].append(task)
                            break
                    idx += 1

            else:
                for i, task in enumerate(tasks):
                    worker = workers[i % worker_count]
                    assignments[worker].append(task)

            distribution = {}
            for w, assigned in assignments.items():
                distribution[w] = {
                    "task_count": len(assigned),
                    "tasks": assigned,
                    "load_percent": round(len(assigned) / max(len(tasks), 1) * 100, 1),
                }

            return _ok({
                "assignments": distribution,
                "strategy": strategy,
                "total_tasks": len(tasks),
                "worker_count": worker_count,
                "balance_quality": self._compute_balance_quality(distribution),
            }, f"Balanced {len(tasks)} tasks across {worker_count} workers using '{strategy}' strategy")
        except Exception as exc:
            return _err(f"Load balancing failed: {exc}")

    def _compute_balance_quality(self, distribution: dict) -> dict:
        counts = [d["task_count"] for d in distribution.values()]
        if not counts:
            return {"perfect": True, "imbalance_ratio": 1.0}
        mn = min(counts)
        mx = max(counts)
        ratio = mn / max(mx, 1)
        return {
            "perfect": ratio >= 0.9,
            "imbalance_ratio": round(ratio, 4),
            "min_tasks": mn,
            "max_tasks": mx,
            "std_dev": round(self._std(counts), 2),
        }

    def _std(self, values: list) -> float:
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return math.sqrt(variance)

    def set_balance_strategy(self, strategy: str) -> _RESPONSE:
        """Change the load balancing strategy."""
        if strategy not in ("round_robin", "least_loaded", "weighted"):
            return _err(f"Unknown strategy '{strategy}'. Use: round_robin, least_loaded, weighted")
        self._balance_strategy = strategy
        return _ok({"strategy": strategy}, f"Balance strategy set to '{strategy}'")

    # ------------------------------------------------------------------
    # 10. auto_shard
    # ------------------------------------------------------------------
    def auto_shard(self, data: list, shard_count: int = None) -> _RESPONSE:
        """Shard large datasets for distributed processing.
        Return sharded data."""
        if not data:
            return _ok({"shards": [], "total_items": 0, "shard_count": 0}, "No data to shard")

        try:
            total = len(data)

            if shard_count is None:
                shard_count = min(self._cpu_count * 2, total)
            shard_count = max(1, min(shard_count, total))

            shard_size = math.ceil(total / shard_count)
            shards = []

            for i in range(shard_count):
                start = i * shard_size
                end = min(start + shard_size, total)
                chunk = data[start:end]
                shard_id = str(uuid.uuid4())
                shard_info = {
                    "shard_id": shard_id,
                    "index": i,
                    "start": start,
                    "end": end,
                    "size": len(chunk),
                    "data": chunk,
                }
                shards.append(shard_info)
                self._shard_registry[shard_id] = {
                    "created_at": datetime.now().isoformat(),
                    "size": len(chunk),
                    "index": i,
                }

            return _ok({
                "shards": shards,
                "total_items": total,
                "shard_count": len(shards),
                "shard_size": shard_size,
                "registry_entries": len(self._shard_registry),
                "recommended_parallelism": len(shards),
            }, f"Sharded {total} items into {len(shards)} shards of ~{shard_size} items each")
        except Exception as exc:
            return _err(f"Auto-shard failed: {exc}")

    def collect_shards(self, shard_ids: list = None) -> _RESPONSE:
        """Reassemble sharded data from registry by shard_ids.
        If no ids given, returns all shard metadata."""
        try:
            if shard_ids:
                found = []
                missing = []
                for sid in shard_ids:
                    if sid in self._shard_registry:
                        found.append(self._shard_registry[sid])
                    else:
                        missing.append(sid)
                return _ok({
                    "shards": found,
                    "found": len(found),
                    "missing": missing,
                }, f"Collected {len(found)} shards, {len(missing)} missing")
            return _ok({
                "shards": list(self._shard_registry.values()),
                "count": len(self._shard_registry),
            }, f"Registry has {len(self._shard_registry)} shard(s)")
        except Exception as exc:
            return _err(f"Shard collection failed: {exc}")

    def clear_shard_registry(self) -> _RESPONSE:
        """Clear all shard metadata from registry."""
        try:
            count = len(self._shard_registry)
            self._shard_registry.clear()
            return _ok({"cleared": count}, f"Cleared {count} shard(s) from registry")
        except Exception as exc:
            return _err(f"Failed to clear shard registry: {exc}")

    # ------------------------------------------------------------------
    # 11. performance_report
    # ------------------------------------------------------------------
    def performance_report(self) -> _RESPONSE:
        """Generate comprehensive performance report.
        Include: resource usage, task completion times, bottlenecks."""
        try:
            report = {
                "summary": self._build_summary(),
                "resources": self._build_resource_section(),
                "tasks": self._build_task_section(),
                "schedulers": self._build_scheduler_section(),
                "bottlenecks": self._identify_bottlenecks(),
                "recommendations": self._generate_recommendations(),
                "generated_at": datetime.now().isoformat(),
                "uptime_seconds": int(time.time() - self._start_time),
            }
            return _ok(report, "Performance report generated")
        except Exception as exc:
            return _err(f"Failed to generate performance report: {exc}")

    def _build_summary(self) -> dict:
        total_tasks = sum(self._task_counter.values())
        all_timings = []
        for timings in self._task_timings.values():
            if isinstance(timings, list):
                for t in timings:
                    if isinstance(t, (int, float)):
                        all_timings.append(t)
        avg_time = sum(all_timings) / len(all_timings) if all_timings else 0
        return {
            "total_tasks_executed": total_tasks,
            "total_api_calls": total_tasks,
            "average_task_time_seconds": round(avg_time, 4),
            "active_schedulers": len(self._schedulers),
            "throttle_active": self._throttle_active,
            "throttle_factor": self._throttle_factor,
            "resource_log_entries": len(self._resource_log),
            "performance_history_entries": len(self._performance_history),
            "cpu_cores": self._cpu_count,
            "psutil_available": _HAS_PSUTIL,
        }

    def _build_resource_section(self) -> dict:
        current = self._collect_performance_metrics()
        history = self._performance_history[-50:] if self._performance_history else []
        cpu_avg = None
        mem_avg = None
        if history:
            cpu_vals = [h.get("cpu", {}).get("percent") for h in history if h.get("cpu", {}).get("percent") is not None]
            mem_vals = [h.get("memory", {}).get("percent") for h in history if h.get("memory", {}).get("percent") is not None]
            cpu_avg = round(sum(cpu_vals) / len(cpu_vals), 1) if cpu_vals else None
            mem_avg = round(sum(mem_vals) / len(mem_vals), 1) if mem_vals else None
        return {
            "current": current,
            "averages": {
                "cpu_percent": cpu_avg,
                "ram_percent": mem_avg,
                "sample_count": len(history),
            },
            "peak": self._compute_peaks(history),
        }

    def _compute_peaks(self, history: list) -> dict:
        if not history:
            return {}
        cpu_peak = max((h.get("cpu", {}).get("percent") for h in history if h.get("cpu", {}).get("percent") is not None), default=None)
        mem_peak = max((h.get("memory", {}).get("percent") for h in history if h.get("memory", {}).get("percent") is not None), default=None)
        disk_peak = max((h.get("disk", {}).get("percent") for h in history if h.get("disk", {}).get("percent") is not None), default=None)
        return {
            "cpu_peak": cpu_peak,
            "ram_peak": mem_peak,
            "disk_peak": disk_peak,
        }

    def _build_task_section(self) -> dict:
        section = {
            "counts": dict(self._task_counter),
            "timings": {},
            "slowest_tasks": [],
        }
        for key, timings in self._task_timings.items():
            if isinstance(timings, list) and all(isinstance(t, (int, float)) for t in timings):
                if timings:
                    section["timings"][key] = {
                        "count": len(timings),
                        "min": round(min(timings), 4),
                        "max": round(max(timings), 4),
                        "avg": round(sum(timings) / len(timings), 4),
                        "total": round(sum(timings), 4),
                    }
        sorted_timings = sorted(
            [(k, v["avg"]) for k, v in section["timings"].items()],
            key=lambda x: x[1], reverse=True,
        )
        section["slowest_tasks"] = [
            {"task_type": k, "avg_seconds": v} for k, v in sorted_timings[:5]
        ]
        return section

    def _build_scheduler_section(self) -> dict:
        schedulers = []
        for sid, thread in self._schedulers.items():
            schedulers.append({
                "scheduler_id": sid[:8],
                "alive": thread.is_alive(),
                "name": thread.name,
            })
        return {
            "active_count": len(schedulers),
            "schedulers": schedulers,
        }

    def _identify_bottlenecks(self) -> list:
        bottlenecks = []
        if self._performance_history:
            recent = self._performance_history[-10:]
            cpu_vals = [h.get("cpu", {}).get("percent") for h in recent if h.get("cpu", {}).get("percent") is not None]
            mem_vals = [h.get("memory", {}).get("percent") for h in recent if h.get("memory", {}).get("percent") is not None]
            if cpu_vals and sum(cpu_vals) / len(cpu_vals) > 80:
                bottlenecks.append({
                    "type": "cpu",
                    "severity": "high",
                    "detail": f"Average CPU {sum(cpu_vals)/len(cpu_vals):.1f}% over last {len(recent)} samples",
                })
            if mem_vals and sum(mem_vals) / len(mem_vals) > 80:
                bottlenecks.append({
                    "type": "memory",
                    "severity": "high",
                    "detail": f"Average RAM {sum(mem_vals)/len(mem_vals):.1f}% over last {len(recent)} samples",
                })

        if self._task_counter.get("parallel_execute", 0) > 100:
            bottlenecks.append({
                "type": "parallelism",
                "severity": "medium",
                "detail": f"High parallel execution volume ({self._task_counter['parallel_execute']} calls) — consider distributed workers",
            })

        for key, timings in self._task_timings.items():
            if isinstance(timings, list) and all(isinstance(t, (int, float)) for t in timings) and len(timings) > 0:
                avg = sum(timings) / len(timings)
                if avg > 10:
                    bottlenecks.append({
                        "type": "slow_task",
                        "severity": "medium",
                        "detail": f"Task '{key}' averages {avg:.1f}s — consider optimization",
                    })
        return bottlenecks

    def _generate_recommendations(self) -> list:
        recs = []
        if _HAS_PSUTIL:
            try:
                mem = psutil.virtual_memory()
                if mem.percent > 80:
                    recs.append({
                        "area": "memory",
                        "priority": "high",
                        "action": "Increase RAM or reduce memory load",
                    })
                cpu = psutil.cpu_percent(interval=0.1)
                if cpu > 80:
                    recs.append({
                        "area": "cpu",
                        "priority": "high",
                        "action": "Reduce worker count or upgrade CPU",
                    })
            except Exception:
                pass

        if not _HAS_PSUTIL:
            recs.append({
                "area": "monitoring",
                "priority": "low",
                "action": "Install psutil for detailed resource monitoring: pip install psutil",
            })

        if not _HAS_GPUTIL:
            recs.append({
                "area": "gpu",
                "priority": "low",
                "action": "Install GPUtil for GPU monitoring: pip install gputil",
            })

        if self._throttle_active:
            recs.append({
                "area": "throttling",
                "priority": "medium",
                "action": f"Throttle active (factor={self._throttle_factor}) — consider reducing concurrent operations",
            })

        if len(self._schedulers) > 10:
            recs.append({
                "area": "schedulers",
                "priority": "low",
                "action": f"{len(self._schedulers)} active schedulers — consider consolidating periodic tasks",
            })

        recs.append({
            "area": "general",
            "priority": "info",
            "action": "Configure balance_strategy in config to match workload pattern",
        })
        return recs

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------
    def get_status(self) -> _RESPONSE:
        """Get overall system status summary."""
        try:
            status_data = {
                "uptime_seconds": int(time.time() - self._start_time),
                "cpu_cores": self._cpu_count,
                "active_schedulers": len(self._schedulers),
                "tasks_executed": sum(self._task_counter.values()),
                "performance_snapshots": len(self._performance_history),
                "resource_logs": len(self._resource_log),
                "throttle_active": self._throttle_active,
                "throttle_factor": self._throttle_factor,
                "balance_strategy": self._balance_strategy,
                "registered_shards": len(self._shard_registry),
                "active_worker_count": len(self._active_workers),
                "psutil_available": _HAS_PSUTIL,
                "gputil_available": _HAS_GPUTIL,
            }
            if _HAS_PSUTIL:
                try:
                    status_data["cpu_current"] = psutil.cpu_percent(interval=0.1)
                    status_data["ram_current"] = psutil.virtual_memory().percent
                except Exception:
                    pass
            return _ok(status_data, "System status retrieved")
        except Exception as exc:
            return _err(f"Failed to get status: {exc}")

    def reset_statistics(self) -> _RESPONSE:
        """Reset all collected statistics and history."""
        try:
            with self._lock:
                self._performance_history.clear()
                self._resource_log.clear()
                self._task_timings.clear()
                self._task_counter.clear()
                self._start_time = time.time()
            return _ok({}, "Statistics reset successfully")
        except Exception as exc:
            return _err(f"Failed to reset statistics: {exc}")

    def get_task_history(self, task_type: str = None) -> _RESPONSE:
        """Get timing history for specific task type or all tasks."""
        try:
            if task_type:
                timings = self._task_timings.get(task_type, [])
                return _ok({
                    "task_type": task_type,
                    "count": len(timings),
                    "timings": timings[-100:],
                }, f"Found {len(timings)} timing(s) for '{task_type}'")
            summary = {}
            for k, v in self._task_timings.items():
                summary[k] = {
                    "count": len(v),
                    "recent": v[-10:] if isinstance(v, list) else [],
                }
            return _ok({
                "task_types": summary,
                "total_types": len(summary),
            }, f"History available for {len(summary)} task type(s)")
        except Exception as exc:
            return _err(f"Failed to get task history: {exc}")

    def emergency_throttle(self, factor: float = 0.1) -> _RESPONSE:
        """Manually force throttling to a specific factor (0.01 to 1.0)."""
        try:
            factor = max(0.01, min(1.0, factor))
            self._throttle_active = True
            self._throttle_factor = factor
            return _ok({
                "throttle_factor": factor,
                "throttle_active": True,
            }, f"Emergency throttle set to factor {factor}")
        except Exception as exc:
            return _err(f"Emergency throttle failed: {exc}")

    def release_throttle(self) -> _RESPONSE:
        """Manually release any active throttle."""
        try:
            self._throttle_active = False
            self._throttle_factor = 1.0
            return _ok({}, "Throttle released")
        except Exception as exc:
            return _err(f"Failed to release throttle: {exc}")

    def export_metrics(self, format: str = "json") -> _RESPONSE:
        """Export collected metrics as JSON or dict."""
        try:
            data = {
                "generated_at": datetime.now().isoformat(),
                "uptime_seconds": int(time.time() - self._start_time),
                "task_counts": dict(self._task_counter),
                "performance_history": self._performance_history[-100:],
                "resource_log": self._resource_log[-100:],
            }
            if format == "json":
                return _ok(json.dumps(data, default=str, indent=2), "Metrics exported as JSON string")
            return _ok(data, "Metrics exported as dictionary")
        except Exception as exc:
            return _err(f"Failed to export metrics: {exc}")

    def simulate_load(self, task_count: int = 10, task_duration: float = 0.1) -> _RESPONSE:
        """Generate synthetic tasks for testing the auto-scaler."""
        try:
            def _synthetic_task(duration: float, idx: int):
                time.sleep(duration)
                return {"task_id": idx, "slept": duration}

            tasks = []
            cpu_tasks_count = task_count // 2
            io_tasks_count = task_count - cpu_tasks_count
            for i in range(cpu_tasks_count):
                tasks.append(_synthetic_task)
            for i in range(io_tasks_count):
                tasks.append([_synthetic_task, (task_duration * random.uniform(0.5, 2.0), i)])

            result = self.parallel_execute(tasks)
            return _ok({
                "simulated_tasks": task_count,
                "cpu_simulated": cpu_tasks_count,
                "io_simulated": io_tasks_count,
                "execution_result": result.get("result"),
            }, f"Simulated load with {task_count} tasks")
        except Exception as exc:
            return _err(f"Load simulation failed: {exc}")


auto_scaler = AutoScaler()
