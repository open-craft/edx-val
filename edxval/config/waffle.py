"""
This module contains various configuration settings via
waffle switches for edx's video abstraction layer.
"""


from edx_toggles.toggles.__future__ import WaffleFlag

WAFFLE_NAMESPACE = 'edxval'


def waffle_name(toggle_name):
    """
    Method to append waffle namespace to toggle's name

    Reason behind not using f-strings is backwards compatibility
    Since this is a method, it should be easy to change later on
    """
    return "{namespace}.{toggle_name}".format(
        namespace=WAFFLE_NAMESPACE,
        toggle_name=toggle_name,
    )


OVERRIDE_EXISTING_IMPORTED_TRANSCRIPTS = WaffleFlag(
    waffle_name('override_existing_imported_transcripts'),
    module_name=__name__,
)
