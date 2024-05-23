from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import partial
from logging import getLogger
from pickle import dumps, PickleError

from requests import Session
from requests.adapters import DEFAULT_POOLSIZE, HTTPAdapter

def wrap(self, sup, background_callback, *args_, **kwargs_):
    resp = sup(*args_, **kwargs_)
    return background_callback(self, resp) or resp

PICKLE_ERROR = ('Cannot pickle function. Refer to documentation: https://'
                'github.com/ross/requests-futures/#using-processpoolexecutor')

class FuturesSession(Session):

    def __init__(self, executor=None, max_workers=8, session=None,
                 adapter_kwargs=None, *args, **kwargs):
        _adapter_kwargs = {}
        super(FuturesSession, self).__init__(*args, **kwargs)
        self._owned_executor = executor is None
        if executor is None:
            executor = ThreadPoolExecutor(max_workers=max_workers)
            if max_workers > DEFAULT_POOLSIZE:
                _adapter_kwargs.update({'pool_connections': max_workers,
                                        'pool_maxsize': max_workers})

        _adapter_kwargs.update(adapter_kwargs or {})

        if _adapter_kwargs:
            self.mount('https://', HTTPAdapter(**_adapter_kwargs))
            self.mount('http://', HTTPAdapter(**_adapter_kwargs))

        self.executor = executor
        self.session = session

    def request(self, *args, **kwargs):
        if self.session:
            func = self.session.request
        else:
            func = partial(Session.request, self)

        background_callback = kwargs.pop('background_callback', None)
        if background_callback:
            logger = getLogger(self.__class__.__name__)
            logger.warn('`background_callback` is deprecated and will be '
                        'removed in 1.0, use `hooks` instead')
            func = partial(wrap, self, func, background_callback)

        if isinstance(self.executor, ProcessPoolExecutor):
            try:
                dumps(func)
            except (TypeError, PickleError):
                raise RuntimeError(PICKLE_ERROR)

        return self.executor.submit(func, *args, **kwargs)

    def close(self):
        super(FuturesSession, self).close()
        if self._owned_executor:
            self.executor.shutdown()

    def get(self, url, **kwargs):
        return super(FuturesSession, self).get(url, **kwargs)

    def options(self, url, **kwargs):
        return super(FuturesSession, self).options(url, **kwargs)

    def head(self, url, **kwargs):
        return super(FuturesSession, self).head(url, **kwargs)

    def post(self, url, data=None, json=None, **kwargs):
        return super(FuturesSession, self).post(url, data=data, json=json, **kwargs)

    def put(self, url, data=None, **kwargs):
        return super(FuturesSession, self).put(url, data=data, **kwargs)

    def patch(self, url, data=None, **kwargs):
        return super(FuturesSession, self).patch(url, data=data, **kwargs)

    def delete(self, url, **kwargs):
        return super(FuturesSession, self).delete(url, **kwargs)
