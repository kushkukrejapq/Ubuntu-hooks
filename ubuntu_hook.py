#!/usr/bin/env python3

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from typing import Set, Optional
from dataclasses import dataclass, asdict

try:
    import inotify_simple
except ImportError:
    print("Error: inotify_simple not installed. Install with: pip install inotify-simple")
    sys.exit(1)

@dataclass
class LogEvent:
    """Represents a log file system event"""
    timestamp: str
    path: str
    filename: str
    event_type: str
    size: Optional[int] = None
    
    def to_dict(self):
        return asdict(self)

class LogDirectoryDiscovery:
    """Discovers potential log directories on Ubuntu systems"""
    
    # Common log directories on Ubuntu/Linux systems
    STANDARD_LOG_DIRS = [
        '/var/log',
        '/var/log/apache2',
        '/var/log/nginx',
        '/var/log/mysql',
        '/var/log/postgresql',
        '/var/log/syslog',
        '/var/log/auth',
        '/var/log/kern',
        '/var/log/mail',
        '/var/log/cron',
        '/var/log/daemon',
        '/var/log/user',
        '/var/log/messages',
        '/var/log/docker',
        '/var/log/pods',
        '/var/log/containers',
        '/opt/*/logs',
        '/usr/local/*/logs',
        '/tmp/logs',
        '/home/*/logs',
        '~/.local/share/logs',
        '/var/log/journal',
    ]
    
    # Application-specific log directories
    APP_LOG_PATTERNS = [
        '/var/log/*/logs',
        '/opt/*/log',
        '/usr/share/*/logs',
        '/etc/*/logs',
    ]
    
    # Common log file extensions
    LOG_EXTENSIONS = {'.log', '.txt', '.out', '.err', '.access', '.error', '.debug', '.info'}
    
    @classmethod
    def discover_log_directories(cls, include_user_dirs=True) -> Set[str]:
        """Discover existing log directories on the system"""
        log_dirs = set()
        
        # Check standard directories
        for log_dir in cls.STANDARD_LOG_DIRS:
            expanded_path = os.path.expanduser(log_dir)
            if '*' in expanded_path:
                # Handle wildcards
                parent_dir = expanded_path.split('*')[0].rstrip('/')
                if os.path.exists(parent_dir):
                    try:
                        for item in os.listdir(parent_dir):
                            full_path = os.path.join(parent_dir, item, 'logs')
                            if os.path.isdir(full_path):
                                log_dirs.add(full_path)
                    except PermissionError:
                        continue
            elif os.path.isdir(expanded_path):
                log_dirs.add(expanded_path)
        
        # Discover directories containing log files
        for log_dir in list(log_dirs):
            try:
                cls._discover_nested_log_dirs(log_dir, log_dirs, max_depth=2)
            except PermissionError:
                continue
        
        return log_dirs
    
    @classmethod
    def _discover_nested_log_dirs(cls, directory: str, found_dirs: Set[str], max_depth: int, current_depth: int = 0):
        """Recursively discover nested directories containing log files"""
        if current_depth >= max_depth:
            return
            
        try:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isdir(item_path):
                    # Check if directory contains log files
                    if cls._contains_log_files(item_path):
                        found_dirs.add(item_path)
                    # Recurse into subdirectory
                    cls._discover_nested_log_dirs(item_path, found_dirs, max_depth, current_depth + 1)
        except PermissionError:
            pass
    
    @classmethod
    def _contains_log_files(cls, directory: str) -> bool:
        """Check if directory contains files that look like logs"""
        try:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isfile(item_path):
                    # Check by extension
                    if any(item.endswith(ext) for ext in cls.LOG_EXTENSIONS):
                        return True
                    # Check by common log file names
                    if any(keyword in item.lower() for keyword in ['log', 'access', 'error', 'debug', 'audit']):
                        return True
            return False
        except PermissionError:
            return False

