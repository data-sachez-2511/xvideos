import threading
import logging
import sys
from typing import Union, Tuple, List, Dict

from xvideos.utils import *


class VideoReader(object):
    '''
    Class for video reading using opencv
    '''

    def __init__(
            self,
            source: Union[str, int],
            batch_size: int = 1,
            buffer_size: int = 1
    ):
        '''
        :param source: video source
        :param batch_size: number of frames, which will be returned
        :param buffer_size: number of frames in internal buffer
        '''
        self.capture = cv2.VideoCapture(source)
        self.capture_info = self.__info()
        self.batch_size = batch_size
        self.buffer_size = buffer_size

        self.buffer = []
        self.semaphore = threading.Semaphore(value=buffer_size)
        self.can_get = threading.Event()
        self.end = False
        threading.Thread(target=self.__read_video).start()

    def __read_video(self):
        if not self.capture.isOpened():
            logging.error('Capture is not opened.')
            return
        while True:
            status, frame = self.capture.read()
            if not status:
                self.can_get.set()
                self.end = True
                break
            self.semaphore.acquire()
            self.buffer.append(frame)
            if len(self.buffer) >= self.batch_size:
                self.can_get.set()

    def get(self) -> Tuple[bool, List]:
        '''
        Get batch of frames from buffer
        :return: pair (bool flag, list of frames). If capture has ended, then flag = False, else flag = True
        '''
        self.can_get.wait()
        batch = self.buffer[:self.batch_size]
        self.buffer = self.buffer[self.batch_size:]
        if sys.version_info[0] == 3 and sys.version_info[1] >= 9:
            self.semaphore.release(n=len(batch))
        else:
            for _ in range(len(batch)):
                self.semaphore.release()
        if len(self.buffer) < self.batch_size:
            self.can_get.clear()
        return not self.end, batch

    def __info(self) -> Dict:
        '''
        Return information of capture
        :return: dict with attributes of capture
        '''
        info = {}
        try:
            info['fps'] = get_fps(self.capture)
        except Exception as e:
            logging.warning(f'Failed to calculate fps: {e}')
        try:
            info['num_frames'] = count_frames(self.capture)
        except Exception as e:
            logging.warning(f'Failed to calculate number of frames: {e}')
        try:
            info['duration'] = video_duration(self.capture)
        except Exception as e:
            logging.warning(f'Failed to calculate duration of video: {e}')
        return info

    @property
    def info(self):
        '''
        Info of video capture
        '''
        return self.capture_info