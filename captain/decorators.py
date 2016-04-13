
def arg(*parser_args, **parser_kwargs):
    def wrap(main):
        main.__dict__.setdefault('decorator_args', [])
        main.__dict__['decorator_args'].append((parser_args, parser_kwargs))
        return main

    return wrap 


def args(*subcommands):
    def wrap(main):
        main.__dict__.setdefault('inherit_args', [])
        main.__dict__['inherit_args'].extend(subcommands)
        return main

    return wrap 

