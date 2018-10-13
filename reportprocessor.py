#!/usr/bin/python3
import sys, os, time, shutil
from logutil import log
from localprocessor import LocalObserverThread, is_complete
from pathlib import Path
from threading import Thread
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

class GlobalObserverThread(Thread):
    def __init__(self, directory: str, config: dict):
        super().__init__()
        self.file_watchers = {}
        self.config = config
        self.directory = directory
        self.observer = None

    def run(self):
        self.observer = GlobalReportObserver(self, self.directory, self.config)
        try:
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            self.observer.stop()

        self.observer.join()
        for thread in self.file_watchers:
            thread.join()

class GlobalReportObserver:
    def __init__(self,
                 thread: GlobalObserverThread,
                 directory,
                 config):
        # Properties
        self.directory = directory
        self.config = config
        self.thread = thread

        # Make folder
        path = Path(directory)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            log('global: directory {} created'.format(path))
        
        # Make observer
        self.observer = Observer()
        self.observer.schedule(GlobalReportHandler(self.thread, self.directory, config),
            path=directory if directory else '.',
            recursive=True)
        self.observer.start()

    def join(self):
        self.observer.join()
    
    def stop(self):
        self.observer.stop()
        log('global: watchdog service for folder {} stopped'.format(self.directory))

class GlobalReportHandler(PatternMatchingEventHandler):
    # Property of PatternMatchingEventHandler which contains list of filter file regex
    patterns=['*.jpg', '*.png', '*.bmp', '*.json']

    def __init__(self, thread: GlobalObserverThread, directory, config):
        super().__init__()
        self.config = config
        self.thread = thread
        self.file_watchers = thread.file_watchers

    def on_created(self, event):
        filename = event.src_path.split('/')[-1]
        folder = event.src_path.replace(filename, '')
        log('global: {0} file {2} at {1}'.format(event.event_type, folder, filename))
        if folder not in self.file_watchers:
            self.file_watchers[folder] = LocalObserverThread(folder, self.file_watchers, self.config)
            self.file_watchers[folder].start()

def main():
    directory = 'report'
    log('global: watching on folder {}'.format(directory))
    observer_thread = GlobalObserverThread(directory, {})
    try:
        observer_thread.start()
    except (KeyboardInterrupt, SystemExit):
        observer_thread.observer.stop()
    observer_thread.join()

if __name__ == '__main__':
    main()