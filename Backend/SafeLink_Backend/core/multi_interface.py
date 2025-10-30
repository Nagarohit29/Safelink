"""
Multi-Interface Packet Capture and Load Balancing

Provides architecture for capturing packets from multiple network interfaces
simultaneously with load balancing across worker threads.
"""

import logging
import threading
import queue
import time
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from scapy.all import AsyncSniffer, conf as scapy_conf

logger = logging.getLogger(__name__)


@dataclass
class InterfaceStats:
    """Statistics for a network interface."""
    interface_name: str
    packets_captured: int = 0
    packets_processed: int = 0
    packets_dropped: int = 0
    bytes_captured: int = 0
    errors: int = 0
    start_time: float = field(default_factory=time.time)
    last_packet_time: float = 0.0
    worker_id: Optional[int] = None
    is_active: bool = True
    
    @property
    def uptime(self) -> float:
        """Get interface uptime in seconds."""
        return time.time() - self.start_time
    
    @property
    def packet_rate(self) -> float:
        """Get packets per second rate."""
        uptime = self.uptime
        return self.packets_captured / uptime if uptime > 0 else 0.0


@dataclass
class WorkerStats:
    """Statistics for a worker thread."""
    worker_id: int
    packets_processed: int = 0
    processing_time: float = 0.0
    errors: int = 0
    interfaces: List[str] = field(default_factory=list)
    is_active: bool = True
    
    @property
    def avg_processing_time(self) -> float:
        """Get average processing time per packet."""
        return (self.processing_time / self.packets_processed 
                if self.packets_processed > 0 else 0.0)
    
    @property
    def load(self) -> float:
        """Get worker load (packets processed)."""
        return float(self.packets_processed)


class InterfaceManager:
    """
    Manages multiple network interfaces for packet capture.
    
    Features:
    - Multi-interface capture
    - Per-interface statistics
    - Interface health monitoring
    - Dynamic interface add/remove
    """
    
    def __init__(self):
        """Initialize interface manager."""
        self.interfaces: Dict[str, InterfaceStats] = {}
        self.sniffers: Dict[str, AsyncSniffer] = {}
        self.lock = threading.Lock()
        
        logger.info("InterfaceManager initialized")
    
    def discover_interfaces(self) -> List[str]:
        """
        Discover available network interfaces.
        
        Returns:
            List of interface names
        """
        try:
            # Get interfaces from scapy
            ifaces = scapy_conf.ifaces
            interface_names = []
            
            for iface_name in ifaces:
                # Skip loopback and disabled interfaces
                if 'loopback' not in iface_name.lower():
                    interface_names.append(iface_name)
            
            logger.info(f"Discovered {len(interface_names)} interfaces: {interface_names}")
            return interface_names
            
        except Exception as e:
            logger.error(f"Error discovering interfaces: {e}")
            return []
    
    def add_interface(self, interface_name: str) -> bool:
        """
        Add an interface for monitoring.
        
        Args:
            interface_name: Name of network interface
            
        Returns:
            True if added successfully
        """
        with self.lock:
            if interface_name in self.interfaces:
                logger.warning(f"Interface {interface_name} already added")
                return False
            
            self.interfaces[interface_name] = InterfaceStats(
                interface_name=interface_name
            )
            logger.info(f"Added interface: {interface_name}")
            return True
    
    def remove_interface(self, interface_name: str) -> bool:
        """
        Remove an interface from monitoring.
        
        Args:
            interface_name: Name of network interface
            
        Returns:
            True if removed successfully
        """
        with self.lock:
            if interface_name not in self.interfaces:
                logger.warning(f"Interface {interface_name} not found")
                return False
            
            # Stop sniffer if running
            if interface_name in self.sniffers:
                try:
                    self.sniffers[interface_name].stop()
                    del self.sniffers[interface_name]
                except Exception as e:
                    logger.error(f"Error stopping sniffer for {interface_name}: {e}")
            
            del self.interfaces[interface_name]
            logger.info(f"Removed interface: {interface_name}")
            return True
    
    def update_stats(self, interface_name: str, 
                    packets: int = 0, bytes_count: int = 0, 
                    dropped: int = 0, errors: int = 0):
        """
        Update statistics for an interface.
        
        Args:
            interface_name: Interface to update
            packets: Number of packets captured
            bytes_count: Number of bytes captured
            dropped: Number of packets dropped
            errors: Number of errors
        """
        with self.lock:
            if interface_name in self.interfaces:
                stats = self.interfaces[interface_name]
                stats.packets_captured += packets
                stats.bytes_captured += bytes_count
                stats.packets_dropped += dropped
                stats.errors += errors
                if packets > 0:
                    stats.last_packet_time = time.time()
    
    def get_stats(self, interface_name: Optional[str] = None) -> Dict:
        """
        Get statistics for interface(s).
        
        Args:
            interface_name: Specific interface or None for all
            
        Returns:
            Statistics dictionary
        """
        with self.lock:
            if interface_name:
                if interface_name in self.interfaces:
                    stats = self.interfaces[interface_name]
                    return {
                        "interface": stats.interface_name,
                        "packets_captured": stats.packets_captured,
                        "packets_processed": stats.packets_processed,
                        "packets_dropped": stats.packets_dropped,
                        "bytes_captured": stats.bytes_captured,
                        "errors": stats.errors,
                        "packet_rate": round(stats.packet_rate, 2),
                        "uptime": round(stats.uptime, 2),
                        "is_active": stats.is_active,
                        "worker_id": stats.worker_id
                    }
                return {}
            
            # Return stats for all interfaces
            return {
                name: self.get_stats(name) 
                for name in self.interfaces.keys()
            }
    
    def get_active_interfaces(self) -> List[str]:
        """Get list of active interface names."""
        with self.lock:
            return [name for name, stats in self.interfaces.items() 
                    if stats.is_active]


