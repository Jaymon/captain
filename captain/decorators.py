
def arg(*parser_args, **parser_kwargs):
    def wrap(main):
        main.__dict__.setdefault('decorator_args', [])
        main.__dict__['decorator_args'].append((parser_args, parser_kwargs))
        return main

    return wrap 

