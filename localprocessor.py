#!/usr/bin/python3
import sys, os, time, shutil
from logutil import log
from pathlib import Path
from datetime import datetime
from threading import Thread
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import requests

class LocalObserverThread(Thread):
    def __init__(self, directory: str, file_watchers, config: dict):
        super().__init__()
        self.file_watchers = file_watchers
        self.config = config
        self.directory = directory
        self.task_done = False
        log('local: attaching observer to {}'.format(directory))

    def run(self):
        if not is_complete(self.directory):
            observer = LocalReportObserver(self, self.directory, self.config)
            try:
                while not self.task_done:
                    time.sleep(1)
            except (KeyboardInterrupt, SystemExit):
                observer.stop()
                observer.join()
                self.join()

            observer.stop()
            observer.join()
            self.file_watchers[self.directory] = None
            log('local: thread task finished')
        else:
            # Directory is complete, no need to spawn watcher
            while not self.task_done:
                # dummy
                url = 'https://cerebro-dev.herokuapp.com/api/v1/authenticate/report/b6b56c1090487819f0938f8de57cdfdf1ed70c72/'
                payload = {
                    'date': '{:%Y-%m-%dT%H:%M:%SZ}'.format(datetime.utcnow()),
                    'action': 'ALLOWED',
                    'door': 'Door 1A',
                    'details': 'Some description',
                    'wiegand_id': '0293204',
                    'user_enrollment_id': '1'
                }
                self.task_done = True

                # resp = send_files(self, url, headers=None,
                #     multipart=get_multipart(self.directory),
                #     payload=payload)
                # log('HTTP {0}: {1}'.format(resp.status_code, resp.text[:100]))
                # if resp.status_code < 400:
                #     self.task_done = True

class LocalReportObserver:
    def __init__(self, thread: LocalObserverThread, directory, config):
        # Properties
        self.directory = directory
        self.config = config
        self.thread = thread

        # Make folder
        path = Path(directory)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            log('local: directory {} created'.format(path))
        
        # Make observer
        self.observer = Observer()
        self.observer.schedule(LocalReportHandler(self.thread, self.directory, config),
            path=directory if directory else '.',
            recursive=True)
        self.observer.start()

    def join(self):
        self.observer.join()
    
    def stop(self):
        self.observer.stop()
        log('local: watchdog service for folder {} stopped'.format(self.directory))

class LocalReportHandler(PatternMatchingEventHandler):
    # Property of PatternMatchingEventHandler which contains list of filter file regex
    patterns=['*.jpg', '*.png', '*.bmp', '*.json']

    def __init__(self, thread: LocalObserverThread, directory, config):
        super().__init__()
        self.config = config
        self.thread = thread
        self.directory = directory
        self.file_watchers = thread.file_watchers

    def on_created(self, event):
        filename = event.src_path.split('/')[-1]
        folder = event.src_path.replace(filename, '')
        log('local: {0} file {2} at {1}'.format(event.event_type, folder, filename))

        # Perform check whether this folder is complete or not
        if self.is_file_complete():
            multipart = self.get_multipart()
            # Notify thread success
            self.thread.task_done = True
            log('local: finishing thread task ...')

    def is_file_complete(self):
        return is_complete(self.directory)

    def get_multipart(self):
        return get_multipart(self.directory)
                

def normalize_path(parent, filename):
    if parent[-1] == '/':
        return parent + filename
    else:
        return '{}/{}'.format(parent, filename)

def get_files_in_folder(directory):
    return [
        normalize_path(directory, f) for f in os.listdir(directory)
        if not os.path.isdir(normalize_path(directory, f))
    ]

def is_complete(directory):
    auth = None
    enroll = None
    files = get_files_in_folder(directory)
    for f in files:
        if 'auth' in f:
            auth = f
        elif 'enroll' in f:
            enroll = f
    return auth is not None and enroll is not None

def get_multipart(directory):
    output = {}
    files = get_files_in_folder(directory)
    for f in files:
        if 'auth' in f:
            output['auth_photo'] = open(f, 'rb')
        elif 'enroll' in f:
            output['enroll_photo'] = open(f, 'rb')
    return output

def send_files(thread: LocalObserverThread, url, headers, multipart, payload):
    log('Sending files to {0}'.format(url))
    return requests.post(url, headers=headers, data=payload, files=multipart)

def main():
    directory = 'report/a101'
    log('local: watching on folder {}'.format(directory))
    config = {}
    observer_thread = LocalObserverThread(directory, config, {})
    config[directory] = observer_thread
    observer_thread.start()
    observer_thread.join()

if __name__ == '__main__':
    main()