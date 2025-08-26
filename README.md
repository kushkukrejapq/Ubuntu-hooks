# Ubuntu Log Directory Monitor

A Python script for **discovering** and **monitoring** log directories on Ubuntu systems using `inotify`. This tool identifies potential log directories and tracks file system events such as file creation, modification, deletion, and more, outputting events to the console or a JSON file.

## **Features**

- **Log Directory Discovery**: Automatically finds common log directories (e.g., `/var/log`, `/var/log/nginx`) and directories containing log-like files (based on extensions like `.log`, `.txt`, or names like "access", "error").
- **Real-Time Monitoring**: Uses `inotify` to monitor file system events (`CREATE`, `MODIFY`, `DELETE`, `MOVED_TO`, `MOVED_FROM`, `CLOSE_WRITE`) in specified or discovered directories.
- **Flexible Output**: Logs events to the console with optional verbose output and/or to a JSON file.
- **Command-Line Interface**: Supports options for discovery, monitoring, specific directories, output file, and verbosity.
- **Error Handling**: Gracefully handles permission errors, missing directories, and `inotify` resource cleanup.

## **Prerequisites**

- **Python 3.6+**: Ensure Python 3 is installed.
- **inotify-simple**: Required for file system event monitoring.

Install the dependency:
```bash
pip install inotify-simple
```
## **Installation**

1. Save the script as `log_monitor.py`.
2. (Optional) Make the script executable:
   ```bash
   chmod +x log_monitor.py
    ```

# Ubuntu Log Directory Monitor

A Python script for **discovering** and **monitoring** log directories on Ubuntu systems using `inotify`. This tool identifies potential log directories and tracks file system events such as file creation, modification, deletion, and more, outputting events to the console or a JSON file.

## **Features**

- **Log Directory Discovery**: Automatically finds common log directories (e.g., `/var/log`, `/var/log/nginx`) and directories containing log-like files (based on extensions like `.log`, `.txt`, or names like "access", "error").
- **Real-Time Monitoring**: Uses `inotify` to monitor file system events (`CREATE`, `MODIFY`, `DELETE`, `MOVED_TO`, `MOVED_FROM`, `CLOSE_WRITE`) in specified or discovered directories.
- **Flexible Output**: Logs events to the console with optional verbose output and/or to a JSON file.
- **Command-Line Interface**: Supports options for discovery, monitoring, specific directories, output file, and verbosity.
- **Error Handling**: Gracefully handles permission errors, missing directories, and `inotify` resource cleanup.

## **Prerequisites**

- **Python 3.6+**: Ensure Python 3 is installed.
- **inotify-simple**: Required for file system event monitoring.

Install the dependency:
```bash
pip install inotify-simple
```

## **Installation**

1. Save the script as `log_monitor.py`.  
2. (Optional) Make the script executable:
   ```bash
   chmod +x log_monitor.py
  ```
3. Ensure the required dependency is installed:
   ```bash
   pip install inotify-simple
  ```
4. Verify the installation of the dependency:
   ```bash
   pip show inotify-simple
  ```
5. Run the script using Python:
   ```bash
   python3 log_monitor.py [options]
  ```
6. (Optional) Use `sudo` if monitoring directories that require elevated permissions, such as `/var/log`:
   ```bash
   sudo python3 log_monitor.py --monitor --dirs /var/log
  ```

## **Stopping the Monitor** 

Press **Ctrl+C** to stop monitoring.  
The script will automatically clean up inotify resources to prevent resource leaks.

## **Output Format**

### Console Output (Non-Verbose)
```bash
2025-08-26T21:45:12.345678 - CREATE - /var/log/syslog
2025-08-26T21:45:13.123456 - MODIFY - /var/log/nginx/access.log
```


### Console Output (Verbose)
```json
LOG EVENT: {
  "timestamp": "2025-08-26T21:45:12.345678",
  "path": "/var/log",
  "filename": "syslog",
  "event_type": "CREATE",
  "size": 1024
}
```

### JSON Output File
Events are appended to the specified file (e.g., `events.json`):
```json
{
  "timestamp": "2025-08-26T21:45:12.345678",
  "path": "/var/log",
  "filename": "syslog",
  "event_type": "CREATE",
  "size": 1024
}
{
  "timestamp": "2025-08-26T21:45:13.123456",
  "path": "/var/log/nginx",
  "filename": "access.log",
  "event_type": "MODIFY",
  "size": 2048
}
```

---

## **Troubleshooting**

- **Permission Errors**  
  If you see "Permission denied" errors, try running with `sudo`:
  ```bash
  sudo ./log_monitor.py --monitor --dirs /var/log
  ```

- **Inotify Watch Limits**  
  If monitoring fails for many directories, check the inotify watch limit:
  ```bash
  cat /proc/sys/fs/inotify/max_user_watches
  ```
  Increase it if needed:
  ```bash
  sudo sysctl -w fs.inotify.max_user_watches=524288
  ```
- **Missing inotify-simple**  
  Verify installation:
  ```bash
  pip show inotify-simple
  ```

- **Install if missing**  
  ```bash
  pip install inotify-simple
  ```

- **No Events**
  Ensure the monitored directories exist and contain activity:
  ```bash
  echo "Test" >> /tmp/logs/test.log
  ```
---

## **Limitations**

- **Linux Only**: Uses inotify, which is Linux-specific.  
- **Permission Requirements**: Some directories (e.g., `/var/log/journal`) may require sudo.  
- **Inotify Limits**: System limits on inotify watches may restrict the number of monitored directories.  
- **No Log Rotation Handling**: Does not automatically handle log rotation (e.g., `access.log.1`).  

---

## **Future Improvements**

- Support for configuration files to specify directories and settings.  
- Event filtering by file extension or name.  
- Real-time statistics or dashboard for monitored events.  
- Handling of log rotation and renamed files.  
- Cross-platform support (e.g., macOS with fsevents, Windows with ReadDirectoryChangesW).  

---

## **Security Considerations**

- **Running as Root**: Use `sudo` cautiously, as monitoring sensitive directories may expose private data.  
- **Output File Permissions**: Ensure the output file (e.g., `events.json`) has restricted permissions (e.g., `0600`).  
- **Path Validation**: Avoid monitoring untrusted directories to prevent path traversal issues.  

