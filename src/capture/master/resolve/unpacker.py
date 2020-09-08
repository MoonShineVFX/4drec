from multiprocessing import Pool, shared_memory
import numpy as np


class Unpacker:
    def __init__(self):
        self._pool = Pool(8)
        self._cache_payloads = {}
        self._cache_memory = {}
        self._cache_orders = []

    @staticmethod
    def unpack_method(package, package_name):
        global _arr
        payload = package.to_payload()
        if payload[2] is not None:
            shm = shared_memory.SharedMemory(name=package_name)
            this_arr = np.ndarray((4096, 4096, 3), dtype=np.uint8, buffer=shm.buf)
            src_arr = payload[2]
            np.copyto(this_arr, src_arr, 'unsafe')
            shm.close()
            return payload[0], payload[1], False
        return payload[0], payload[1], None

    def handle_callback(self, result, callback, package_name):
        if result[2] is False:
            shm = shared_memory.SharedMemory(name=package_name)
            this_arr = np.ndarray((4096, 4096, 3), dtype=np.uint8, buffer=shm.buf)
            copy_arr = this_arr.copy()
            shm.close()
            shm.unlink()
            del self._cache_memory[package_name]

            payload = (result[0], result[1], copy_arr)
            if package_name not in self._cache_orders:
                self._cache_orders.append(package_name)
                self._cache_payloads[package_name] = payload
                if len(self._cache_orders) > 60:
                    del_names = self._cache_orders[:-60]
                    for name in del_names:
                        self._cache_orders.remove(name)
                        del self._cache_payloads[name]

            if callback is not None:
                callback(payload)
        else:
            if callback is not None:
                callback((result[0], result[1], None))

    @staticmethod
    def handle_error(err):
        raise(err)

    def unpack(self, package, callback):
        package_name = package.get_name()
        if package_name in self._cache_orders:
            payload = self._cache_payloads[package_name]
            if payload is None:
                return
            if not package.get_dont_send():
                callback(self._cache_payloads[package_name])
        self._cache_orders.append(package_name)
        self._cache_payloads[package_name] = None
        self._cache_memory[package_name] = shared_memory.SharedMemory(name=package_name, create=True, size=4096 * 4096 * 3)

        callback_func = None if package.get_dont_send() else callback

        self._pool.apply_async(
            self.unpack_method, (package, package_name),
            callback=lambda result: self.handle_callback(result, callback_func, package_name),
            error_callback=self.handle_error
        )
