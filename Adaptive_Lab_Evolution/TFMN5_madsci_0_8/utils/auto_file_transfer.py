import os
import shutil
import time
import argparse
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from lab_mail import send_email

# written by claude.ai

class FolderMonitor(FileSystemEventHandler):
    def __init__(self, source_folder, destination_folder):
        self.source_folder = source_folder
        self.destination_folder = destination_folder
        self.last_transfer = time.time()
        self.email_sent = False
        self.email_monitor_minutes = 120 # 2 hours in minutes
        
        # Create destination folder if it doesn't exist
        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder)
            print(f"Created destination folder: {destination_folder}")
    
    def on_created(self, event):
        # Ignore directory creation events
        if event.is_directory:
            return
        
        # Get the file path
        source_file = event.src_path
        filename = os.path.basename(source_file)
        destination_file = os.path.join(self.destination_folder, filename)
        
        # Wait a moment to ensure file is fully written
        time.sleep(0.5)
        
        try:
            # Copy the file
            shutil.copy2(source_file, destination_file)
            print(f"Copied: {filename} -> {destination_file}")

            # Reset inactivity timer and email flag
            self.last_transfer = time.time()
            self.email_sent = False

        except Exception as e:
            print(f"Error copying {filename}: {str(e)}")



def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Monitor a folder and copy new files to another location.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Example:\n  python folder_monitor.py -s "C:\\WatchFolder" -d "C:\\BackupFolder"'
    )
    
    parser.add_argument('-s', '--source', required=True, help='Source folder to monitor')
    parser.add_argument('-d', '--destination', required=True, help='Destination folder for copied files')
    
    args = parser.parse_args()
    
    source_folder = args.source
    destination_folder = args.destination
    
    # Validate source folder exists
    if not os.path.exists(source_folder):
        print(f"Error: Source folder does not exist: {source_folder}")
        sys.exit(1)
    
    if not os.path.isdir(source_folder):
        print(f"Error: Source path is not a directory: {source_folder}")
        sys.exit(1)
    
    print(f"Monitoring folder: {source_folder}")
    print(f"Copying files to: {destination_folder}")
    print("Press Ctrl+C to stop monitoring...\n")
    
    # Create event handler and observer
    try: 
        event_handler = FolderMonitor(source_folder, destination_folder)
        observer = Observer()
        observer.schedule(event_handler, source_folder, recursive=False)
        
        # Start monitoring
        observer.start()
    except Exception as e: 
        # don't fail
        print(e)
    
    try:
        while True:
            time.sleep(1)

            # Send email if no files have been transferred for the specified time
            if time.time() - event_handler.last_transfer > event_handler.email_monitor_minutes * 60 and not event_handler.email_sent:
                try: 
                    send_email(f"WARNING!! No files have been automatically transferred for the specified time: {event_handler.email_monitor_minutes} minutes.")
                    event_handler.email_sent = True

                except Exception as e:
                    print(f"Failed to send email: {e}")
                    # don't fail, just print the error and continue monitoring
                        
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopped monitoring.")
    
    observer.join()

if __name__ == "__main__":
    main()