class LoadBalancer:
    """
    Load balances packet processing across multiple worker threads.
    
    Strategies:
    - Round-robin: Distribute packets evenly
    - Least-loaded: Send to worker with fewest packets
    - Affinity: Keep interface-worker pairing
    """
    
    def __init__(self, num_workers: int = 4, strategy: str = "least-loaded"):
        """
        Initialize load balancer.
        
        Args:
            num_workers: Number of worker threads
            strategy: Load balancing strategy ("round-robin", "least-loaded", "affinity")
        """
        self.num_workers = num_workers
        self.strategy = strategy
        
        # Worker queues
        self.worker_queues: List[queue.Queue] = [
            queue.Queue(maxsize=1000) for _ in range(num_workers)
        ]
        
        # Worker statistics
        self.worker_stats: List[WorkerStats] = [
            WorkerStats(worker_id=i) for i in range(num_workers)
        ]
        
        # Worker threads
        self.workers: List[threading.Thread] = []
        
        # Round-robin counter
        self.rr_counter = 0
        
        # Interface affinity mapping
        self.interface_affinity: Dict[str, int] = {}
        
        # Running flag
        self.running = False
        
        # Lock for thread safety
        self.lock = threading.Lock()
        
        logger.info(f"LoadBalancer initialized: {num_workers} workers, strategy={strategy}")
    
    def _get_least_loaded_worker(self) -> int:
        """Get ID of least loaded worker."""
        with self.lock:
            min_load = float('inf')
            worker_id = 0
            
            for i, stats in enumerate(self.worker_stats):
                if stats.is_active and stats.load < min_load:
                    min_load = stats.load
                    worker_id = i
            
            return worker_id
    
    def _get_round_robin_worker(self) -> int:
        """Get next worker in round-robin order."""
        with self.lock:
            worker_id = self.rr_counter % self.num_workers
            self.rr_counter += 1
            return worker_id
    
    def _get_affinity_worker(self, interface_name: str) -> int:
        """Get worker with affinity to interface."""
        with self.lock:
            if interface_name not in self.interface_affinity:
                # Assign to least loaded worker
                worker_id = self._get_least_loaded_worker()
                self.interface_affinity[interface_name] = worker_id
                self.worker_stats[worker_id].interfaces.append(interface_name)
            
            return self.interface_affinity[interface_name]
    
    def assign_packet(self, packet, interface_name: str) -> bool:
        """
        Assign packet to a worker based on strategy.
        
        Args:
            packet: Packet to process
            interface_name: Source interface
            
        Returns:
            True if assigned successfully
        """
        # Select worker based on strategy
        if self.strategy == "round-robin":
            worker_id = self._get_round_robin_worker()
        elif self.strategy == "least-loaded":
            worker_id = self._get_least_loaded_worker()
        elif self.strategy == "affinity":
            worker_id = self._get_affinity_worker(interface_name)
        else:
            worker_id = 0
        
        # Add to worker queue
        try:
            self.worker_queues[worker_id].put_nowait((packet, interface_name))
            return True
        except queue.Full:
            logger.warning(f"Worker {worker_id} queue full, packet dropped")
            return False
    
    def start_workers(self, processor_func: Callable):
        """
        Start worker threads.
        
        Args:
            processor_func: Function to process packets (packet, interface_name) -> None
        """
        if self.running:
            logger.warning("Workers already running")
            return
        
        self.running = True
        
        def worker(worker_id: int):
            """Worker thread function."""
            logger.info(f"Worker {worker_id} started")
            stats = self.worker_stats[worker_id]
            
            while self.running:
                try:
                    # Get packet from queue (with timeout)
                    packet, interface_name = self.worker_queues[worker_id].get(timeout=1.0)
                    
                    # Process packet
                    start_time = time.time()
                    try:
                        processor_func(packet, interface_name)
                        stats.packets_processed += 1
                    except Exception as e:
                        logger.error(f"Worker {worker_id} processing error: {e}")
                        stats.errors += 1
                    finally:
                        processing_time = time.time() - start_time
                        stats.processing_time += processing_time
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Worker {worker_id} error: {e}")
                    stats.errors += 1
            
            logger.info(f"Worker {worker_id} stopped")
        
        # Start workers
        for i in range(self.num_workers):
            thread = threading.Thread(
                target=worker,
                args=(i,),
                daemon=True,
                name=f"PacketWorker-{i}"
            )
            thread.start()
            self.workers.append(thread)
        
        logger.info(f"Started {self.num_workers} worker threads")
    
    def stop_workers(self):
        """Stop all worker threads."""
        if not self.running:
            return
        
        self.running = False
        
        # Wait for workers to finish
        for thread in self.workers:
            thread.join(timeout=5.0)
        
        self.workers.clear()
        logger.info("All workers stopped")
    
    def get_statistics(self) -> Dict:
        """
        Get load balancer statistics.
        
        Returns:
            Statistics dictionary
        """
        with self.lock:
            worker_stats_list = []
            for stats in self.worker_stats:
                worker_stats_list.append({
                    "worker_id": stats.worker_id,
                    "packets_processed": stats.packets_processed,
                    "errors": stats.errors,
                    "avg_processing_time": round(stats.avg_processing_time * 1000, 3),  # ms
                    "load": stats.load,
                    "interfaces": stats.interfaces,
                    "is_active": stats.is_active,
                    "queue_size": self.worker_queues[stats.worker_id].qsize()
                })
            
            total_processed = sum(s.packets_processed for s in self.worker_stats)
            total_errors = sum(s.errors for s in self.worker_stats)
            
            return {
                "num_workers": self.num_workers,
                "strategy": self.strategy,
                "total_processed": total_processed,
                "total_errors": total_errors,
                "workers": worker_stats_list,
                "is_running": self.running
            }


