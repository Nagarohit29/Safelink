"""
Packet Buffer for Optimized Capture and Processing

Provides efficient packet buffering with batch processing capabilities,
overflow handling, and performance monitoring.
"""

import logging
import threading
import queue
import time
from typing import Callable, Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PacketBufferStats:
    """Statistics for packet buffer."""
    total_received: int = 0
    total_processed: int = 0
    total_dropped: int = 0
    total_batches: int = 0
    avg_batch_size: float = 0.0
    avg_processing_time: float = 0.0
    buffer_utilization: float = 0.0  # Percentage
    

class PacketBuffer:
    """
    Thread-safe packet buffer with batch processing.
    
    Features:
    - Configurable buffer size
    - Batch processing
    - Overflow handling (drop or block)
    - Performance statistics
    - Multiple consumer support
    """
    
    def __init__(
        self,
        max_size: int = 10000,
        batch_size: int = 32,
        batch_timeout: float = 0.1,
        overflow_strategy: str = "drop",  # "drop" or "block"
        enable_stats: bool = True
    ):
        """
        Initialize packet buffer.
        
        Args:
            max_size: Maximum buffer size
            batch_size: Number of packets per batch
            batch_timeout: Max seconds to wait for batch to fill
            overflow_strategy: How to handle buffer overflow ("drop" or "block")
            enable_stats: Whether to collect statistics
        """
        self.max_size = max_size
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.overflow_strategy = overflow_strategy
        self.enable_stats = enable_stats
        
        # Thread-safe queue
        if overflow_strategy == "drop":
            # Non-blocking queue, will raise Full exception
            self.queue = queue.Queue(maxsize=max_size)
        else:
            # Blocking queue, will wait when full
            self.queue = queue.Queue(maxsize=max_size)
        
        # Statistics
        self.stats = PacketBufferStats()
        self.stats_lock = threading.Lock()
        
        # Running flag
        self.running = False
        
        # Processing threads
        self.processor_thread: Optional[threading.Thread] = None
        
        logger.info(f"PacketBuffer initialized: max_size={max_size}, batch_size={batch_size}, "
                   f"strategy={overflow_strategy}")
    
    def put(self, packet, block: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Add packet to buffer.
        
        Args:
            packet: Packet object to buffer
            block: Whether to block if buffer is full
            timeout: Timeout for blocking put
            
        Returns:
            True if packet was added, False if dropped
        """
        try:
            if self.overflow_strategy == "drop" and self.queue.full():
                # Drop packet
                if self.enable_stats:
                    with self.stats_lock:
                        self.stats.total_dropped += 1
                logger.warning("Buffer full, packet dropped")
                return False
            
            # Add to queue
            self.queue.put(packet, block=block, timeout=timeout)
            
            if self.enable_stats:
                with self.stats_lock:
                    self.stats.total_received += 1
            
            return True
            
        except queue.Full:
            if self.enable_stats:
                with self.stats_lock:
                    self.stats.total_dropped += 1
            logger.warning("Buffer full, packet dropped")
            return False
    
    def get_batch(self, timeout: Optional[float] = None) -> List:
        """
        Get a batch of packets from buffer.
        
        Args:
            timeout: Max time to wait for packets
            
        Returns:
            List of packets (up to batch_size)
        """
        batch = []
        deadline = time.time() + (timeout or self.batch_timeout)
        
        try:
            while len(batch) < self.batch_size:
                remaining_time = deadline - time.time()
                
                if remaining_time <= 0:
                    break
                
                try:
                    packet = self.queue.get(timeout=remaining_time)
                    batch.append(packet)
                except queue.Empty:
                    break
            
            if batch and self.enable_stats:
                with self.stats_lock:
                    self.stats.total_processed += len(batch)
                    self.stats.total_batches += 1
                    
                    # Update average batch size
                    total_batches = self.stats.total_batches
                    avg = self.stats.avg_batch_size
                    self.stats.avg_batch_size = (
                        (avg * (total_batches - 1) + len(batch)) / total_batches
                    )
            
            return batch
            
        except Exception as e:
            logger.error(f"Error getting batch: {e}")
            return batch
    
    def start_processing(self, processor_func: Callable[[List], None], 
                        num_workers: int = 1):
        """
        Start background processing of buffered packets.
        
        Args:
            processor_func: Function to process packet batches
            num_workers: Number of worker threads
        """
        if self.running:
            logger.warning("Packet buffer already processing")
            return
        
        self.running = True
        
        def worker():
            """Background worker for processing packets."""
            while self.running:
                try:
                    batch = self.get_batch(timeout=self.batch_timeout)
                    
                    if not batch:
                        continue
                    
                    # Process batch
                    start_time = time.time()
                    processor_func(batch)
                    processing_time = time.time() - start_time
                    
                    # Update stats
                    if self.enable_stats:
                        with self.stats_lock:
                            total_batches = self.stats.total_batches
                            avg = self.stats.avg_processing_time
                            self.stats.avg_processing_time = (
                                (avg * (total_batches - 1) + processing_time) / total_batches
                            )
                    
                except Exception as e:
                    logger.error(f"Error in packet processor: {e}")
        
        # Start worker threads
        for i in range(num_workers):
            thread = threading.Thread(target=worker, daemon=True, name=f"PacketProcessor-{i}")
            thread.start()
            logger.info(f"Started packet processor worker {i}")
        
        logger.info(f"Packet buffer processing started with {num_workers} workers")
    
    def stop_processing(self):
        """Stop background processing."""
        if not self.running:
            return
        
        self.running = False
        logger.info("Packet buffer processing stopped")
    
    def size(self) -> int:
        """Get current buffer size."""
        return self.queue.qsize()
    
    def is_full(self) -> bool:
        """Check if buffer is full."""
        return self.queue.full()
    
    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        return self.queue.empty()
    
    def clear(self):
        """Clear all packets from buffer."""
        count = 0
        try:
            while True:
                self.queue.get_nowait()
                count += 1
        except queue.Empty:
            pass
        
        if count > 0:
            logger.info(f"Cleared {count} packets from buffer")
    
    def get_statistics(self) -> Dict:
        """
        Get buffer statistics.
        
        Returns:
            Statistics dictionary
        """
        if not self.enable_stats:
            return {}
        
        with self.stats_lock:
            # Calculate buffer utilization
            current_size = self.size()
            utilization = (current_size / self.max_size * 100) if self.max_size > 0 else 0
            
            self.stats.buffer_utilization = utilization
            
            return {
                "total_received": self.stats.total_received,
                "total_processed": self.stats.total_processed,
                "total_dropped": self.stats.total_dropped,
                "total_batches": self.stats.total_batches,
                "avg_batch_size": round(self.stats.avg_batch_size, 2),
                "avg_processing_time": round(self.stats.avg_processing_time, 4),
                "buffer_size": current_size,
                "buffer_max_size": self.max_size,
                "buffer_utilization": round(utilization, 2),
                "drop_rate": (
                    self.stats.total_dropped / max(self.stats.total_received, 1) * 100
                ) if self.stats.total_received > 0 else 0,
                "is_running": self.running
            }
    
    def reset_statistics(self):
        """Reset all statistics."""
        if self.enable_stats:
            with self.stats_lock:
                self.stats = PacketBufferStats()
            logger.info("Buffer statistics reset")
    
    def __repr__(self) -> str:
        stats = self.get_statistics()
        return (f"PacketBuffer(size={stats.get('buffer_size', 0)}/{self.max_size}, "
                f"received={stats.get('total_received', 0)}, "
                f"processed={stats.get('total_processed', 0)}, "
                f"dropped={stats.get('total_dropped', 0)})")


# Global instance
_packet_buffer = None


def get_packet_buffer(**kwargs) -> PacketBuffer:
    """
    Get singleton packet buffer instance.
    
    Args:
        **kwargs: Configuration parameters (only used on first call)
        
    Returns:
        PacketBuffer instance
    """
    global _packet_buffer
    if _packet_buffer is None:
        _packet_buffer = PacketBuffer(**kwargs)
    return _packet_buffer
