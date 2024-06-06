# -*- coding: utf-8 -*-

from datatypes.config import Environ


class Environ(Environ):
    def __init__(self, *args, **kwargs):
        super().__init__(namespace="CAPTAIN_", **kwargs)

        # This should be a string similar to what --quiet takes
        self.setdefault("QUIET_DEFAULT", "")

        # lots of output functions are width constrained, this is the global
        # width they default to
        self.setdefault("WIDTH", 79, type=int)

        # the name of the autodiscover module name that will be used if
        # AUTODISCOVER is True
        self.setdefault("AUTODISCOVER_NAME", "commands")

    def get_command_prefixes(self, env_name='PREFIX'):
        """this will look for CAPTAIN_PREFIX, and CAPTAIN_PREFIX_N (where
        N is 1 to infinity) in the environment, if it finds them, it will
        assume they are python module paths where endpoints can find Controller
        subclasses

        The num checks (eg CAPTAIN_PREFIX_1, CAPTAIN_PREFIX_2) go in order,
        so you can't do CAPTAIN_PREFIX_1, CAPTAIN_PREFIX_3, because it will
        fail on _2 and move on, so make sure your num dsns are in order (eg, 1,
        2, 3, ...)

        :Example:
            export CAPTAIN_PREFIX_1=foo.commands
            export CAPTAIN_PREFIX_2=bar.che
            $ python
            >>> from captain.config import environ
            >>> environ.get_command_prefixes()
            ['foo.commands', 'bar.che']

        :param env_name: string, the name of the environment variables
        :returns: list, the found module paths
        """
        return list(self.paths(env_name))


environ = Environ()

