from multiprocessing import current_process

if current_process().name == 'MainProcess':
    from .manager import ResolveManager
    resolve_manager = ResolveManager()
