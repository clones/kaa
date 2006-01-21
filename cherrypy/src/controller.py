__all__ = [ 'expose' ]

import kid

from kaa.notifier import MainThreadCallback

def expose(template=None, mainloop=True):

    def decorator(func):
            
        def newfunc(self, *args, **kwargs):
            _function = _execute_func
            if mainloop:
                _function = MainThreadCallback(_execute_func)
                _function.set_async(False)
            return _function(self, template, func, *args, **kwargs)
            
        try:
            newfunc.func_name = func.func_name
        except TypeError:
            pass
        newfunc.exposed = True
        return newfunc
        
    return decorator


def _execute_func(self, template, func, *args, **kwargs):
    if not template:
        return func(self, *args, **kwargs)
    template = kid.Template(file=template)
    func(self, template, *args, **kwargs)
    return template.serialize(output='xhtml')