class LogDirectoryMonitor:
    """Monitors log directories using inotify for file system events"""
    
    def __init__(self, output_file: Optional[str] = None, verbose: bool = False):
        self.inotify = inotify_simple.INotify()
        self.watch_descriptors = {}  # wd -> directory path mapping
        self.monitored_dirs = set()
        self.output_file = output_file
        self.verbose = verbose
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Events we're interested in
        self.watch_flags = (
            inotify_simple.flags.CREATE |
            inotify_simple.flags.MODIFY |
            inotify_simple.flags.DELETE |
            inotify_simple.flags.MOVED_TO |
            inotify_simple.flags.MOVED_FROM |
            inotify_simple.flags.CLOSE_WRITE
        )
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('LogMonitor')
        logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def add_directory(self, directory: str) -> bool:
        """Add a directory to monitor"""
        try:
            if not os.path.isdir(directory):
                self.logger.warning(f"Directory does not exist: {directory}")
                return False
            
            if directory in self.monitored_dirs:
                self.logger.debug(f"Directory already monitored: {directory}")
                return True
            
            wd = self.inotify.add_watch(directory, self.watch_flags)
            self.watch_descriptors[wd] = directory
            self.monitored_dirs.add(directory)
            
            self.logger.info(f"Added watch for directory: {directory}")
            return True
            
        except PermissionError:
            self.logger.error(f"Permission denied accessing: {directory}")
            return False
        except Exception as e:
            self.logger.error(f"Error adding watch for {directory}: {e}")
            return False
    
    def remove_directory(self, directory: str) -> bool:
        """Remove a directory from monitoring"""
        try:
            # Find the watch descriptor for this directory
            wd_to_remove = None
            for wd, path in self.watch_descriptors.items():
                if path == directory:
                    wd_to_remove = wd
                    break
            
            if wd_to_remove is not None:
                self.inotify.rm_watch(wd_to_remove)
                del self.watch_descriptors[wd_to_remove]
                self.monitored_dirs.discard(directory)
                self.logger.info(f"Removed watch for directory: {directory}")
                return True
            else:
                self.logger.warning(f"Directory not currently monitored: {directory}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error removing watch for {directory}: {e}")
            return False
    
    def _get_file_size(self, filepath: str) -> Optional[int]:
        """Get file size safely"""
        try:
            return os.path.getsize(filepath)
        except (OSError, FileNotFoundError):
            return None
    
    def _process_event(self, event) -> Optional[LogEvent]:
        """Process an inotify event and create a LogEvent"""
        directory = self.watch_descriptors.get(event.wd)
        if not directory:
            return None
        
        full_path = os.path.join(directory, event.name)
        
        # Determine event type
        event_types = []
        if event.mask & inotify_simple.flags.CREATE:
            event_types.append('CREATE')
        if event.mask & inotify_simple.flags.MODIFY:
            event_types.append('MODIFY')
        if event.mask & inotify_simple.flags.DELETE:
            event_types.append('DELETE')
        if event.mask & inotify_simple.flags.MOVED_TO:
            event_types.append('MOVED_TO')
        if event.mask & inotify_simple.flags.MOVED_FROM:
            event_types.append('MOVED_FROM')
        if event.mask & inotify_simple.flags.CLOSE_WRITE:
            event_types.append('CLOSE_WRITE')
        
        event_type = '|'.join(event_types) if event_types else 'UNKNOWN'
        
        # Get file size if file exists
        file_size = self._get_file_size(full_path) if os.path.exists(full_path) else None
        
        log_event = LogEvent(
            timestamp=datetime.now().isoformat(),
            path=directory,
            filename=event.name,
            event_type=event_type,
            size=file_size
        )
        
        return log_event
    
    def _output_event(self, log_event: LogEvent):
        """Output event to console and/or file"""
        event_json = json.dumps(log_event.to_dict(), indent=2)
        
        # Console output
        if self.verbose:
            print(f"LOG EVENT: {event_json}")
        else:
            print(f"{log_event.timestamp} - {log_event.event_type} - {log_event.path}/{log_event.filename}")
        
        # File output
        if self.output_file:
            try:
                with open(self.output_file, 'a') as f:
                    f.write(event_json + '\n')
            except Exception as e:
                self.logger.error(f"Error writing to output file: {e}")
    
    def start_monitoring(self):
        """Start the monitoring loop"""
        if not self.monitored_dirs:
            self.logger.error("No directories to monitor!")
            return
        
        self.logger.info(f"Starting monitoring of {len(self.monitored_dirs)} directories...")
        self.logger.info(f"Monitored directories: {', '.join(sorted(self.monitored_dirs))}")
        
        try:
            while True:
                # Read events (this blocks until events are available)
                events = self.inotify.read()
                
                for event in events:
                    log_event = self._process_event(event)
                    if log_event:
                        self._output_event(log_event)
                        
        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Error during monitoring: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up inotify resources"""
        try:
            self.inotify.close()
            self.logger.info("Cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

def main():
    parser = argparse.ArgumentParser(description="Ubuntu Log Directory Monitor using inotify")
    parser.add_argument('--discover', action='store_true', 
                       help='Discover and list potential log directories')
    parser.add_argument('--monitor', action='store_true',
                       help='Start monitoring discovered log directories')
    parser.add_argument('--dirs', nargs='+', 
                       help='Specific directories to monitor (space-separated)')
    parser.add_argument('--output', type=str,
                       help='Output file for events (JSON format)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    parser.add_argument('--max-dirs', type=int, default=50,
                       help='Maximum number of directories to monitor (default: 50)')
    
    args = parser.parse_args()
    
    if args.discover or (not args.dirs and args.monitor):
        print("Discovering log directories...")
        discovered_dirs = LogDirectoryDiscovery.discover_log_directories()
        
        if args.discover:
            print(f"\nFound {len(discovered_dirs)} potential log directories:")
            for directory in sorted(discovered_dirs):
                print(f"  {directory}")
            if not args.monitor:
                return
        
        # Use discovered directories for monitoring
        monitor_dirs = list(discovered_dirs)[:args.max_dirs]
    else:
        monitor_dirs = args.dirs or []
    
    if args.monitor and monitor_dirs:
        monitor = LogDirectoryMonitor(output_file=args.output, verbose=args.verbose)
        
        # Add directories to monitor
        added_count = 0
        for directory in monitor_dirs:
            if monitor.add_directory(directory):
                added_count += 1
        
        if added_count > 0:
            print(f"Successfully added {added_count} directories for monitoring")
            monitor.start_monitoring()
        else:
            print("No directories could be added for monitoring")
    elif not args.discover:
        parser.print_help()

if __name__ == "__main__":
    main()