class MultiInterfaceSniffer:
    """
    High-level interface for multi-interface packet capture with load balancing.
    
    Combines InterfaceManager and LoadBalancer for easy deployment.
    """
    
    def __init__(self, num_workers: int = 4, strategy: str = "least-loaded"):
        """
        Initialize multi-interface sniffer.
        
        Args:
            num_workers: Number of worker threads
            strategy: Load balancing strategy
        """
        self.interface_manager = InterfaceManager()
        self.load_balancer = LoadBalancer(num_workers=num_workers, strategy=strategy)
        self.packet_handler = None
        self.running = False
        
        logger.info("MultiInterfaceSniffer initialized")
    
    def start(self, interfaces: List[str], packet_handler: Callable, 
              filter_str: str = "arp"):
        """
        Start capturing on multiple interfaces.
        
        Args:
            interfaces: List of interface names to capture on
            packet_handler: Function to handle packets
            filter_str: BPF filter string
        """
        if self.running:
            logger.warning("Sniffer already running")
            return
        
        self.packet_handler = packet_handler
        self.running = True
        
        # Add interfaces
        for iface in interfaces:
            self.interface_manager.add_interface(iface)
        
        # Start workers
        def process_packet(pkt, interface_name):
            """Process packet with handler."""
            try:
                self.packet_handler(pkt, interface_name)
                # Update interface stats
                self.interface_manager.update_stats(interface_name, packets=0, 
                                                   processed=1)
            except Exception as e:
                logger.error(f"Error processing packet from {interface_name}: {e}")
                self.interface_manager.update_stats(interface_name, errors=1)
        
        self.load_balancer.start_workers(process_packet)
        
        # Start sniffers for each interface
        for iface in interfaces:
            def make_handler(iface_name):
                def handler(pkt):
                    # Assign to worker
                    self.load_balancer.assign_packet(pkt, iface_name)
                    # Update interface stats
                    self.interface_manager.update_stats(iface_name, packets=1)
                return handler
            
            try:
                sniffer = AsyncSniffer(
                    iface=iface,
                    filter=filter_str,
                    prn=make_handler(iface),
                    store=False
                )
                sniffer.start()
                self.interface_manager.sniffers[iface] = sniffer
                logger.info(f"Started sniffer on {iface}")
            except Exception as e:
                logger.error(f"Error starting sniffer on {iface}: {e}")
        
        logger.info(f"MultiInterfaceSniffer started on {len(interfaces)} interfaces")
    
    def stop(self):
        """Stop all sniffers and workers."""
        if not self.running:
            return
        
        self.running = False
        
        # Stop sniffers
        for iface, sniffer in self.interface_manager.sniffers.items():
            try:
                sniffer.stop()
                logger.info(f"Stopped sniffer on {iface}")
            except Exception as e:
                logger.error(f"Error stopping sniffer on {iface}: {e}")
        
        self.interface_manager.sniffers.clear()
        
        # Stop workers
        self.load_balancer.stop_workers()
        
        logger.info("MultiInterfaceSniffer stopped")
    
    def get_statistics(self) -> Dict:
        """
        Get comprehensive statistics.
        
        Returns:
            Statistics for interfaces and workers
        """
        return {
            "interfaces": self.interface_manager.get_stats(),
            "load_balancer": self.load_balancer.get_statistics(),
            "is_running": self.running
        }


# Global instance
_multi_sniffer = None


def get_multi_interface_sniffer(**kwargs) -> MultiInterfaceSniffer:
    """Get singleton multi-interface sniffer instance."""
    global _multi_sniffer
    if _multi_sniffer is None:
        _multi_sniffer = MultiInterfaceSniffer(**kwargs)
    return _multi_sniffer
